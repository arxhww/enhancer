import win32service
import win32serviceutil
from typing import Any, Dict
from .base import Action, ActionSnapshot


class ServiceAction(Action):

    def __init__(self, definition: Dict[str, Any]) -> None:
        super().__init__(definition)
        self.service_name = definition["service_name"]

    def snapshot(self) -> ActionSnapshot:
        try:
            status = win32serviceutil.QueryServiceStatus(self.service_name)[1]
            return ActionSnapshot("service", {
                "service_name": self.service_name,
                "old_status": status,
                "old_start_type": None,
            })
        except Exception:
            raise RuntimeError(f"Failed to snapshot service {self.service_name}")

    def apply(self) -> None:
        pass

    def verify(self) -> bool:
        try:
            win32serviceutil.QueryServiceStatus(self.service_name)
            return True
        except Exception:
            return False

    def rollback(self, snapshot: ActionSnapshot) -> None:
        meta = snapshot.metadata
        if meta.get("old_status") is None:
            raise RuntimeError(f"Cannot rollback service {meta.get('service_name')}")

    @classmethod
    def from_snapshot(cls, snapshot: ActionSnapshot) -> "ServiceAction":
        meta = snapshot.metadata
        return cls({
            "type": "service",
            "service_name": meta["service_name"],
        })
