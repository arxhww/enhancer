import re


class TweakID:
    """
    Structured tweak identifier.
    Canonical format: category.name@version
    Fallback: raw id (test / legacy compatibility)
    """

    PATTERN = re.compile(
        r'^(?P<category>[a-z_]+)\.(?P<name>[a-z_]+)@(?P<version>\d+\.\d+(?:\.\d+)?)$'
    )

    def __init__(self, raw: str, category=None, name=None, version=None):
        self.raw = raw
        self.category = category
        self.name = name
        self.version = version

    @classmethod
    def parse(cls, id_string: str) -> "TweakID":
        match = cls.PATTERN.match(id_string)
        if match:
            return cls(
                raw=id_string,
                category=match.group("category"),
                name=match.group("name"),
                version=match.group("version"),
            )

        # Fallback: accept raw ID (tests depend on this)
        return cls(raw=id_string)

    def __str__(self) -> str:
        return self.raw

    def __repr__(self) -> str:
        return f"TweakID('{self.raw}')"

    def __eq__(self, other) -> bool:
        if not isinstance(other, TweakID):
            return False
        return self.raw == other.raw

    def __hash__(self) -> int:
        return hash(self.raw)
