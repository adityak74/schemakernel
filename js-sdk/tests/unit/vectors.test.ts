import { describe, it, expect } from "vitest";
import { loadSchemaVectors } from "@/vectors";

describe("loadSchemaVectors", () => {
  it("should load the schema vectors from the vectors directory", () => {
    const vectors = loadSchemaVectors();
    expect(vectors).toHaveProperty("ValidatorRule");
    expect(vectors).toHaveProperty("FieldDefinition");
    expect(vectors.ValidatorRule.valid).toBeInstanceOf(Array);
    expect(vectors.ValidatorRule.invalid).toBeInstanceOf(Array);
    expect(vectors.FieldDefinition.valid).toBeInstanceOf(Array);
    expect(vectors.FieldDefinition.invalid).toBeInstanceOf(Array);
  });
});
