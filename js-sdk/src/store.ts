import { SchemaState, PlannerTrace, CompletionOutcome } from "./models";
import { SessionNotFound } from "./exceptions";

export interface StorageBackend {
  saveState(state: SchemaState): Promise<void>;
  loadState(session_id: string): Promise<SchemaState>;
  deleteState(session_id: string): Promise<void>;
  saveTrace(trace: PlannerTrace): Promise<void>;
  listTraces(session_id: string): Promise<PlannerTrace[]>;
  saveOutcome(outcome: CompletionOutcome): Promise<void>;
  loadOutcome(session_id: string): Promise<CompletionOutcome>;
}

export class InMemoryStore implements StorageBackend {
  private states: Map<string, SchemaState> = new Map();
  private traces: Map<string, PlannerTrace[]> = new Map();
  private outcomes: Map<string, CompletionOutcome> = new Map();

  async saveState(state: SchemaState): Promise<void> {
    this.states.set(state.session_id, structuredClone(state));
  }

  async loadState(session_id: string): Promise<SchemaState> {
    const state = this.states.get(session_id);
    if (!state) {
      throw new SessionNotFound(`Session '${session_id}' not found`);
    }
    return structuredClone(state);
  }

  async deleteState(session_id: string): Promise<void> {
    this.states.delete(session_id);
    this.traces.delete(session_id);
    this.outcomes.delete(session_id);
  }

  async saveTrace(trace: PlannerTrace): Promise<void> {
    if (!this.traces.has(trace.session_id)) {
      this.traces.set(trace.session_id, []);
    }
    this.traces.get(trace.session_id)!.push(structuredClone(trace));
  }

  async listTraces(session_id: string): Promise<PlannerTrace[]> {
    return structuredClone(this.traces.get(session_id) || []);
  }

  async saveOutcome(outcome: CompletionOutcome): Promise<void> {
    this.outcomes.set(outcome.session_id, structuredClone(outcome));
  }

  async loadOutcome(session_id: string): Promise<CompletionOutcome> {
    const outcome = this.outcomes.get(session_id);
    if (!outcome) {
      throw new SessionNotFound(`No outcome for session '${session_id}'`);
    }
    return structuredClone(outcome);
  }
}
