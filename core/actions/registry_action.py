from typing import Any, Dict, Tuple
from .base import Action, ActionSnapshot
from .. import registry


class RegistryAction(Action):

    def __init__(self, definition: Dict[str, Any]):
        super().__init__(definition)

        self.path = definition["path"]
        self.key = definition["key"]
        self.value = definition["value"]
        self.value_type = definition.get("value_type", "DWORD")
        self.force_create = definition.get("force_create", False)

    def snapshot(self) -> ActionSnapshot:
        subkey_existed = registry.subkey_exists(self.path)
        old_value, old_type = registry.get_value(self.path, self.key)

        metadata = {
            "path": self.path,
            "key": self.key,
            "old_value": old_value,
            "old_type": old_type,
            "value_existed": old_type is not None,
            "subkey_existed": subkey_existed,
        }

        return ActionSnapshot("registry", metadata)

    def apply(self) -> None:
        registry.set_value(
            self.path,
            self.key,
            self.value,
            self.value_type,
            force=self.force_create,
        )

    def verify(self) -> Tuple[bool, str]:
        actual_value, actual_type = registry.get_value(self.path, self.key)

        if actual_value is None:
            return False, "value missing"

        if actual_value != self.value:
            return False, "value mismatch"

        expected_type = registry.REG_TYPES.get(self.value_type, self.value_type)
        if actual_type != expected_type:
            return False, "type mismatch"

        return True, "ok"

    def rollback(self, snapshot: ActionSnapshot) -> None:
        meta = getattr(self, "_snapshot_meta", snapshot.metadata)

        if meta["value_existed"]:
            registry.set_value(
                meta["path"],
                meta["key"],
                meta["old_value"],
                meta["old_type"],
                force=True,
            )
        else:
            registry.delete_value(meta["path"], meta["key"])

            if not meta["subkey_existed"] and self._is_subkey_empty(meta["path"]):
                registry.delete_subkey(meta["path"])

    def _is_subkey_empty(self, path: str) -> bool:
        try:
            import winreg
            hive, subkey = registry.parse_registry_path(path)
            key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ)
            try:
                winreg.EnumValue(key, 0)
                winreg.CloseKey(key)
                return False
            except OSError:
                winreg.CloseKey(key)
                return True
        except (FileNotFoundError, OSError):
            return True

    def get_description(self) -> str:
        return f"Set {self.path}\\{self.key} = {self.value}"

    @classmethod
    def from_snapshot(cls, snapshot: ActionSnapshot) -> "RegistryAction":
        if snapshot.action_type != "registry":
            raise ValueError("Invalid snapshot type")

        meta = snapshot.metadata

        definition = {
            "type": "registry",
            "path": meta["path"],
            "key": meta["key"],
            "value": meta.get("old_value"),
            "value_type": meta["old_type"] if meta["old_type"] is not None else "DWORD",
            "force_create": True,
        }

        inst = cls(definition)
        inst._snapshot_meta = meta
        return inst
