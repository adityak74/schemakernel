export class SchemaKernelError extends Error {
  constructor(message: string) {
    super(message);
    this.name = this.constructor.name;
  }
}

// Planner layer
export class PlannerError extends SchemaKernelError {}

export class PlannerResponseError extends PlannerError {}

export class PlannerRetryExhausted extends PlannerError {}

// Validation layer
export class ValidationError extends SchemaKernelError {}

export class FieldValidationError extends ValidationError {
  constructor(public key: string, public reason: string, public value?: any) {
    super(`Field '${key}': ${reason}`);
    this.name = "FieldValidationError";
  }
}

export class PolicyViolationError extends ValidationError {}

export class PlannerOutputRejected extends ValidationError {}

// Workflow layer
export class WorkflowError extends SchemaKernelError {}

export class TurnLimitExceeded extends WorkflowError {}

export class SessionNotFound extends WorkflowError {}

export class InvalidTransition extends WorkflowError {}
