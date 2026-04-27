import json
import os
from unittest.mock import patch, MagicMock

import pytest
import instructor
from openai import OpenAI
from pydantic import BaseModel
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from schemakernel.telemetry.logging import get_logger, setup_logging
from schemakernel.telemetry.tracing import setup_tracing, get_tracer

def test_structured_logging(capsys):
    # Force JSON rendering by mocking isatty
    with patch("sys.stderr.isatty", return_value=False):
        setup_logging()
    
    logger = get_logger("test-logger")
    logger.info("test message", key="value")
    
    captured = capsys.readouterr()
    # structlog PrintLoggerFactory defaults to sys.stdout
    log_output = captured.out.strip().split('\n')[-1]
    
    try:
        data = json.loads(log_output)
        assert data["event"] == "test message"
        assert data["key"] == "value"
        assert "timestamp" in data
        assert "level" in data
    except json.JSONDecodeError:
        pytest.fail(f"Output was not valid JSON: {log_output}")

def test_tracing_setup():
    # Setup a local tracer provider and exporter
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    
    # Patch the global trace provider to use our test provider
    with patch("opentelemetry.trace.get_tracer_provider", return_value=provider):
        setup_tracing("test-service")
        
        tracer = get_tracer("test-tracer")
        with tracer.start_as_current_span("manual-span"):
            pass
            
    spans = exporter.get_finished_spans()
    assert any(span.name == "manual-span" for span in spans)

def test_instructor_instrumentation_call():
    # Verify that InstructorInstrumentor.instrument is called during setup_tracing
    with patch("openinference.instrumentation.instructor.InstructorInstrumentor.instrument") as mock_instrument:
        setup_tracing("test-service")
        mock_instrument.assert_called()

def test_log_level_env():
    from schemakernel.telemetry.logging import get_log_level
    import logging
    with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
        assert get_log_level() == logging.DEBUG
    with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}):
        assert get_log_level() == logging.ERROR
