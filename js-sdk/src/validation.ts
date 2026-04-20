import dayjs from "dayjs";
import { PolicyConfig } from "./policy";
import { 
  PlannerResponse, 
  FieldDefinition, 
  FieldType, 
  ValidatorType, 
  ActionType,
  ValidatorRule,
  SchemaState
} from "./models";
import { 
  FieldValidationError, 
  PolicyViolationError, 
  PlannerOutputRejected 
} from "./exceptions";

export interface ValidationResult {
  valid: boolean;
  errors: FieldValidationError[];
}

const ALLOWED_ACTION_TYPES = new Set(Object.values(ActionType));
const ALLOWED_FIELD_TYPES = new Set(Object.values(FieldType));
const ALLOWED_VALIDATOR_TYPES = new Set(Object.values(ValidatorType));

const FORBIDDEN_UI_PATTERNS = ["__", "exec", "eval", "import", "<script", "javascript:"];

export class ValidationEngine {
  constructor(private policy: PolicyConfig) {}

  validatePlannerResponse(
    response: PlannerResponse, 
    state: SchemaState,
    options: { raiseOnFailure?: boolean } = {}
  ): ValidationResult {
    const errors: FieldValidationError[] = [];

    // 1. Allowlist: action types
    for (const action of response.actions) {
      if (!ALLOWED_ACTION_TYPES.has(action.action)) {
        errors.push(new FieldValidationError("_action", `Unknown action type '${action.action}'`));
      }
    }

    // 2. Allowlist: field types
    for (const fd of response.fields ?? []) {
      if (!ALLOWED_FIELD_TYPES.has(fd.type)) {
        errors.push(new FieldValidationError(fd.key, `Unknown field type '${fd.type}'`));
      }
    }

    // 3. Allowlist: validator types
    for (const fd of response.fields ?? []) {
      for (const vr of fd.validators ?? []) {
        if (!ALLOWED_VALIDATOR_TYPES.has(vr.type)) {
          errors.push(new FieldValidationError(fd.key, `Unknown validator type '${vr.type}'`));
        }
      }
    }

    // 4. Safety: ui_props forbidden patterns
    for (const fd of response.fields ?? []) {
      for (const [k, v] of Object.entries(fd.ui_props ?? {})) {
        for (const pat of FORBIDDEN_UI_PATTERNS) {
          if (k.toLowerCase().includes(pat) || String(v).toLowerCase().includes(pat)) {
            errors.push(new FieldValidationError(fd.key, `ui_props contains forbidden pattern '${pat}'`));
          }
        }
      }
    }

    // 5. Policy: max_fields check
    const addKeys = new Set(response.actions.filter(a => a.action === ActionType.ADD).map(a => a.field_key));
    const removeKeys = new Set(response.actions.filter(a => a.action === ActionType.REMOVE).map(a => a.field_key));
    const currentFieldCount = Object.keys(state.fields).length;
    const projectedCount = currentFieldCount + addKeys.size - removeKeys.size;
    if (projectedCount > this.policy.max_fields) {
      errors.push(new FieldValidationError("_schema", `Schema would have ${projectedCount} fields, exceeding max_fields=${this.policy.max_fields}`));
    }

    // 6. Policy: prohibited topics
    errors.push(...this.checkProhibitedContent(response));

    // 7. Cross-reference: ADD must not duplicate existing keys
    for (const action of response.actions) {
      if (action.action === ActionType.ADD && action.field_key && state.fields[action.field_key]) {
        errors.push(new FieldValidationError(action.field_key, `ADD action targets already-existing field '${action.field_key}'`));
      }
    }

    // 8. Cross-reference: UPDATE/REMOVE/REQUIRE/HIDE/SHOW must target existing keys
    const mutateActions = new Set([
      ActionType.UPDATE,
      ActionType.REMOVE,
      ActionType.REQUIRE,
      ActionType.HIDE,
      ActionType.SHOW,
      ActionType.REORDER,
    ]);
    for (const action of response.actions) {
      if (mutateActions.has(action.action) && action.field_key) {
        if (!state.fields[action.field_key]) {
          errors.push(new FieldValidationError(action.field_key, `action '${action.action}' targets non-existent field '${action.field_key}'`));
        }
      }
    }

    const result = { valid: errors.length === 0, errors };
    if (!result.valid && options.raiseOnFailure) {
      throw new PlannerOutputRejected(`Planner response rejected: ${errors.map(e => e.reason).join("; ")}`);
    }
    return result;
  }

  private checkProhibitedContent(response: PlannerResponse): FieldValidationError[] {
    const errors: FieldValidationError[] = [];
    if (!this.policy.prohibited_topics || this.policy.prohibited_topics.length === 0) {
      return errors;
    }

    const topics = this.policy.prohibited_topics.map(t => t.toLowerCase());

    for (const fd of response.fields ?? []) {
      const combined = `${fd.key} ${fd.label || ""} ${fd.description || ""}`.toLowerCase();
      for (const topic of topics) {
        if (combined.includes(topic)) {
          errors.push(new FieldValidationError(fd.key, `Field references prohibited topic '${topic}'`));
          break;
        }
      }
    }

    for (const text of response.rationale ?? []) {
      const tl = text.toLowerCase();
      for (const topic of topics) {
        if (tl.includes(topic)) {
          errors.push(new FieldValidationError("_rationale", `Rationale references prohibited topic '${topic}'`));
          break;
        }
      }
    }

    if (response.next_prompt_context) {
      const npc = response.next_prompt_context.toLowerCase();
      for (const topic of topics) {
        if (npc.includes(topic)) {
          errors.push(new FieldValidationError("_next_prompt_context", `next_prompt_context references prohibited topic '${topic}'`));
          break;
        }
      }
    }

    return errors;
  }

