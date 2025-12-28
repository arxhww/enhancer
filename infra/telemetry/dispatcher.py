from typing import List, Dict, Any
from .base import TelemetrySink

class TelemetryManager:
    def __init__(self):
        self._sinks: List[TelemetrySink] = []

    def register_sink(self, sink: TelemetrySink) -> None:
        self._sinks.append(sink)

    def dispatch(self, event: str, payload: Dict[str, Any]) -> None:
        for sink in self._sinks:
            try:
                sink.emit(event, payload)
            except Exception:
                pass

manager = TelemetryManager()
