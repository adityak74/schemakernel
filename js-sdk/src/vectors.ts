import { readFileSync } from "fs";
import { join } from "path";

export interface VectorGroup<T> {
  valid: T[];
  invalid: (T & { reason?: string })[];
}

export interface SchemaVectors {
  ValidatorRule: VectorGroup<any>;
  FieldDefinition: VectorGroup<any>;
}

export function loadSchemaVectors(): SchemaVectors {
  const path = join(__dirname, "../../vectors/schema_vectors.json");
  const data = readFileSync(path, "utf-8");
  return JSON.parse(data);
}
