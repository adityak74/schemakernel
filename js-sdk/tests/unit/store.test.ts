import { describe, it, expect, beforeEach } from "vitest";
import { InMemoryStore } from "../../src/store";
import { WorkflowStage, SchemaState } from "../../src/models";
import { SessionNotFound } from "../../src/exceptions";

describe("InMemoryStore", () => {
  let store: InMemoryStore;

  beforeEach(() => {
    store = new InMemoryStore();
  });

  it("should save and load state", async () => {
    const state: SchemaState = {
      session_id: "session-1",
      fields: {},
      field_order: [],
      answers: {},
      stage: WorkflowStage.INITIALIZED,
      turn_count: 0,
      created_at: new Date(),
      updated_at: new Date(),
      audit_log: [],
    };

    await store.saveState(state);
    const loaded = await store.loadState("session-1");
    expect(loaded.session_id).toBe("session-1");
  });

  it("should perform deep copies when saving and loading", async () => {
    const state: SchemaState = {
      session_id: "session-1",
      fields: {},
      field_order: [],
      answers: { test: "original" },
      stage: WorkflowStage.INITIALIZED,
      turn_count: 0,
      created_at: new Date(),
      updated_at: new Date(),
      audit_log: [],
    };

    await store.saveState(state);
    
    // Modify original
    state.answers.test = "modified";
    
    const loaded = await store.loadState("session-1");
    expect(loaded.answers.test).toBe("original");
    
    // Modify loaded
    loaded.answers.test = "modified_again";
    const loaded2 = await store.loadState("session-1");
    expect(loaded2.answers.test).toBe("original");
  });

  it("should throw SessionNotFound when loading missing session", async () => {
    await expect(store.loadState("missing")).rejects.toThrow(SessionNotFound);
  });

  it("should delete state", async () => {
    const state: SchemaState = {
      session_id: "session-1",
      fields: {},
      field_order: [],
      answers: {},
      stage: WorkflowStage.INITIALIZED,
      turn_count: 0,
      created_at: new Date(),
      updated_at: new Date(),
      audit_log: [],
    };
    await store.saveState(state);
    await store.deleteState("session-1");
    await expect(store.loadState("session-1")).rejects.toThrow(SessionNotFound);
  });
});
