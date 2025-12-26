import re
from typing import Optional, Tuple


class TweakID:
    """
    Structured tweak identifier with category, name, and version.
    
    Format: category.name@version
    - category: namespace (gaming, privacy, performance, etc.)
    - name: descriptive action name (snake_case)
    - version: semantic version (major.minor or major.minor.patch)
    
    Examples:
        gaming.disable_game_dvr@1.0
        privacy.disable_telemetry@2.1.0
        performance.disable_superfetch@1.0
    """
    
    PATTERN = re.compile(
        r'^(?P<category>[a-z_]+)\.(?P<name>[a-z_]+)@(?P<version>\d+\.\d+(?:\.\d+)?)$'
    )
    
    LEGACY_PATTERN = re.compile(r'^\d{3,}$')
    
    def __init__(self, category: str, name: str, version: str):
        self.category = category
        self.name = name
        self.version = version
        
        if not self._is_valid_identifier(category):
            raise ValueError(f"Invalid category: {category}")
        if not self._is_valid_identifier(name):
            raise ValueError(f"Invalid name: {name}")
        if not self._is_valid_version(version):
            raise ValueError(f"Invalid version: {version}")
    
    @classmethod
    def parse(cls, id_string: str) -> 'TweakID':
        match = cls.PATTERN.match(id_string)
        if match:
            return cls(
                category=match.group('category'),
                name=match.group('name'),
                version=match.group('version')
            )
        
        if cls.LEGACY_PATTERN.match(id_string):
            return cls(
                category="legacy",
                name=f"tweak_{id_string}",
                version="1.0"
            )
        
        raise ValueError(
            f"Invalid tweak ID format: '{id_string}'. "
            f"Expected format: category.name@version (e.g., gaming.disable_dvr@1.0)"
        )
    
    @staticmethod
    def _is_valid_identifier(s: str) -> bool:
        return bool(re.match(r'^[a-z][a-z0-9_]*$', s))
    
    @staticmethod
    def _is_valid_version(v: str) -> bool:
        return bool(re.match(r'^\d+\.\d+(?:\.\d+)?$', v))
    
    def __str__(self) -> str:
        return f"{self.category}.{self.name}@{self.version}"
    
    def __repr__(self) -> str:
        return f"TweakID('{self}')"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, TweakID):
            return False
        return str(self) == str(other)
    
    def __hash__(self) -> int:
        return hash(str(self))
    
    @property
    def base_id(self) -> str:
        return f"{self.category}.{self.name}"
    
    def is_compatible_upgrade(self, other: 'TweakID') -> bool:
        if self.base_id != other.base_id:
            return False
        
        return self._compare_versions(self.version, other.version) >= 0
    
    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        parts1 = [int(x) for x in v1.split('.')]
        parts2 = [int(x) for x in v2.split('.')]
        
        max_len = max(len(parts1), len(parts2))
        parts1 += [0] * (max_len - len(parts1))
        parts2 += [0] * (max_len - len(parts2))
        
        for p1, p2 in zip(parts1, parts2):
            if p1 < p2:
                return -1
            elif p1 > p2:
                return 1
        
        return 0


def validate_tweak_definition(tweak_def: dict) -> TweakID:
    if "id" not in tweak_def:
        raise ValueError("Tweak definition missing 'id' field")
    
    return TweakID.parse(tweak_def["id"])