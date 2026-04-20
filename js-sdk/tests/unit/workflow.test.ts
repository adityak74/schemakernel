import { describe, it, expect, vi, beforeEach } from "vitest";
import { WorkflowStateMachine } from "../../src/workflow";
import { 
  ActionType, 
  CompletionStatus, 
  FieldType, 
  WorkflowStage, 
  ConditionOperator 
} from "../../src/models";
import { InMemoryStore } from "../../src/store";
import { ValidationEngine } from "../../src/validation";
import { PlannerClient } from "../../src/planner";

describe("WorkflowStateMachine", () => {
  let policy: any;
  let store: InMemoryStore;
  let planner: any;
  let validator: ValidationEngine;
  let wsm: WorkflowStateMachine;

  beforeEach(() => {
    policy = {
      baseline_questions: [
        { key: "q1", type: FieldType.TEXT, label: "Q1", required: true }
      ],
      max_turns: 5,
      max_fields: 10,
      prohibited_topics: [],
      glossary: {},
      exception_rules: [],
      completion_criteria: {},
      reasoning_style: "balanced"
    };
    store = new InMemoryStore();
    planner = {
      call: vi.fn()
    };
    validator = new ValidationEngine(policy);
    wsm = new WorkflowStateMachine(policy, store, planner as any, validator);
  });

  it("should start a session with baseline questions", async () => {
    const state = await wsm.startSession("session-1");
    expect(state.session_id).toBe("session-1");
    expect(state.fields["q1"]).toBeDefined();
    expect(state.field_order).toContain("q1");
    expect(state.stage).toBe(WorkflowStage.COLLECTING);
  });

  it("should submit a valid answer", async () => {
    await wsm.startSession("session-1");
    const result = await wsm.submitAnswer("session-1", "q1", "Answer 1");
    expect(result.valid).toBe(true);

    const state = await store.loadState("session-1");
    expect(state.answers["q1"]).toBe("Answer 1");
  });

  it("should run a planner turn and apply actions", async () => {
    await wsm.startSession("session-1");
    
    const mockResponse = {
      actions: [
        { action: ActionType.ADD, field_key: "q2" },
        { action: ActionType.COMPLETE }
      ],
      fields: [
        { key: "q2", type: FieldType.TEXT, label: "Q2", required: false }
      ],
      rationale: ["Added Q2", "Done"],
      completion_status: CompletionStatus.COMPLETE
    };

    planner.call.mockResolvedValue(mockResponse);

    const state = await wsm.runPlannerTurn("session-1");
    
    expect(state.fields["q2"]).toBeDefined();
    expect(state.field_order).toContain("q2");
    expect(state.stage).toBe(WorkflowStage.COMPLETE);
    expect(state.turn_count).toBe(1);
  });

  it("should evaluate conditions for getNextFields", async () => {
    policy.baseline_questions.push({
      key: "q2",
      type: FieldType.TEXT,
      label: "Q2",
      visible_if: {
        combinator: "and",
        conditions: [{ field_key: "q1", operator: ConditionOperator.EQ, value: "yes" }]
      }
    });

    await wsm.startSession("session-1");

    // Initially q2 is hidden because q1 is not "yes"
    let nextFields = await wsm.getNextFields("session-1");
    expect(nextFields.map(f => f.key)).toEqual(["q1"]);

    // Answer q1 with "no"
    await wsm.submitAnswer("session-1", "q1", "no");
    nextFields = await wsm.getNextFields("session-1");
    expect(nextFields.map(f => f.key)).toEqual([]);

    // Answer q1 with "yes"
    await wsm.submitAnswer("session-1", "q1", "yes");
    nextFields = await wsm.getNextFields("session-1");
    expect(nextFields.map(f => f.key)).toEqual(["q2"]);
  });
});
