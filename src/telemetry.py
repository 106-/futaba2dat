from typing import Any, Literal

from js import Object, console
from pyodide.ffi import to_js


def log_event(
    event: str,
    *,
    level: Literal["info", "warning", "error"] = "info",
    **fields: Any,
) -> None:
    """Workers Logsで検索できる構造化イベントを出力する。"""
    record = {"event": event, **fields}
    js_record = to_js(record, dict_converter=Object.fromEntries)
    if level == "error":
        console.error(js_record)
    elif level == "warning":
        console.warn(js_record)
    else:
        console.log(js_record)
