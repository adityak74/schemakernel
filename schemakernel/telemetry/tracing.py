import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from contextlib import contextmanager
from opentelemetry import context as otel_context
from openinference.instrumentation.instructor import InstructorInstrumentor
from openinference.semconv.trace import SpanAttributes

def setup_tracing(service_name: Optional[str] = None):
    """
    Setup OpenTelemetry tracing and instrument instructor.
    """
    if service_name is None:
        service_name = os.getenv("OTEL_SERVICE_NAME", "schemakernel")
        
    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    
    # Set the global tracer provider
    trace.set_tracer_provider(provider)
    
    # Instrument instructor calls
    # InstructorInstrumentor from openinference-instrumentation-instructor
    # automatically handles multiple instrument() calls usually, but we call it here.
    InstructorInstrumentor().instrument()

def get_tracer(name: str) -> trace.Tracer:
    """Return an OpenTelemetry tracer."""
    return trace.get_tracer(name)

@contextmanager
def session_context(session_id: str):
    """
    Context manager to set the session_id in the OpenTelemetry context.
    This session_id is used by OpenInference instrumentation to tag spans.
    """
    token = otel_context.attach(otel_context.set_value(SpanAttributes.SESSION_ID, session_id))
    try:
        yield
    finally:
        otel_context.detach(token)
