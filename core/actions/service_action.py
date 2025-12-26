import win32service
import win32serviceutil
from typing import Any, Dict
from .base import Action, ActionSnapshot

class ServiceAction(Action):
    
    START_TYPE_MAP = {
        "boot": win32service.SERVICE_BOOT_START,
        "system": win32service.SERVICE_SYSTEM_START,
        "auto": win32service.SERVICE_AUTO_START,
        "manual": win32service.SERVICE_DEMAND_START,
        "disabled": win32service.SERVICE_DISABLED
    }
    
    START_TYPE_STR_MAP = {v: k for k, v in START_TYPE_MAP.items()}

    def __init__(self, definition: Dict[str, Any]) -> None:
        super().__init__(definition)
        self.service_name = definition["service_name"]
        
        self.desired_state = definition.get("state") # 'running', 'stopped'
        if self.desired_state not in ["running", "stopped", None]:
            raise ValueError(f"Invalid service state: {self.desired_state}")

        raw_start_type = definition.get("start_type")
        self.desired_start_type_const = None
        
        if raw_start_type:
            if isinstance(raw_start_type, int):
                self.desired_start_type_const = raw_start_type
            elif isinstance(raw_start_type, str):
                if raw_start_type.lower() not in self.START_TYPE_MAP:
                    raise ValueError(f"Invalid start_type string: {raw_start_type}")
                self.desired_start_type_const = self.START_TYPE_MAP[raw_start_type.lower()]

    def _get_service_info(self) -> Dict[str, Any]:
        try:
            status = win32serviceutil.QueryServiceStatus(self.service_name)[1]
            
            hscm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_CONNECT)
            hs = win32service.OpenService(hscm, self.service_name, win32service.SERVICE_QUERY_CONFIG)
            config = win32service.QueryServiceConfig(hs)
            
            win32service.CloseService(hs)
            win32service.CloseServiceManager(hscm)
            
            return {
                "status_code": status,
                "start_type_const": config[2] # Store as integer constant
            }
        except Exception as e:
            raise RuntimeError(f"Failed to query service '{self.service_name}': {e}")

    def snapshot(self) -> ActionSnapshot:
        info = self._get_service_info()
        return ActionSnapshot("service", {
            "service_name": self.service_name,
            "old_status": info["status_code"],
            "old_start_type": info["start_type_const"]
        })

    def apply(self) -> None:
        if self.desired_start_type_const is not None:
            win32serviceutil.SetServiceStartType(
                self.service_name, 
                self.desired_start_type_const
            )
        
        if self.desired_state == "running":
            if win32serviceutil.QueryServiceStatus(self.service_name)[1] != win32service.SERVICE_RUNNING:
                win32serviceutil.StartService(self.service_name)
        elif self.desired_state == "stopped":
            if win32serviceutil.QueryServiceStatus(self.service_name)[1] != win32service.SERVICE_STOPPED:
                win32service.StopService(self.service_name)

    def verify(self) -> bool:
        info = self._get_service_info()
        
        if self.desired_start_type_const is not None:
            if info["start_type_const"] != self.desired_start_type_const:
                return False
        
        if self.desired_state == "running":
            return info["status_code"] == win32service.SERVICE_RUNNING
        elif self.desired_state == "stopped":
            return info["status_code"] == win32service.SERVICE_STOPPED
            
        return True

    def rollback(self, snapshot: ActionSnapshot) -> None:
        meta = snapshot.metadata
        
        if meta.get("old_start_type") is not None:
            win32serviceutil.SetServiceStartType(
                meta["service_name"], 
                meta["old_start_type"] 
            )

        if meta.get("old_status") == win32service.SERVICE_RUNNING:
            try:
                win32service.StartService(meta["service_name"])
            except Exception:
                pass 
        elif meta.get("old_status") == win32service.SERVICE_STOPPED:
            try:
                win32service.StopService(meta["service_name"])
            except Exception:
                pass

    def get_description(self) -> str:
        type_str = self.START_TYPE_STR_MAP.get(self.desired_start_type_const, "None")
        return f"Service {self.service_name}: State={self.desired_state}, Type={type_str}"

    @classmethod
    def from_snapshot(cls, snapshot: ActionSnapshot) -> 'ServiceAction':
        meta = snapshot.metadata
        definition = {
            "type": "service",
            "service_name": meta["service_name"],
            "state": "running" if meta["old_status"] == win32service.SERVICE_RUNNING else "stopped",
            "start_type": meta["old_start_type"]
        }
        return cls(definition)