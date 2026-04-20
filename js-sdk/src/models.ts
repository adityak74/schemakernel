import { z } from "zod";

export enum FieldType {
  TEXT = "text",
  NUMBER = "number",
  INTEGER = "integer",
  BOOLEAN = "boolean",
  DATE = "date",
  DATETIME = "datetime",
  SELECT = "select",
  MULTISELECT = "multiselect",
  EMAIL = "email",
  URL = "url",
  PHONE = "phone",
  TEXTAREA = "textarea",
}

export const FieldTypeSchema = z.nativeEnum(FieldType);

export enum ValidatorType {
  REQUIRED = "required",
  MIN = "min",
  MAX = "max",
  MIN_LENGTH = "min_length",
  MAX_LENGTH = "max_length",
  PATTERN = "pattern",
  ENUM_MEMBER = "enum_member",
  POSITIVE = "positive",
  NON_NEGATIVE = "non_negative",
  DATE_AFTER = "date_after",
  DATE_BEFORE = "date_before",
}

export const ValidatorTypeSchema = z.nativeEnum(ValidatorType);

export enum ActionType {
  ADD = "add",
  UPDATE = "update",
  REMOVE = "remove",
  REQUIRE = "require",
  HIDE = "hide",
  SHOW = "show",
  REORDER = "reorder",
  COMPLETE = "complete",
  ESCALATE = "escalate",
}

export const ActionTypeSchema = z.nativeEnum(ActionType);

export enum CompletionStatus {
  IN_PROGRESS = "in_progress",
  NEEDS_CLARIFICATION = "needs_clarification",
  COMPLETE = "complete",
  ESCALATE = "escalate",
}

export const CompletionStatusSchema = z.nativeEnum(CompletionStatus);

export enum WorkflowStage {
  INITIALIZED = "initialized",
  COLLECTING = "collecting",
  CLARIFYING = "clarifying",
  COMPLETE = "complete",
  ESCALATED = "escalated",
}

export const WorkflowStageSchema = z.nativeEnum(WorkflowStage);

export enum ConditionOperator {
  EQ = "eq",
  NEQ = "neq",
  GT = "gt",
  GTE = "gte",
  LT = "lt",
  LTE = "lte",
  IN = "in",
  NOT_IN = "not_in",
  IS_EMPTY = "is_empty",
  NOT_EMPTY = "not_empty",
}

export const ConditionOperatorSchema = z.nativeEnum(ConditionOperator);

export const ValidatorRuleSchema = z
  .object({
    type: ValidatorTypeSchema,
    value: z.union([z.string(), z.number(), z.boolean()]).optional().nullable(),
    message: z.string().max(300).optional().nullable(),
  })
  .refine(
    (data) => {
      const parameterized = new Set([
        ValidatorType.MIN,
        ValidatorType.MAX,
        ValidatorType.MIN_LENGTH,
        ValidatorType.MAX_LENGTH,
        ValidatorType.PATTERN,
        ValidatorType.DATE_AFTER,
        ValidatorType.DATE_BEFORE,
      ]);
      if (parameterized.has(data.type) && (data.value === undefined || data.value === null)) {
        return false;
      }
      return true;
    },
    {
      message: "Value is required for this validator type",
      path: ["value"],
    }
  );

export type ValidatorRule = z.infer<typeof ValidatorRuleSchema>;

export const ConditionSchema = z.object({
  field_key: z.string(),
  operator: ConditionOperatorSchema,
  value: z.union([z.string(), z.number(), z.boolean(), z.array(z.any())]).optional().nullable(),
});

export type Condition = z.infer<typeof ConditionSchema>;

export const ConditionalLogicSchema = z.object({
  combinator: z.enum(["and", "or"]).default("and"),
  conditions: z.array(ConditionSchema).min(1),
});

export type ConditionalLogic = z.infer<typeof ConditionalLogicSchema>;

const FORBIDDEN_UI_PATTERNS = ["__", "exec", "eval", "import", "<script", "javascript:"];