  validateAnswer(
    field: FieldDefinition, 
    value: any,
    options: { raiseOnFailure?: boolean } = {}
  ): ValidationResult {
    const errors: FieldValidationError[] = [];
    const { coerced, error } = this.coerce(field, value);
    if (error) {
      const fve = new FieldValidationError(field.key, error, value);
      errors.push(fve);
      const result = { valid: false, errors };
      if (options.raiseOnFailure) {
        throw fve;
      }
      return result;
    }

    for (const rule of field.validators ?? []) {
      const ruleError = this.checkRule(field, rule, coerced);
      if (ruleError) {
        errors.push(ruleError);
      }
    }

    const result = { valid: errors.length === 0, errors };
    if (!result.valid && options.raiseOnFailure) {
      throw errors[0];
    }
    return result;
  }

  coerce(field: FieldDefinition, value: any): { coerced: any; error?: string } {
    if (value === null || value === undefined) {
      return { coerced: null };
    }

    try {
      if (field.type === FieldType.INTEGER) {
        const val = parseInt(value, 10);
        if (isNaN(val)) return { coerced: null, error: `Cannot coerce '${value}' to integer` };
        return { coerced: val };
      }
      if (field.type === FieldType.NUMBER) {
        const val = parseFloat(value);
        if (isNaN(val)) return { coerced: null, error: `Cannot coerce '${value}' to number` };
        return { coerced: val };
      }
      if (field.type === FieldType.BOOLEAN) {
        if (typeof value === "boolean") return { coerced: value };
        const sv = String(value).toLowerCase().trim();
        if (["true", "1", "yes"].includes(sv)) return { coerced: true };
        if (["false", "0", "no"].includes(sv)) return { coerced: false };
        return { coerced: null, error: `Cannot coerce '${value}' to boolean` };
      }
      if (field.type === FieldType.DATE || field.type === FieldType.DATETIME) {
        const d = dayjs(value);
        if (!d.isValid()) return { coerced: null, error: `Cannot coerce '${value}' to ${field.type}` };
        return { coerced: d.toDate() };
      }
    } catch (e) {
      return { coerced: null, error: `Type coercion failed for type '${field.type}': ${e}` };
    }

    return { coerced: value };
  }

  private checkRule(field: FieldDefinition, rule: ValidatorRule, coerced: any): FieldValidationError | null {
    const key = field.key;
    const msg = rule.message;

    const err = (defaultMsg: string) => new FieldValidationError(key, msg || defaultMsg, coerced);

    if (rule.type === ValidatorType.REQUIRED) {
      if (coerced === null || coerced === undefined || coerced === "") {
        return err("This field is required");
      }
    } else if (rule.type === ValidatorType.MIN) {
      if (coerced !== null && coerced !== undefined) {
        if (Number(coerced) < Number(rule.value)) {
          return err(`Value must be >= ${rule.value}`);
        }
      }
    } else if (rule.type === ValidatorType.MAX) {
      if (coerced !== null && coerced !== undefined) {
        if (Number(coerced) > Number(rule.value)) {
          return err(`Value must be <= ${rule.value}`);
        }
      }
    } else if (rule.type === ValidatorType.MIN_LENGTH) {
      if (coerced !== null && coerced !== undefined) {
        if (String(coerced).length < Number(rule.value)) {
          return err(`Length must be >= ${rule.value}`);
        }
      }
    } else if (rule.type === ValidatorType.MAX_LENGTH) {
      if (coerced !== null && coerced !== undefined) {
        if (String(coerced).length > Number(rule.value)) {
          return err(`Length must be <= ${rule.value}`);
        }
      }
    } else if (rule.type === ValidatorType.PATTERN) {
      if (coerced !== null && coerced !== undefined) {
        const pattern = String(rule.value);
        const regex = new RegExp(`^${pattern}$`);
        if (!regex.test(String(coerced))) {
          return err(`Value does not match pattern '${pattern}'`);
        }
      }
    } else if (rule.type === ValidatorType.ENUM_MEMBER) {
      if (coerced !== null && coerced !== undefined && field.options) {
        if (!field.options.includes(String(coerced))) {
          return err(`Value must be one of ${field.options.join(", ")}`);
        }
      }
    } else if (rule.type === ValidatorType.POSITIVE) {
      if (coerced !== null && coerced !== undefined) {
        if (Number(coerced) <= 0) {
          return err("Value must be positive (> 0)");
        }
      }
    } else if (rule.type === ValidatorType.NON_NEGATIVE) {
      if (coerced !== null && coerced !== undefined) {
        if (Number(coerced) < 0) {
          return err("Value must be non-negative (>= 0)");
        }
      }
    } else if (rule.type === ValidatorType.DATE_AFTER) {
      if (coerced !== null && coerced !== undefined) {
        const threshold = dayjs(String(rule.value));
        const coercedDate = dayjs(coerced);
        if (coercedDate.isBefore(threshold) || coercedDate.isSame(threshold)) {
          return err(`Date must be after ${rule.value}`);
        }
      }
    } else if (rule.type === ValidatorType.DATE_BEFORE) {
      if (coerced !== null && coerced !== undefined) {
        const threshold = dayjs(String(rule.value));
        const coercedDate = dayjs(coerced);
        if (coercedDate.isAfter(threshold) || coercedDate.isSame(threshold)) {
          return err(`Date must be before ${rule.value}`);
        }
      }
    }

    return null;
  }
}
