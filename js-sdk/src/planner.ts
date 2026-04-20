import Instructor from "@instructor-ai/instructor";
import OpenAI from "openai";
import { PlannerError, PlannerRetryExhausted } from "./exceptions";
import { PlannerResponse, PlannerResponseSchema } from "./models";
import { PolicyConfig } from "./policy";

export class PlannerClient {
  private _policy: PolicyConfig;
  private _client: any;

  constructor(policy: PolicyConfig) {
    this._policy = policy;
    this._client = this._buildClient();
  }

  private _buildClient() {
    if (this._policy.provider === "openai") {
      const raw = new OpenAI();
      return Instructor({
        client: raw,
        mode: "TOOLS",
      });
    } else if (this._policy.provider === "anthropic") {
      // In JS SDK, Anthropic support might require @anthropic-ai/sdk which is not in package.json
      // For now, we throw an error as in the Python mirroring attempt where applicable.
      throw new Error(`Anthropic provider not yet implemented in JS SDK. Please use 'openai'.`);
    } else {
      throw new Error(`Unsupported provider: '${this._policy.provider}'`);
    }
  }

  async call(
    messages: { role: "user" | "assistant" | "system"; content: string }[],
    systemPrompt: string,
    options?: { maxRetries?: number }
  ): Promise<PlannerResponse> {
    const retries = options?.maxRetries ?? this._policy.max_retries;

    const chatMessages: any[] = [
      { role: "system", content: systemPrompt },
      ...messages,
    ];

    try {
      const response = await this._client.chat.completions.create({
        model: this._policy.model,
        messages: chatMessages,
        response_model: {
          schema: PlannerResponseSchema,
          name: "PlannerResponse",
        },
        max_retries: retries,
        temperature: this._policy.temperature,
      });

      return response as PlannerResponse;
    } catch (exc: any) {
      // Detect instructor retry exhaustion by name if possible
      if (exc.constructor?.name === "InstructorRetryException" || exc.name === "InstructorRetryException") {
        throw new PlannerRetryExhausted(
          `Planner failed after ${retries} retries: ${exc.message}`
        );
      }
      throw new PlannerError(`Planner call failed: ${exc.message}`);
    }
  }
}
