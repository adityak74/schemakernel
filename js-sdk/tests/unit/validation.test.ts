import { describe, it, expect, beforeEach } from "vitest";
import { ValidationEngine } from "../../src/validation";
import { 
  FieldType, 
  ValidatorType, 
  PlannerResponse, 
  CompletionStatus, 
  ActionType,
  WorkflowStage
} from "../../src/models";
import { PolicyConfigSchema } from "../../src/policy";
import { PlannerOutputRejected, FieldValidationError } from "../../src/exceptions";

describe("ValidationEngine", () => {
  let engine: ValidationEngine;
  const defaultPolicy = PolicyConfigSchema.parse({});

  beforeEach(() => {
    engine = new ValidationEngine(defaultPolicy);
  });

  const makeMockState = (fields: any = {}) => ({
    session_id: "test",
    fields: fields,
    field_order: Object.keys(fields),
    answers: {},
    stage: WorkflowStage.INITIALIZED,
    turn_count: 0,
    created_at: new Date(),
    updated_at: new Date(),
    audit_log: []
  });

  describe("validatePlannerResponse", () => {
    it("should reject response with too many fields", () => {
      const policy = PolicyConfigSchema.parse({ max_fields: 2 });
      const smallEngine = new ValidationEngine(policy);
      const response: PlannerResponse = {
        actions: [
          { action: ActionType.ADD, field_key: "f1" },
          { action: ActionType.ADD, field_key: "f2" },
          { action: ActionType.ADD, field_key: "f3" },
        ],
        fields: [
          { key: "f1", type: FieldType.TEXT, label: "L1" },
          { key: "f2", type: FieldType.TEXT, label: "L2" },
          { key: "f3", type: FieldType.TEXT, label: "L3" },
        ],
        rationale: ["Too many"],
        completion_status: CompletionStatus.IN_PROGRESS,
      };
      expect(() => smallEngine.validatePlannerResponse(response, makeMockState(), { raiseOnFailure: true })).toThrow(PlannerOutputRejected);
    });

    it("should accept valid response", () => {
      const response: PlannerResponse = {
        actions: [{ action: ActionType.ADD, field_key: "f1" }],
        fields: [{ key: "f1", type: FieldType.TEXT, label: "L1" }],
        rationale: ["OK"],
        completion_status: CompletionStatus.IN_PROGRESS,
      };
      expect(() => engine.validatePlannerResponse(response, makeMockState())).not.toThrow();
    });
  });

  describe("validateAnswer", () => {
    it("should coerce and validate number", () => {
      const field = {
        key: "age",
        type: FieldType.NUMBER,
        label: "Age",
        validators: [{ type: ValidatorType.MIN, value: 18 }]
      } as any;
      
      const result = engine.validateAnswer(field, "25");
      expect(result.valid).toBe(true);
      expect(() => engine.validateAnswer(field, "15", { raiseOnFailure: true })).toThrow(FieldValidationError);
    });

    it("should coerce and validate boolean", () => {
      const field = {
        key: "agree",
        type: FieldType.BOOLEAN,
        label: "Agree",
      } as any;
      
      expect(engine.validateAnswer(field, "true").valid).toBe(true);
      expect(engine.validateAnswer(field, "false").valid).toBe(true);
      expect(engine.validateAnswer(field, 1).valid).toBe(true);
      expect(engine.validateAnswer(field, 0).valid).toBe(true);
    });

    it("should coerce and validate date", () => {
      const field = {
        key: "dob",
        type: FieldType.DATE,
        label: "DOB",
        validators: [{ type: ValidatorType.DATE_BEFORE, value: "2000-01-01" }]
      } as any;
      
      const result = engine.validateAnswer(field, "1990-05-05");
      expect(result.valid).toBe(true);
      expect(() => engine.validateAnswer(field, "2005-01-01", { raiseOnFailure: true })).toThrow(FieldValidationError);
    });

    it("should validate regex pattern", () => {
      const field = {
        key: "code",
        type: FieldType.TEXT,
        label: "Code",
        validators: [{ type: ValidatorType.PATTERN, value: "^[A-Z]{3}$" }]
      } as any;
      
      expect(engine.validateAnswer(field, "ABC").valid).toBe(true);
      expect(() => engine.validateAnswer(field, "abcd", { raiseOnFailure: true })).toThrow(FieldValidationError);
      expect(() => engine.validateAnswer(field, "ABCD", { raiseOnFailure: true })).toThrow(FieldValidationError); // too long
    });

    it("should validate required field", () => {
       const field = {
        key: "name",
        type: FieldType.TEXT,
        label: "Name",
        required: true,
        validators: [{ type: ValidatorType.REQUIRED }]
      } as any;
      
      expect(engine.validateAnswer(field, "John").valid).toBe(true);
      expect(() => engine.validateAnswer(field, null, { raiseOnFailure: true })).toThrow(FieldValidationError);
      expect(() => engine.validateAnswer(field, "", { raiseOnFailure: true })).toThrow(FieldValidationError);
    });
  });
});
