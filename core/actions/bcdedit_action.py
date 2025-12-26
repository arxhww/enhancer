import subprocess
import re
from typing import Any, Dict, Optional
from .base import Action, ActionSnapshot


class BcdEditAction(Action):
    """
    Action to modify Boot Configuration Data (BCD).
    Tier 2: Reboot required.
    Harden: Explicit handling of missing values (delete on rollback).
    """
    
    def __init__(self, definition: Dict[str, Any]) -> None:
        super().__init__(definition)
        self.id_type = definition["id_type"] 
        self.datatype = definition["datatype"]
        
        self.value = definition.get("value") 
        self.delete_value = definition.get("delete", False)

    def _exec_bcdedit(self, args: list) -> str:
        result = subprocess.run(
            ["bcdedit.exe"] + args,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode != 0:
             raise RuntimeError(f"bcdedit failed with code {result.returncode}: {result.stderr}")
        return result.stdout

    def _find_value_in_enum(self, output: str, datatype: str) -> Optional[str]:
        pattern = re.compile(rf"^{re.escape(datatype)}\s+(.*)$", re.MULTILINE)
        match = pattern.search(output)
        if match:
            val = match.group(1).strip()
            return val if val else None 
        return None

    def snapshot(self) -> ActionSnapshot:
        output = self._exec_bcdedit(["/enum", self.id_type])
        old_value = self._find_value_in_enum(output, self.datatype)
        
        return ActionSnapshot("bcdedit", {
            "id_type": self.id_type,
            "datatype": self.datatype,
            "old_value": old_value 
        })

    def apply(self) -> None:
        if self.delete_value:
            self._exec_bcdedit(["/deletevalue", self.id_type, self.datatype])
        elif self.value is not None:
            self._exec_bcdedit(["/set", self.id_type, self.datatype, self.value])

    def verify(self) -> bool:
        try:
            output = self._exec_bcdedit(["/enum", self.id_type])
            current_stored = self._find_value_in_enum(output, self.datatype)
            
            if self.delete_value:
                return current_stored is None
            
            return current_stored == self.value
        except Exception as e:
            raise RuntimeError(f"BCD verification failed: {e}")

    def rollback(self, snapshot: ActionSnapshot) -> None:
        meta = snapshot.metadata
        old_val = meta.get("old_value")
        
        if old_val is None:
            try:
                self._exec_bcdedit(["/deletevalue", meta["id_type"], meta["datatype"]])
            except Exception:
                pass
        else:
            self._exec_bcdedit(["/set", meta["id_type"], meta["datatype"], old_val])

    def get_description(self) -> str:
        if self.delete_value:
            return f"BCD Delete {self.datatype}"
        return f"BCD Set {self.datatype} = {self.value}"

    @classmethod
    def from_snapshot(cls, snapshot: ActionSnapshot) -> 'BcdEditAction':
        meta = snapshot.metadata
        old_val = meta.get("old_value")
        
        definition = {
            "type": "bcdedit",
            "id_type": meta["id_type"],
            "datatype": meta["datatype"],
            "delete": (old_val is None), 
            "value": old_val
        }
        return cls(definition)