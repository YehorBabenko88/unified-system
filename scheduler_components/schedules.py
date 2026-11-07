"""Worker schedule only. Coordinator duties require separate policy."""
from datetime import timedelta
from zoneinfo import ZoneInfo


def active_at(instant, start_minute, end_minute, weekdays):
    weekdays = tuple(weekdays)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError('aware instant required')
    if (type(start_minute) is not int or type(end_minute) is not int
            or not 0 <= start_minute < 1440 or not 0 <= end_minute < 1440
            or start_minute == end_minute or any(type(d) is not int or d not in range(7) for d in weekdays)):
        raise ValueError('invalid schedule')
    local = instant.astimezone(ZoneInfo('Europe/Berlin'))
    minute = local.hour * 60 + local.minute
    if start_minute < end_minute:
        return local.weekday() in weekdays and start_minute <= minute < end_minute
    if minute >= start_minute:
        return local.weekday() in weekdays
    return minute < end_minute and (local - timedelta(days=1)).weekday() in weekdays

def worker_mode(active, running):
    if type(active) is not bool or type(running) is not int or running < 0:
        raise ValueError('boolean policy and nonnegative assignment count required')
    return 'ACTIVE' if active else ('DRAINING' if running else 'STANDBY')
