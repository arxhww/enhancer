import logging
import json
import sys
from typing import Dict, Any
from .base import TelemetrySink

class LoggerSink(TelemetrySink):
    def __init__(self, log_file=None):
        self._logger = logging.Logger(
            f"EnhancerCore.LoggerSink",
            level=logging.INFO
        )

        handlers = [logging.StreamHandler(sys.stdout)]
        if log_file:
            handlers.append(logging.FileHandler(log_file))

        formatter = logging.Formatter('%(message)s')
        for h in handlers:
            h.setFormatter(formatter)
            self._logger.addHandler(h)

    def emit(self, event: str, payload: Dict[str, Any]) -> None:
        level = logging.INFO
        if payload.get("result") == "failure":
            level = logging.ERROR
        elif payload.get("result") == "noop":
            level = logging.DEBUG

        log_entry = {
            "event": event,
            **payload
        }

        self._logger.log(
            level,
            json.dumps(log_entry, default=str, ensure_ascii=False)
        )
