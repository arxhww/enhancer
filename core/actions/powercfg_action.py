import subprocess
import re
from typing import Any, Dict, Tuple
from .base import Action, ActionSnapshot


class PowerCfgAction(Action):
    
    def __init__(self, definition: Dict[str, Any]) -> None:
        super().__init__(definition)
        self.scheme_guid = definition["scheme_guid"]
        self.subgroup_guid = definition["subgroup_guid"]
        self.setting_guid = definition["setting_guid"]
        self.value_ac = definition.get("value_ac")
        self.value_dc = definition.get("value_dc")

    def _exec_powercfg(self, args: list) -> str:
        result = subprocess.run(
            ["powercfg.exe"] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout

    def _parse_query_values(self, output: str) -> Tuple[int, int]:
        # Pattern for AC: "AC Setting Index: 0x0000000a"
        ac_match = re.search(r"AC Setting Index:\s*0x([0-9a-fA-F]+)", output)
        # Pattern for DC: "DC Setting Index: 0x00000005"
        dc_match = re.search(r"DC Setting Index:\s*0x([0-9a-fA-F]+)", output)
        
        if not ac_match or not dc_match:
            raise ValueError(
                f"Failed to parse powercfg output for {self.setting_guid}. "
                "Ensure GUIDs are correct and scheme exists."
            )
            
        return (
            int(ac_match.group(1), 16),
            int(dc_match.group(1), 16)
        )

    def snapshot(self) -> ActionSnapshot:
        output = self._exec_powercfg([
            "/query", self.scheme_guid, self.subgroup_guid, self.setting_guid
        ])
        
        old_ac, old_dc = self._parse_query_values(output)
        
        return ActionSnapshot("powercfg", {
            "scheme_guid": self.scheme_guid,
            "subgroup_guid": self.subgroup_guid,
            "setting_guid": self.setting_guid,
            "old_value_ac": old_ac,
            "old_value_dc": old_dc 
        })

    def apply(self) -> None:
        if self.value_ac is not None:
            self._exec_powercfg([
                "/setacvalueindex",
                self.scheme_guid, self.subgroup_guid, self.setting_guid,
                str(self.value_ac)
            ])
        
        if self.value_dc is not None:
            self._exec_powercfg([
                "/setdcvalueindex",
                self.scheme_guid, self.subgroup_guid, self.setting_guid,
                str(self.value_dc)
            ])

    def verify(self) -> bool:
        try:
            output = self._exec_powercfg([
                "/query", self.scheme_guid, self.subgroup_guid, self.setting_guid
            ])
            current_ac, current_dc = self._parse_query_values(output)
            
            if self.value_ac is not None and current_ac != self.value_ac:
                return False
            
            if self.value_dc is not None and current_dc != self.value_dc:
                return False
                
            return True
        except Exception:
            raise

    def rollback(self, snapshot: ActionSnapshot) -> None:
        meta = snapshot.metadata
        
        self._exec_powercfg([
            "/setacvalueindex",
            meta["scheme_guid"], meta["subgroup_guid"], meta["setting_guid"],
            str(meta["old_value_ac"])
        ])
        
        self._exec_powercfg([
            "/setdcvalueindex",
            meta["scheme_guid"], meta["subgroup_guid"], meta["setting_guid"],
            str(meta["old_value_dc"])
        ])

    def get_description(self) -> str:
        parts = []
        if self.value_ac is not None: parts.append(f"AC:{self.value_ac}")
        if self.value_dc is not None: parts.append(f"DC:{self.value_dc}")
        return f"PowerCfg {self.setting_guid} -> {','.join(parts)}"

    @classmethod
    def from_snapshot(cls, snapshot: ActionSnapshot) -> 'PowerCfgAction':
        meta = snapshot.metadata
        definition = {
            "type": "powercfg",
            "scheme_guid": meta["scheme_guid"],
            "subgroup_guid": meta["subgroup_guid"],
            "setting_guid": meta["setting_guid"],
            "value_ac": meta["old_value_ac"],
            "value_dc": meta["old_value_dc"]
        }
        return cls(definition)