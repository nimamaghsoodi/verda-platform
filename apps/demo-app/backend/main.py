"""
Demo app backend — FastAPI + OpenTelemetry
Exposes endpoints for simulating success, error, and slow-request scenarios.
Traces → OTEL Collector → Tempo
Metrics → Prometheus endpoint (scraped by kube-prometheus-stack)
Logs → stdout with trace_id injected (collected by Promtail → Loki)
"""

import asyncio
import logging
import os
import time
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import BaseModel

# ─── OpenTelemetry Setup ──────────────────────────────────────────────────────

OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "demo-app")
SERVICE_VERSION = os.getenv("OTEL_RESOURCE_ATTRIBUTES", "service.version=dev").split("service.version=")[-1].split(",")[0]

resource = Resource.create({
    "service.name": SERVICE_NAME,
    "service.version": SERVICE_VERSION,
    "deployment.environment": os.getenv("DEPLOYMENT_ENV", "local"),
})

# Traces
tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True))
)
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer(SERVICE_NAME)

# Metrics
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint=OTEL_ENDPOINT, insecure=True),
    export_interval_millis=15_000,
)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(SERVICE_NAME)

# Configure logging BEFORE LoggingInstrumentor so our formatter is not overridden.
# basicConfig only takes effect if the root logger has no handlers yet.
_json_formatter = logging.Formatter(
    '{"time":"%(asctime)s","level":"%(levelname)s",'
    '"trace_id":"%(otelTraceID)s","span_id":"%(otelSpanID)s","message":"%(message)s"}'
)
_handler = logging.StreamHandler()
_handler.setFormatter(_json_formatter)
logging.root.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "INFO")))
logging.root.addHandler(_handler)

# LoggingInstrumentor injects otelTraceID / otelSpanID attributes onto every
# LogRecord while inside an active span — no format change needed.
LoggingInstrumentor().instrument(set_logging_format=False)

# Silence uvicorn's own access logger so only our structured lines reach Loki
logging.getLogger("uvicorn.access").propagate = False

logger = logging.getLogger(__name__)

# ─── Custom Metrics ──────────────────────────────────────────────────────────

scenario_counter = meter.create_counter(
    "demo_scenario_total",
    description="Total simulated scenarios triggered",
    unit="1",
)
scenario_duration = meter.create_histogram(
    "demo_scenario_duration_seconds",
    description="Duration of simulated scenarios",
    unit="s",
)

# ─── FastAPI App ─────────────────────────────────────────────────────────────

app = FastAPI(title="Verda Demo App", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)


# ─── Models ──────────────────────────────────────────────────────────────────

class SimulateRequest(BaseModel):
    delay_ms: int = 0          # artificial delay in milliseconds (for slow scenario)
    error_message: str = "Simulated error"


class SimulateResponse(BaseModel):
    scenario: str
    status: str
    trace_id: str
    span_id: str
    duration_ms: float
    message: str


def current_trace_ids() -> tuple[str, str]:
    span = trace.get_current_span()
    ctx = span.get_span_context()
    return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": SERVICE_NAME}


@app.post("/api/simulate/success", response_model=SimulateResponse)
async def simulate_success(body: SimulateRequest):
    start = time.perf_counter()

    with tracer.start_as_current_span("simulate-success") as span:
        span.set_attribute("scenario.type", "success")
        span.set_attribute("scenario.delay_ms", body.delay_ms)

        if body.delay_ms > 0:
            await asyncio.sleep(body.delay_ms / 1000)

        # Nested child span to show span hierarchy in Tempo
        with tracer.start_as_current_span("process-business-logic") as child:
            child.set_attribute("result", "ok")
            await asyncio.sleep(0.01)

        tid, sid = current_trace_ids()
        duration = (time.perf_counter() - start) * 1000

        logger.info("Scenario success completed", extra={"scenario": "success", "duration_ms": duration})
        scenario_counter.add(1, {"scenario": "success", "status": "ok"})
        scenario_duration.record(duration / 1000, {"scenario": "success"})

        return SimulateResponse(
            scenario="success",
            status="ok",
            trace_id=tid,
            span_id=sid,
            duration_ms=round(duration, 2),
            message="Request completed successfully.",
        )


@app.post("/api/simulate/error", response_model=SimulateResponse)
async def simulate_error(body: SimulateRequest):
    start = time.perf_counter()

    with tracer.start_as_current_span("simulate-error") as span:
        span.set_attribute("scenario.type", "error")
        span.set_attribute("error.message", body.error_message)

        try:
            # Intentionally raises to create an error span
            raise ValueError(body.error_message)
        except ValueError as exc:
            span.record_exception(exc)
            span.set_status(trace.StatusCode.ERROR, str(exc))

            tid, sid = current_trace_ids()
            duration = (time.perf_counter() - start) * 1000

            logger.error(
                "Scenario error triggered",
                extra={"scenario": "error", "error": str(exc), "duration_ms": duration},
            )
            scenario_counter.add(1, {"scenario": "error", "status": "error"})
            scenario_duration.record(duration / 1000, {"scenario": "error"})

            # Return 500 so the Grafana error rate metric fires
            raise HTTPException(
                status_code=500,
                detail={
                    "scenario": "error",
                    "status": "error",
                    "trace_id": tid,
                    "span_id": sid,
                    "duration_ms": round(duration, 2),
                    "message": str(exc),
                },
            )


@app.post("/api/simulate/slow", response_model=SimulateResponse)
async def simulate_slow(body: SimulateRequest):
    delay_ms = max(body.delay_ms, 2000)  # minimum 2 s to make it visible in Tempo
    start = time.perf_counter()

    with tracer.start_as_current_span("simulate-slow") as span:
        span.set_attribute("scenario.type", "slow")
        span.set_attribute("scenario.delay_ms", delay_ms)

        with tracer.start_as_current_span("slow-database-query") as db_span:
            db_span.set_attribute("db.system", "postgresql")
            db_span.set_attribute("db.statement", "SELECT * FROM heavy_table WHERE unindexed_col = ?")
            await asyncio.sleep(delay_ms / 1000)

        tid, sid = current_trace_ids()
        duration = (time.perf_counter() - start) * 1000

        logger.warning(
            "Slow scenario completed",
            extra={"scenario": "slow", "delay_ms": delay_ms, "duration_ms": duration},
        )
        scenario_counter.add(1, {"scenario": "slow", "status": "ok"})
        scenario_duration.record(duration / 1000, {"scenario": "slow"})

        return SimulateResponse(
            scenario="slow",
            status="ok",
            trace_id=tid,
            span_id=sid,
            duration_ms=round(duration, 2),
            message=f"Request intentionally delayed {delay_ms} ms.",
        )


@app.get("/api/history")
async def history():
    """Returns static demo history — in production this would query a DB."""
    return {
        "message": "History endpoint — extend with a real store if needed.",
        "hint": "Use the trace_id from previous calls to look up traces in Grafana → Explore → Tempo.",
    }
