"""Run structured generation through ModelGateway without a network provider."""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import json
from pathlib import Path

from syune.model_gateway import (
    CallRole, Capability, EvidenceStore, HealthStatus, ModelCapabilities,
    ModelExecutionRequest, ModelGateway, ModelMetadata, RawProviderResponse,
)


@dataclass
class DeterministicAdapter:
    name: str = "deterministic-local"
    is_local: bool = True

    def model_metadata(self, model: str) -> ModelMetadata:
        capabilities = ModelCapabilities(frozenset({
            Capability.TEXT_GENERATION,
            Capability.STRUCTURED_OUTPUT,
            Capability.NATIVE_JSON_SCHEMA,
            Capability.USAGE_TELEMETRY,
        }), max_output_tokens=100)
        return ModelMetadata(self.name, model, "example-v1", capabilities, 0.0, 0.0)

    def capabilities(self, model: str) -> ModelCapabilities:
        return self.model_metadata(model).capabilities

    def health(self, model: str) -> HealthStatus:
        return HealthStatus.HEALTHY

    def execute(self, request: object) -> RawProviderResponse:
        text = json.dumps({"answer": "ready"})
        return RawProviderResponse(
            200, json.dumps({"output_text": text}), "example-request", "example-model",
            "example-v1", "completed", None, 4, 3, 1.0,
            sanitized_metadata={"response_text": text},
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", type=Path, required=True)
    args = parser.parse_args()
    args.state_root.mkdir(parents=True, exist_ok=True)

    store = EvidenceStore(args.state_root / "gateway.sqlite3")
    adapter = DeterministicAdapter()
    gateway = ModelGateway(
        {adapter.name: adapter}, store,
        routes=((adapter.name, "example-model"),), sleeper=lambda _: None,
    )
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
    }
    request = ModelExecutionRequest(
        "example-call", "documentation example",
        ({"role": "user", "content": "Return readiness."},),
        call_role=CallRole.DECISION,
        structured_output_schema=schema,
        preferred_model="example-model",
        exact_model=True,
    )
    result = gateway.execute(request)
    print("committed:", result.committed)
    print("value:", result.value)
    print("provider:", result.provider)
    store.close()


if __name__ == "__main__":
    main()
