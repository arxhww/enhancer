from datetime import datetime, timezone, timedelta
import time as _time

class TimeProvider:
    """
    Abstraction for system time.
    Allows deterministic control in tests and future clock strategies.
    """

    def __init__(self, offset_seconds: float = 0.0):
        self.offset = offset_seconds

    def now(self) -> datetime:
        """
        Returns timezone-aware UTC datetime.
        Microseconds stripped for DB consistency.
        """
        return (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            + timedelta(seconds=self.offset)
        )

    def sleep(self, seconds: float) -> None:
        _time.sleep(seconds)


# Engine-wide default provider
DEFAULT_TIME_PROVIDER = TimeProvider()