export const FieldDefinitionSchema = z
  .object({
    key: z.string().regex(/^[a-zA-Z_][a-zA-Z0-9_]{0,63}$/),
    type: FieldTypeSchema,
    label: z.string().min(1).max(200),
    description: z.string().max(1000).optional().nullable(),
    required: z.boolean().default(false),
    default: z.any().optional().nullable(),
    validators: z.array(ValidatorRuleSchema).default([]),
    ui_props: z.record(z.union([z.string(), z.number(), z.boolean()])).default({}),
    visible_if: ConditionalLogicSchema.optional().nullable(),
    ask_if_missing: z.boolean().default(true),
    follow_up_if: ConditionalLogicSchema.optional().nullable(),
    priority: z.number().int().min(0).max(9999).default(100),
    options: z.array(z.string()).optional().nullable(),
  })
  .refine(
    (data) => {
      if (data.type === FieldType.SELECT || data.type === FieldType.MULTISELECT) {
        return !!data.options && data.options.length > 0;
      }
      return true;
    },
    {
      message: "Options are required for SELECT or MULTISELECT field types",
      path: ["options"],
    }
  )
  .refine(
    (data) => {
      for (const [k, v] of Object.entries(data.ui_props)) {
        for (const pat of FORBIDDEN_UI_PATTERNS) {
          if (k.toLowerCase().includes(pat) || String(v).toLowerCase().includes(pat)) {
            return false;
          }
        }
      }
      return true;
    },
    {
      message: "ui_props contains forbidden pattern",
      path: ["ui_props"],
    }
  );

export type FieldDefinition = z.infer<typeof FieldDefinitionSchema>;

export const PlannerActionSchema = z
  .object({
    action: ActionTypeSchema,
    field_key: z.string().optional().nullable(),
    position: z.number().int().min(0).optional().nullable(),
    reason_code: z
      .string()
      .max(100)
      .regex(/^[A-Z0-9_]+$/)
      .optional()
      .nullable(),
  })
  .refine(
    (data) => {
      const fieldActions = new Set([
        ActionType.ADD,
        ActionType.UPDATE,
        ActionType.REMOVE,
        ActionType.REQUIRE,
        ActionType.HIDE,
        ActionType.SHOW,
      ]);
      if (fieldActions.has(data.action) && !data.field_key) {
        return false;
      }
      if (data.action === ActionType.REORDER && (data.position === undefined || data.position === null)) {
        return false;
      }
      return true;
    },
    {
      message: "field_key or position is required for this action",
      path: ["field_key"],
    }
  );

export type PlannerAction = z.infer<typeof PlannerActionSchema>;

export const PlannerResponseSchema = z
  .object({
    actions: z.array(PlannerActionSchema).min(1),
    fields: z.array(FieldDefinitionSchema).default([]),
    rationale: z.array(z.string()).min(1).max(20),
    completion_status: CompletionStatusSchema,
    next_prompt_context: z.string().max(2000).optional().nullable(),
  })
  .refine(
    (data) => {
      const addUpdateKeys = new Set(
        data.actions
          .filter((a) => a.action === ActionType.ADD || a.action === ActionType.UPDATE)
          .map((a) => a.field_key)
      );
      const definedKeys = new Set(data.fields.map((f) => f.key));
      for (const key of addUpdateKeys) {
        if (key && !definedKeys.has(key)) {
          return false;
        }
      }
      return true;
    },
    {
      message: "PlannerResponse: actions reference undefined fields",
      path: ["actions"],
    }
  )
  .refine(
    (data) => {
      const hasComplete = data.actions.some((a) => a.action === ActionType.COMPLETE);
      const hasEscalate = data.actions.some((a) => a.action === ActionType.ESCALATE);
      if (hasComplete && data.completion_status !== CompletionStatus.COMPLETE) {
        return false;
      }
      if (hasEscalate && data.completion_status !== CompletionStatus.ESCALATE) {
        return false;
      }
      return true;
    },
    {
      message: "Completion action must match completion status",
      path: ["completion_status"],
    }
  );

export type PlannerResponse = z.infer<typeof PlannerResponseSchema>;

export const SchemaStateSchema = z.object({
  session_id: z.string(),
  fields: z.record(FieldDefinitionSchema).default({}),
  field_order: z.array(z.string()).default([]),
  answers: z.record(z.any()).default({}),
  stage: WorkflowStageSchema.default(WorkflowStage.INITIALIZED),
  turn_count: z.number().int().default(0),
  created_at: z.string().datetime().or(z.date()),
  updated_at: z.string().datetime().or(z.date()),
  audit_log: z.array(z.record(z.any())).default([]),
});

export type SchemaState = z.infer<typeof SchemaStateSchema>;
