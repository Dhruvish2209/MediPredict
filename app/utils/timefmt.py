"""Timestamps are stored in UTC by SQLite; show them in the viewer machine's local time."""
from datetime import datetime, timezone

import pandas as pd


def _local_tz():
    return datetime.now().astimezone().tzinfo


def to_local(series):
    return pd.to_datetime(series, utc=True).dt.tz_convert(_local_tz()).dt.tz_localize(None)


def parse(ts: str) -> datetime:
    return pd.to_datetime(ts, utc=True).tz_convert(_local_tz()).tz_localize(None).to_pydatetime()


def fmt(ts: str, with_time=True) -> str:
    d = parse(ts)
    return d.strftime("%d %b %Y, %H:%M") if with_time else d.strftime("%d %b %Y")


def ago(ts: str) -> str:
    d = parse(ts)
    secs = (datetime.now() - d).total_seconds()
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)} min ago"
    if secs < 86400:
        return f"{int(secs // 3600)} h ago"
    if secs < 86400 * 7:
        return f"{int(secs // 86400)} d ago"
    return d.strftime("%d %b %Y")
