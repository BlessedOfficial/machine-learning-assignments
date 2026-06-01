"""Export JSON Schema for every agent message payload type."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.protocol import PAYLOAD_SCHEMAS, MessageType

OUT_DIR = ROOT / "data" / "schemas"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index: dict[str, str] = {}

    for message_type, schema_cls in PAYLOAD_SCHEMAS.items():
        filename = f"{message_type.value}.schema.json"
        path = OUT_DIR / filename
        path.write_text(
            json.dumps(schema_cls.model_json_schema(), indent=2),
            encoding="utf-8",
        )
        index[message_type.value] = filename

    envelope_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "AgentEnvelope",
        "description": "A2A envelope: sender, recipient, correlation_id, typed payload",
        "type": "object",
        "required": [
            "message_id",
            "correlation_id",
            "timestamp",
            "sender",
            "recipient",
            "message_type",
            "payload",
        ],
        "properties": {
            "message_id": {"type": "string", "format": "uuid"},
            "correlation_id": {"type": "string", "format": "uuid"},
            "timestamp": {"type": "string", "format": "date-time"},
            "sender": {
                "enum": ["orchestrator", "retriever", "synthesizer", "safety_reviewer"]
            },
            "recipient": {
                "enum": ["orchestrator", "retriever", "synthesizer", "safety_reviewer"]
            },
            "message_type": {"enum": list(index.keys())},
            "payload": {
                "description": "Must validate against payload schema for message_type",
            },
        },
        "payloadSchemas": index,
    }
    (OUT_DIR / "agent_envelope.schema.json").write_text(
        json.dumps(envelope_schema, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(index) + 1} schemas to {OUT_DIR}")


if __name__ == "__main__":
    main()
