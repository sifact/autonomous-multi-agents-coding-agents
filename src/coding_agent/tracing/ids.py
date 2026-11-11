"""Trace and span ids that ignore ``random.seed``.

OpenTelemetry's default generator draws from the global ``random`` module. The benchmark
runner reseeds it before every task (for reproducibility), which would give every task
the same trace id and merge all runs into one trace.
"""
import secrets

from opentelemetry.sdk.trace.id_generator import IdGenerator


class SecureIdGenerator(IdGenerator):
    def generate_span_id(self) -> int:
        return secrets.randbits(64) or 1

    def generate_trace_id(self) -> int:
        return secrets.randbits(128) or 1
