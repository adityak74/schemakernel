import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";
import { 
    ValidationEngine, 
    WorkflowStateMachine, 
    PolicyConfigSchema, 
    InMemoryStore
} from "../../src";

const VECTORS_DIR = path.resolve(__dirname, "../../../vectors");

function loadVector(name: string) {
    const filePath = path.join(VECTORS_DIR, `${name}_vectors.json`);
    return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

describe("Parity Tests", () => {
    describe("Validation Parity", () => {
        const cases = loadVector("validation");
        cases.forEach((c: any) => {
            it(`should match python validation for: ${c.name}`, () => {
                const engine = new ValidationEngine(PolicyConfigSchema.parse({}));
                const result = engine.validateAnswer(c.field, c.answer);
                expect(result.valid).toBe(c.expected_valid);
            });
        });
    });

    describe("Condition Parity", () => {
        const cases = loadVector("condition");
        cases.forEach((c: any) => {
            it(`should match python condition evaluation for: ${c.name}`, () => {
                const defaultPolicy = PolicyConfigSchema.parse({});
                const wf = new WorkflowStateMachine(defaultPolicy, new InMemoryStore(), null as any, new ValidationEngine(defaultPolicy));
                // @ts-ignore - accessing private method for parity testing
                const result = wf._evaluateCondition(c.logic, c.answers);
                expect(result).toBe(c.expected);
            });
        });
    });

    describe("Workflow Parity", () => {
        const cases = loadVector("workflow");
        cases.forEach((c: any) => {
            it(`should match python workflow transitions for: ${c.name}`, () => {
                const store = new InMemoryStore();
                const defaultPolicy = PolicyConfigSchema.parse({});
                const wf = new WorkflowStateMachine(defaultPolicy, store, null as any, new ValidationEngine(defaultPolicy));
                
                const state = JSON.parse(JSON.stringify(c.initial_state));
                // Map snake_case to camelCase for the state object if necessary, 
                // but since we are injecting c.initial_state directly into _applyActions,
                // let's ensure it has camelCase properties if that's what JS expects.
                // The vectors were generated from Python's model_dump which is snake_case.
                
                const jsState = {
                    session_id: state.session_id,
                    stage: state.stage,
                    fields: state.fields,
                    field_order: state.field_order,
                    answers: state.answers,
                    turn_count: state.turn_count,
                    updated_at: new Date(state.updated_at),
                    audit_log: state.audit_log || []
                };

                // @ts-ignore - accessing private method for parity testing
                wf._applyActions(jsState, c.response);

                if (c.expected_fields) {
                    expect(Object.keys(jsState.fields).sort()).toEqual(c.expected_fields.sort());
                }

                if (c.expected_stage) {
                    expect(jsState.stage).toBe(c.expected_stage);
                }

                if (c.expected_order) {
                    expect(jsState.field_order).toEqual(c.expected_order);
                }
            });
        });
    });
});
