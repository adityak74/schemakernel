import { describe, it, expect } from "vitest";
import { 
  ValidatorRuleSchema, 
  FieldDefinitionSchema,
} from "@/models";
import { loadSchemaVectors } from "@/vectors";

const vectors = loadSchemaVectors();

describe("ValidatorRuleSchema", () => {
  it("should validate valid ValidatorRule vectors", () => {
    for (const vector of vectors.ValidatorRule.valid) {
      const result = ValidatorRuleSchema.safeParse(vector);
      expect(result.success).toBe(true);
    }
  });

  it("should reject invalid ValidatorRule vectors", () => {
    for (const vector of vectors.ValidatorRule.invalid) {
      const result = ValidatorRuleSchema.safeParse(vector);
      expect(result.success).toBe(false);
    }
  });
});

describe("FieldDefinitionSchema", () => {
  it("should validate valid FieldDefinition vectors", () => {
    for (const vector of vectors.FieldDefinition.valid) {
      const result = FieldDefinitionSchema.safeParse(vector);
      expect(result.success, `Failed on valid vector: ${JSON.stringify(vector)}`).toBe(true);
    }
  });

  it("should reject invalid FieldDefinition vectors", () => {
    for (const vector of vectors.FieldDefinition.invalid) {
      const result = FieldDefinitionSchema.safeParse(vector);
      expect(result.success, `Should have failed on invalid vector: ${JSON.stringify(vector)}`).toBe(false);
    }
  });
});
