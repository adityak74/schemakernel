import { 
  ActionType, 
  CompletionOutcome, 
  CompletionStatus, 
  ConditionalLogic, 
  ConditionOperator, 
  FieldDefinition, 
  FieldDefinitionSchema,
  PlannerResponse, 
  PlannerTrace, 
  SchemaState, 
  WorkflowStage 
} from "./models";
import { PolicyConfig } from "./policy";
import { StorageBackend } from "./store";
import { PlannerClient } from "./planner";
import { ValidationEngine, ValidationResult } from "./validation";
import { 
  FieldValidationError, 
  PlannerOutputRejected, 
  TurnLimitExceeded 
} from "./exceptions";

export const ALWAYS_HIDDEN: ConditionalLogic = {
  combinator: "and",
  conditions: [
    {
      field_key: "__never__",
      operator: ConditionOperator.EQ,
      value: "__never__",
    },
  ],
};

export class WorkflowStateMachine {
  constructor(
    private _policy: PolicyConfig,
    private _store: StorageBackend,
    private _planner: PlannerClient,
    private _validator: ValidationEngine
  ) {}

  async startSession(sessionId?: string): Promise<SchemaState> {
    const sid = sessionId || (typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2));
    const state: SchemaState = {
      session_id: sid,
      fields: {},
      field_order: [],
      answers: {},
      stage: WorkflowStage.COLLECTING,
      turn_count: 0,
      created_at: new Date(),
      updated_at: new Date(),
      audit_log: [],
    };

    for (const fd of this._policy.baseline_questions) {
      state.fields[fd.key] = FieldDefinitionSchema.parse(fd);
      state.field_order.push(fd.key);
    }

