import { Router, Request, Response } from "express";
import { WorkflowStateMachine } from "../workflow";
import { z } from "zod";
import { 
  SessionNotFound, 
  FieldValidationError, 
  PlannerOutputRejected, 
  TurnLimitExceeded 
} from "../exceptions";

const SessionSchema = z.object({
  sessionId: z.string().optional(),
});

const AnswerSchema = z.object({
  sessionId: z.string(),
  fieldKey: z.string(),
  value: z.any(),
});

const PlanSchema = z.object({
  sessionId: z.string(),
});

/**
 * Creates an Express router with SchemaKernel orchestration endpoints.
 */
export function createSchemaKernelRouter(workflow: WorkflowStateMachine): Router {
  const router = Router();

  /**
   * POST /session
   * Starts a new session.
   */
  router.post("/session", async (req: Request, res: Response) => {
    try {
      const { sessionId } = SessionSchema.parse(req.body);
      const state = await workflow.startSession(sessionId);
      res.status(201).json(state);
    } catch (error) {
      handleError(error, res);
    }
  });

  /**
   * POST /answer
   * Submits an answer for a field.
   */
  router.post("/answer", async (req: Request, res: Response) => {
    try {
      const { sessionId, fieldKey, value } = AnswerSchema.parse(req.body);
      const result = await workflow.submitAnswer(sessionId, fieldKey, value);
      
      if (!result.valid) {
        return res.status(400).json({
          error: "Validation failed",
          details: result.errors,
        });
      }

      res.status(200).json({
        success: true,
        message: "Answer recorded",
      });
    } catch (error) {
      handleError(error, res);
    }
  });

  /**
   * POST /plan
   * Triggers a planner turn to update the schema based on current answers.
   */
  router.post("/plan", async (req: Request, res: Response) => {
    try {
      const { sessionId } = PlanSchema.parse(req.body);
      const state = await workflow.runPlannerTurn(sessionId);
      res.status(200).json(state);
    } catch (error) {
      handleError(error, res);
    }
  });

  /**
   * GET /session/:sessionId
   * Retrieves the current state of a session.
   */
  router.get("/session/:sessionId", async (req: Request, res: Response) => {
    try {
      const { sessionId } = req.params;
      const state = await workflow.getState(sessionId);
      res.status(200).json(state);
    } catch (error) {
      handleError(error, res);
    }
  });

  return router;
}

function handleError(error: any, res: Response) {
  if (error instanceof z.ZodError) {
    return res.status(400).json({
      error: "Invalid request body",
      details: error.errors,
    });
  }

  if (error instanceof SessionNotFound) {
    return res.status(404).json({
      error: "Session not found",
      sessionId: error.sessionId,
    });
  }

  if (error instanceof FieldValidationError) {
    return res.status(400).json({
      error: "Field validation error",
      fieldKey: error.fieldKey,
      message: error.message,
    });
  }

  if (error instanceof TurnLimitExceeded) {
    return res.status(429).json({
      error: "Turn limit exceeded",
      message: error.message,
    });
  }

  if (error instanceof PlannerOutputRejected) {
    return res.status(502).json({
      error: "Planner output rejected",
      message: error.message,
    });
  }

  console.error("Internal Server Error:", error);
  res.status(500).json({
    error: "Internal server error",
    message: error instanceof Error ? error.message : String(error),
  });
}
