import { describe, it, expect } from "vitest";
import { mapToSurveyJS } from "../../src/adapters/surveyjs";
import {
  FieldType,
  SchemaState,
  WorkflowStage,
  ConditionOperator,
} from "../../src/models";

describe("SurveyJS Adapter", () => {
  it("should map a simple SchemaState to SurveyJS JSON", () => {
    const state: SchemaState = {
      session_id: "test-session",
      fields: {
        name: {
          key: "name",
          type: FieldType.TEXT,
          label: "Full Name",
          required: true,
          ui_props: {},
          validators: [],
          priority: 100,
          ask_if_missing: true,
        },
      },
      field_order: ["name"],
      answers: {},
      stage: WorkflowStage.COLLECTING,
      turn_count: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      audit_log: [],
    };

    const surveyJson = mapToSurveyJS(state);

    expect(surveyJson.elements).toHaveLength(1);
    expect(surveyJson.elements[0].name).toBe("name");
    expect(surveyJson.elements[0].type).toBe("text");
    expect(surveyJson.elements[0].title).toBe("Full Name");
    expect(surveyJson.elements[0].isRequired).toBe(true);
  });

  it("should map different field types correctly", () => {
    const state: SchemaState = {
      session_id: "test-session",
      fields: {
        bio: {
          key: "bio",
          type: FieldType.TEXTAREA,
          label: "Biography",
          required: false,
          ui_props: {},
          validators: [],
          priority: 100,
          ask_if_missing: true,
        },
        gender: {
          key: "gender",
          type: FieldType.SELECT,
          label: "Gender",
          required: true,
          options: ["Male", "Female", "Other"],
          ui_props: {},
          validators: [],
          priority: 100,
          ask_if_missing: true,
        },
      },
      field_order: ["bio", "gender"],
      answers: {},
      stage: WorkflowStage.COLLECTING,
      turn_count: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      audit_log: [],
    };

    const surveyJson = mapToSurveyJS(state);

    expect(surveyJson.elements).toHaveLength(2);
    expect(surveyJson.elements[0].type).toBe("comment");
    expect(surveyJson.elements[1].type).toBe("dropdown");
    expect(surveyJson.elements[1].choices).toEqual(["Male", "Female", "Other"]);
  });

  it("should map conditional logic to visibleIf", () => {
    const state: SchemaState = {
      session_id: "test-session",
      fields: {
        is_employed: {
          key: "is_employed",
          type: FieldType.BOOLEAN,
          label: "Are you employed?",
          required: true,
          ui_props: {},
          validators: [],
          priority: 100,
          ask_if_missing: true,
        },
        employer: {
          key: "employer",
          type: FieldType.TEXT,
          label: "Employer Name",
          required: true,
          visible_if: {
            combinator: "and",
            conditions: [
              {
                field_key: "is_employed",
                operator: ConditionOperator.EQ,
                value: true,
              },
            ],
          },
          ui_props: {},
          validators: [],
          priority: 100,
          ask_if_missing: true,
        },
      },
      field_order: ["is_employed", "employer"],
      answers: {},
      stage: WorkflowStage.COLLECTING,
      turn_count: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      audit_log: [],
    };

    const surveyJson = mapToSurveyJS(state);

    expect(surveyJson.elements[1].visibleIf).toBe("{is_employed} = true");
  });

  it("should map complex conditional logic with OR combinator", () => {
    const state: SchemaState = {
      session_id: "test-session",
      fields: {
        role: {
          key: "role",
          type: FieldType.TEXT,
          label: "Role",
          required: true,
          ui_props: {},
          validators: [],
          priority: 100,
          ask_if_missing: true,
        },
        special_access: {
          key: "special_access",
          type: FieldType.BOOLEAN,
          label: "Special Access",
          required: false,
          visible_if: {
            combinator: "or",
            conditions: [
              {
                field_key: "role",
                operator: ConditionOperator.EQ,
                value: "admin",
              },
              {
                field_key: "role",
                operator: ConditionOperator.EQ,
                value: "superadmin",
              },
            ],
          },
          ui_props: {},
          validators: [],
          priority: 100,
          ask_if_missing: true,
        },
      },
      field_order: ["role", "special_access"],
      answers: {},
      stage: WorkflowStage.COLLECTING,
      turn_count: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      audit_log: [],
    };

    const surveyJson = mapToSurveyJS(state);

    expect(surveyJson.elements[1].visibleIf).toBe("{role} = 'admin' or {role} = 'superadmin'");
  });

  it("should handle IN operator correctly", () => {
    const state: SchemaState = {
      session_id: "test-session",
      fields: {
        category: {
          key: "category",
          type: FieldType.TEXT,
          label: "Category",
          required: true,
          ui_props: {},
          validators: [],
          priority: 100,
          ask_if_missing: true,
        },
        extra_info: {
          key: "extra_info",
          type: FieldType.TEXT,
          label: "Extra Info",
          required: false,
          visible_if: {
            combinator: "and",
            conditions: [
              {
                field_key: "category",
                operator: ConditionOperator.IN,
                value: ["A", "B"],
              },
            ],
          },
          ui_props: {},
          validators: [],
          priority: 100,
          ask_if_missing: true,
        },
      },
      field_order: ["category", "extra_info"],
      answers: {},
      stage: WorkflowStage.COLLECTING,
      turn_count: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      audit_log: [],
    };

    const surveyJson = mapToSurveyJS(state);

    expect(surveyJson.elements[1].visibleIf).toBe("{category} anyof ['A', 'B']");
  });
});
