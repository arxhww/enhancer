from typing import Protocol, Dict, Any

class TelemetrySink(Protocol):
    def emit(self, event: str, payload: Dict[str, Any]) -> None:
        pass
