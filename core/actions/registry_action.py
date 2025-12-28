from typing import Any, Dict
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
        try:
            subkey_existed = registry.subkey_exists(self.path)
            old_value, old_type = registry.get_value(self.path, self.key)
        except Exception:
            subkey_existed = False
            old_value, old_type = None, None

        return ActionSnapshot("registry", {
            "path": self.path,
            "key": self.key,
            "old_value": old_value,
            "old_type": old_type,
            "value_existed": old_type is not None,
            "subkey_existed": subkey_existed,
        })

    def apply(self) -> None:
        registry.set_value(
            self.path,
            self.key,
            self.value,
            self.value_type,
            force=self.force_create,
        )

    def verify(self) -> bool:
        try:
            actual_value, actual_type = registry.get_value(self.path, self.key)
            if actual_value != self.value:
                return False
            expected_type = registry.REG_TYPES.get(self.value_type, self.value_type)
            return actual_type == expected_type
        except Exception:
            return False

    def rollback(self, snapshot: ActionSnapshot) -> None:
        meta = snapshot.metadata

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
            if not meta["subkey_existed"]:
                try:
                    registry.delete_subkey(meta["path"])
                except Exception:
                    pass

    @classmethod
    def from_snapshot(cls, snapshot: ActionSnapshot) -> "RegistryAction":
        meta = snapshot.metadata
        inst = cls({
            "type": "registry",
            "path": meta["path"],
            "key": meta["key"],
            "value": meta.get("old_value"),
            "value_type": meta["old_type"] or "DWORD",
            "force_create": True,
        })
        return inst
