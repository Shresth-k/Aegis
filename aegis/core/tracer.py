import json
import os
from datetime import datetime, timezone
from typing import Any, Dict
from aegis.config import settings

class LocalTracer:
    """Lightweight, zero-overhead JSONL tracer recording step-by-step incident trajectories."""

    def __init__(self, trace_file: str = settings.TRACE_LOG_PATH):
        self.trace_file = trace_file

    def log_event(self, incident_id: str, step: str, event_type: str, data: Dict[str, Any]):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "incident_id": incident_id,
            "step": step,
            "event_type": event_type,
            "data": data,
        }
        try:
            with open(self.trace_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            if settings.DEBUG:
                print(f"[Tracer Error] Failed to write event: {e}")

    def get_incident_trace(self, incident_id: str) -> list[Dict[str, Any]]:
        if not os.path.exists(self.trace_file):
            return []
        trace = []
        with open(self.trace_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    if entry.get("incident_id") == incident_id:
                        trace.append(entry)
        return trace

tracer = LocalTracer()
