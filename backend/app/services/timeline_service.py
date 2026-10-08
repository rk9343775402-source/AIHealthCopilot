from datetime import date, datetime, time, timezone


def event_datetime(value: date | datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, time.min, tzinfo=timezone.utc)
