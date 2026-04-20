import { describe, it, expect, vi, beforeEach } from "vitest";
import { createSchemaKernelRouter } from "../../src/middleware/express";
import { WorkflowStateMachine } from "../../src/workflow";
import { Request, Response } from "express";

describe("Express Middleware", () => {
  let mockWorkflow: any;
  let router: any;

  beforeEach(() => {
    mockWorkflow = {
      startSession: vi.fn(),
      submitAnswer: vi.fn(),
      runPlannerTurn: vi.fn(),
      getState: vi.fn(),
    };
    router = createSchemaKernelRouter(mockWorkflow as unknown as WorkflowStateMachine);
  });

  const createMockRes = () => {
    const res: any = {};
    res.status = vi.fn().mockReturnValue(res);
    res.json = vi.fn().mockReturnValue(res);
    return res;
  };

  it("should handle POST /session", async () => {
    const req = { body: { sessionId: "test-sid" } } as Request;
    const res = createMockRes();
    
    mockWorkflow.startSession.mockResolvedValue({ session_id: "test-sid" });

    // Find the route handler for POST /session
    const handler = router.stack.find((s: any) => s.route?.path === "/session" && s.route?.methods.post).route.stack[0].handle;
    
    await handler(req, res);

    expect(mockWorkflow.startSession).toHaveBeenCalledWith("test-sid");
    expect(res.status).toHaveBeenCalledWith(201);
    expect(res.json).toHaveBeenCalledWith({ session_id: "test-sid" });
  });

  it("should handle POST /answer with valid data", async () => {
    const req = { body: { sessionId: "sid", fieldKey: "name", value: "Alice" } } as Request;
    const res = createMockRes();
    
    mockWorkflow.submitAnswer.mockResolvedValue({ valid: true });

    const handler = router.stack.find((s: any) => s.route?.path === "/answer" && s.route?.methods.post).route.stack[0].handle;
    
    await handler(req, res);

    expect(mockWorkflow.submitAnswer).toHaveBeenCalledWith("sid", "name", "Alice");
    expect(res.status).toHaveBeenCalledWith(200);
    expect(res.json).toHaveBeenCalledWith({ success: true, message: "Answer recorded" });
  });

  it("should handle POST /answer with invalid data", async () => {
    const req = { body: { sessionId: "sid", fieldKey: "age", value: "not-a-number" } } as Request;
    const res = createMockRes();
    
    mockWorkflow.submitAnswer.mockResolvedValue({ valid: false, errors: [{ reason: "Must be a number" }] });

    const handler = router.stack.find((s: any) => s.route?.path === "/answer" && s.route?.methods.post).route.stack[0].handle;
    
    await handler(req, res);

    expect(res.status).toHaveBeenCalledWith(400);
    expect(res.json).toHaveBeenCalledWith(expect.objectContaining({ error: "Validation failed" }));
  });

  it("should handle POST /plan", async () => {
    const req = { body: { sessionId: "sid" } } as Request;
    const res = createMockRes();
    
    mockWorkflow.runPlannerTurn.mockResolvedValue({ session_id: "sid", turn_count: 1 });

    const handler = router.stack.find((s: any) => s.route?.path === "/plan" && s.route?.methods.post).route.stack[0].handle;
    
    await handler(req, res);

    expect(mockWorkflow.runPlannerTurn).toHaveBeenCalledWith("sid");
    expect(res.status).toHaveBeenCalledWith(200);
    expect(res.json).toHaveBeenCalledWith({ session_id: "sid", turn_count: 1 });
  });

  it("should handle invalid request body with 400", async () => {
    const req = { body: {} } as Request; // Missing sessionId for /plan
    const res = createMockRes();
    
    const handler = router.stack.find((s: any) => s.route?.path === "/plan" && s.route?.methods.post).route.stack[0].handle;
    
    await handler(req, res);

    expect(res.status).toHaveBeenCalledWith(400);
    expect(res.json).toHaveBeenCalledWith(expect.objectContaining({ error: "Invalid request body" }));
  });
});
