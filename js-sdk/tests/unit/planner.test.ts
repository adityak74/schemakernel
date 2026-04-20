import { describe, it, expect, vi, beforeEach } from "vitest";
import { PlannerClient } from "../../src/planner";
import { PolicyConfig } from "../../src/policy";
import { ActionType, CompletionStatus } from "../../src/models";
import Instructor from "@instructor-ai/instructor";

vi.mock("openai");
vi.mock("@instructor-ai/instructor", () => {
  const mockCreate = vi.fn();
  return {
    default: vi.fn(() => ({
      chat: {
        completions: {
          create: mockCreate,
        },
      },
    })),
  };
});

describe("PlannerClient", () => {
  let policy: PolicyConfig;
  let client: PlannerClient;

  beforeEach(() => {
    vi.clearAllMocks();
    policy = {
      provider: "openai",
      model: "gpt-4",
      max_retries: 3,
      temperature: 0.2,
      baseline_questions: [],
      glossary: {},
      exception_rules: [],
      prohibited_topics: [],
      escalation_thresholds: [],
      completion_criteria: {},
      reasoning_style: "balanced",
      max_fields: 20,
      max_turns: 10,
    } as any;
    client = new PlannerClient(policy);
  });

  it("should call instructor with correct parameters", async () => {
    const mockResponse = {
      actions: [{ action: ActionType.COMPLETE }],
      fields: [],
      rationale: ["Done"],
      completion_status: CompletionStatus.COMPLETE,
    };

    const mockedInstructor = vi.mocked(Instructor);
    const mockCreate = (mockedInstructor.mock.results[0].value as any).chat.completions.create;
    mockCreate.mockResolvedValue(mockResponse);

    const messages = [{ role: "user", content: "Hello" }];
    const systemPrompt = "You are a helpful assistant";

    const response = await client.call(messages as any, systemPrompt);

    expect(response).toEqual(mockResponse);
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        model: "gpt-4",
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: "Hello" },
        ],
        temperature: 0.2,
        max_retries: 3,
      })
    );
  });

  it("should throw PlannerError on failure", async () => {
    const mockedInstructor = vi.mocked(Instructor);
    const mockCreate = (mockedInstructor.mock.results[0].value as any).chat.completions.create;
    mockCreate.mockRejectedValue(new Error("API Error"));

    await expect(client.call([], "system")).rejects.toThrow("Planner call failed: API Error");
  });
});
