import time
from datetime import datetime, timezone, timedelta
from core.time import TimeProvider

def test_time_provider_returns_datetime():
    tp = TimeProvider()
    now = tp.now()
    assert isinstance(now, datetime)
    assert now.tzinfo == timezone.utc
    assert (datetime.now(timezone.utc) - now) < timedelta(seconds=1)

def test_time_provider_accepts_offset():
    tp = TimeProvider(offset_seconds=3600)
    now = tp.now()
    assert isinstance(now, datetime)

def test_sleep_wrapper():
    tp = TimeProvider()
    start = time.time()
    tp.sleep(0.1)
    end = time.time()
    assert (end - start) >= 0.1