    await this._store.saveState(state);
    return JSON.parse(JSON.stringify(state));
  }

  async submitAnswer(
    sessionId: string,
    fieldKey: string,
    value: any,
    options: { raiseOnFailure?: boolean } = {}
  ): Promise<ValidationResult> {
    const state = await this._store.loadState(sessionId);

    if (!state.fields[fieldKey]) {
      const err = new FieldValidationError(fieldKey, `Field '${fieldKey}' does not exist in schema`);
      const result: ValidationResult = { valid: false, errors: [err] };
      if (options.raiseOnFailure) {
        throw err;
      }
      return result;
    }

    const field = state.fields[fieldKey];
    const result = this._validator.validateAnswer(field, value, options);

    if (result.valid) {
      // Use coerced value from validator
      const { coerced } = this._validator.coerce(field, value);
      state.answers[fieldKey] = coerced;
      state.audit_log.push({
        event: "answer_submitted",
        field_key: fieldKey,
        value: coerced,
        timestamp: new Date().toISOString()
      });
      state.updated_at = new Date();
      await this._store.saveState(state);
    }

    return result;
  }

  async runPlannerTurn(sessionId: string): Promise<SchemaState> {
    const state = await this._store.loadState(sessionId);

    if (state.turn_count >= this._policy.max_turns) {
      throw new TurnLimitExceeded(`Session '${sessionId}' reached max_turns=${this._policy.max_turns}`);
    }

    const systemPrompt = this._buildSystemPrompt(state);
    const messages = this._buildMessages(state);

    const response = await this._planner.call(messages as any, systemPrompt);

    const trace: PlannerTrace = {
      session_id: sessionId,
      turn: state.turn_count,
      raw_response: response,
      validated: false,
      timestamp: new Date()
    };

    const valResult = this._validator.validatePlannerResponse(response, state);

    if (!valResult.valid) {
      const rejection = valResult.errors.map(e => e.reason).join("; ");
      trace.rejection_reason = rejection;
      await this._store.saveTrace(trace);
      throw new PlannerOutputRejected(`Planner response rejected: ${rejection}`);
    }

    trace.validated = true;
    await this._store.saveTrace(trace);

    this._applyActions(state, response);
    state.turn_count += 1;
    state.audit_log.push({
      event: "planner_turn",
      turn: state.turn_count,
      completion_status: response.completion_status,
      rationale: response.rationale,
      timestamp: new Date().toISOString()
    });
    state.updated_at = new Date();

    if (
      response.completion_status === CompletionStatus.COMPLETE ||
      response.completion_status === CompletionStatus.ESCALATE
    ) {
      const outcome: CompletionOutcome = {
        session_id: sessionId,
        status: response.completion_status,
        final_answers: { ...state.answers },
        final_schema: JSON.parse(JSON.stringify(state.fields)),
        rationale: response.rationale,
        completed_at: new Date(),
      };
      await this._store.saveOutcome(outcome);
    }

    await this._store.saveState(state);
    return JSON.parse(JSON.stringify(state));
  }

  async getNextFields(sessionId: string): Promise<FieldDefinition[]> {
    const state = await this._store.loadState(sessionId);
    const result: FieldDefinition[] = [];

    for (const key of state.field_order) {
      const fd = state.fields[key];
      if (!fd) continue;
      if (!fd.ask_if_missing) continue;
      if (key in state.answers) continue;
      if (fd.visible_if) {
        if (!this._evaluateCondition(fd.visible_if, state.answers)) {
          continue;
        }
      }
      result.push(fd);
    }

    result.sort((a, b) => (a.priority || 100) - (b.priority || 100));
    return result;
  }

  async getState(sessionId: string): Promise<SchemaState> {
    return this._store.loadState(sessionId);
  }

  private _buildSystemPrompt(state: SchemaState): string {
    const p = this._policy;
    const lines: string[] = [
      "You are a form planning assistant for SchemaKernel.",
      `Reasoning style: ${p.reasoning_style}`,
      "",
      "Your job is to decide which fields to add, update, or finalize based on the",
      "current schema and the answers collected so far.",
      "You MUST return a valid PlannerResponse. Do not generate HTML, CSS, or executable code.",
      "",
    ];

    if (Object.keys(p.glossary).length > 0) {
      lines.push("## Glossary");
      for (const [term, definition] of Object.entries(p.glossary)) {
        lines.push(`- ${term}: ${definition}`);
      }
      lines.push("");
    }

    if (p.prohibited_topics.length > 0) {
      lines.push("## Prohibited Topics");
      lines.push("You must NOT reference these topics in any field or rationale:");
      for (const topic of p.prohibited_topics) {
        lines.push(`- ${topic}`);
      }
      lines.push("");
    }

    if (p.exception_rules.length > 0) {
      lines.push("## Exception Rules");
      for (const rule of p.exception_rules) {
        lines.push(`- [${rule.name}] ${rule.description}`);
      }
      lines.push("");
    }

    const criteria = p.completion_criteria;
    if (criteria.required_fields_answered?.length || criteria.minimum_answered_count || criteria.custom_description) {
      lines.push("## Completion Criteria");
      if (criteria.required_fields_answered?.length) {
        lines.push(`- Required fields answered: ${criteria.required_fields_answered.join(", ")}`);
      }
      if (criteria.minimum_answered_count) {
        lines.push(`- Minimum answered count: ${criteria.minimum_answered_count}`);
      }
      if (criteria.custom_description) {
        lines.push(`- ${criteria.custom_description}`);
      }
      lines.push("");
    }

    lines.push("## Current Schema");
    if (state.field_order.length > 0) {
      for (const key of state.field_order) {
        const fd = state.fields[key];
        if (!fd) continue;
        const answered = key in state.answers ? "answered" : "not answered";
        lines.push(`- ${key} (${fd.type}, required=${fd.required}, ${answered}): ${fd.label}`);
      }
    } else {
      lines.push("(no fields yet)");
    }
    lines.push("");

    lines.push(`Max fields allowed: ${p.max_fields}`);
    lines.push(`Current turn: ${state.turn_count + 1} / ${p.max_turns}`);

    return lines.join("\n");
  }

  private _buildMessages(state: SchemaState): any[] {
    const answersText = JSON.stringify(state.answers, null, 2);
    return [
      {
        role: "user",
        content: `Current answers:\n\`\`\`json\n${answersText}\n\`\`\`\n\n` +
          "Based on the policy and the answers above, decide what to do next. " +
          "Return a PlannerResponse."
      }
    ];
  }

  private _applyActions(state: SchemaState, response: PlannerResponse): void {
    const fieldMap = new Map((response.fields || []).map(f => [f.key, f]));

    for (const action of response.actions) {
      const key = action.field_key;
      
      switch (action.action) {
        case ActionType.ADD:
          if (key) {
            const fd = fieldMap.get(key);
            if (fd) {
              state.fields[key] = FieldDefinitionSchema.parse(fd);
              if (!state.field_order.includes(key)) {
                state.field_order.push(key);
              }
            }
          }
          break;

        case ActionType.UPDATE:
          if (key) {
            const fd = fieldMap.get(key);
            if (fd) {
              state.fields[key] = FieldDefinitionSchema.parse(fd);
            }
          }
          break;

        case ActionType.REMOVE:
          if (key) {
            delete state.fields[key];
            state.field_order = state.field_order.filter(k => k !== key);
            delete state.answers[key];
          }
          break;

        case ActionType.REQUIRE:
          if (key && state.fields[key]) {
            state.fields[key].required = true;
          }
          break;

        case ActionType.HIDE:
          if (key && state.fields[key]) {
            state.fields[key].visible_if = JSON.parse(JSON.stringify(ALWAYS_HIDDEN));
          }
          break;

        case ActionType.SHOW:
          if (key && state.fields[key]) {
            state.fields[key].visible_if = null;
          }
          break;

        case ActionType.REORDER:
          if (key && state.field_order.includes(key) && action.position !== undefined && action.position !== null) {
            state.field_order = state.field_order.filter(k => k !== key);
            const pos = Math.min(action.position, state.field_order.length);
            state.field_order.splice(pos, 0, key);
          }
          break;

        case ActionType.COMPLETE:
          state.stage = WorkflowStage.COMPLETE;
          break;

        case ActionType.ESCALATE:
          state.stage = WorkflowStage.ESCALATED;
          break;
      }
    }
  }

  private _evaluateCondition(logic: ConditionalLogic, answers: Record<string, any>): boolean {
    const results = logic.conditions.map(c => this._evalSingle(c, answers));
    if (logic.combinator === "and") {
      return results.every(r => r);
    }
    return results.some(r => r);
  }

  private _evalSingle(condition: any, answers: Record<string, any>): boolean {
    const value = answers[condition.field_key];
    const op = condition.operator;
    const cv = condition.value;

    if (op === ConditionOperator.IS_EMPTY) {
      return value === null || value === undefined || value === "";
    }
    if (op === ConditionOperator.NOT_EMPTY) {
      return value !== null && value !== undefined && value !== "";
    }
    if (op === ConditionOperator.EQ) {
      return value === cv;
    }
    if (op === ConditionOperator.NEQ) {
      return value !== cv;
    }
    if (op === ConditionOperator.IN) {
      return Array.isArray(cv) && cv.includes(value);
    }
    if (op === ConditionOperator.NOT_IN) {
      return Array.isArray(cv) && !cv.includes(value);
    }

    // Numeric comparisons
    const fv = parseFloat(value);
    const fc = parseFloat(cv);
    if (isNaN(fv) || isNaN(fc)) {
      return false;
    }

    if (op === ConditionOperator.GT) return fv > fc;
    if (op === ConditionOperator.GTE) return fv >= fc;
    if (op === ConditionOperator.LT) return fv < fc;
    if (op === ConditionOperator.LTE) return fv <= fc;

    return false;
  }
}
