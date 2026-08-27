import json
import logging
from typing import Any, Literal

_fallback_logger = logging.getLogger("futaba2dat")


def log_event(
    event: str,
    *,
    level: Literal["info", "warning", "error"] = "info",
    **fields: Any,
) -> None:
    """Workers Logsで検索できる構造化イベントを出力する。"""
    record = {"event": event, **fields}

    try:
        from js import Object, console
        from pyodide.ffi import to_js

        js_record = to_js(record, dict_converter=Object.fromEntries)
        if level == "error":
            console.error(js_record)
        elif level == "warning":
            console.warn(js_record)
        else:
            console.log(js_record)
    except Exception:
        log_level = {
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
        }[level]
        _fallback_logger.log(
            log_level,
            json.dumps(record, ensure_ascii=False, default=str),
        )
