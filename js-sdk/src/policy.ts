import { z } from "zod";
import { FieldDefinitionSchema } from "./models";

export const EscalationConditionSchema = z.object({
  field_key: z.string(),
  trigger: z.string().max(200),
});

export type EscalationCondition = z.infer<typeof EscalationConditionSchema>;

export const CompletionCriteriaSchema = z.object({
  required_fields_answered: z.array(z.string()).optional().nullable(),
  minimum_answered_count: z.number().int().min(1).optional().nullable(),
  custom_description: z.string().max(500).optional().nullable(),
});

export type CompletionCriteria = z.infer<typeof CompletionCriteriaSchema>;

export const ExceptionRuleSchema = z.object({
  name: z.string().regex(/^[A-Z0-9_]+$/).max(60),
  description: z.string().max(500),
  follow_up_fields: z.array(z.string()).default([]),
});

export type ExceptionRule = z.infer<typeof ExceptionRuleSchema>;

export const PolicyConfigSchema = z
  .object({
    baseline_questions: z.array(FieldDefinitionSchema).default([]),
    glossary: z.record(z.string()).default({}),
    exception_rules: z.array(ExceptionRuleSchema).default([]),
    prohibited_topics: z.array(z.string()).default([]),
    escalation_thresholds: z.array(EscalationConditionSchema).default([]),
    completion_criteria: CompletionCriteriaSchema.default({}),
    reasoning_style: z.string().max(500).default("balanced"),
    max_fields: z.number().int().min(1).max(100).default(20),
    max_turns: z.number().int().min(1).max(50).default(10),
    provider: z.enum(["anthropic", "openai"]).default("anthropic"),
    model: z.string().default("claude-sonnet-4-6"),
    temperature: z.number().min(0.0).max(1.0).default(0.2),
    max_retries: z.number().int().min(1).max(10).default(3),
  })
  .refine(
    (data) => {
      const keys = data.baseline_questions.map((f) => f.key);
      return new Set(keys).size === keys.length;
    },
    {
      message: "baseline_questions contains duplicate field keys",
      path: ["baseline_questions"],
    }
  );

export type PolicyConfig = z.infer<typeof PolicyConfigSchema>;
