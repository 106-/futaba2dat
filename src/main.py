import codecs
import datetime
import json
import logging
import time
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from db import D1HistoryRepository, History
from futaba import FutabaBoard, FutabaThread
from settings import Settings
from thread_cache import CloudflareThreadStateStore, ThreadCacheCoordinator
from transform import convert_futaba_urls_to_2ch_format, futaba_uploader

logger = logging.getLogger(__name__)
package_dir = Path(__file__).parent
settings = Settings()


def _numref_errors(exc):
    """cp932 にない文字を HTML 数値文字参照へ置換する。"""
    if isinstance(exc, UnicodeEncodeError):
        ch = exc.object[exc.start]
        return (f"&#x{ord(ch):X};", exc.start + 1)
    raise exc


codecs.register_error("numref", _numref_errors)

app = FastAPI()
templates = Jinja2Templates(directory=str(package_dir / "templates"))


def time_ago(timestamp: int) -> str:
    """Unix epoch milliseconds から相対時間を返す。"""
    target = datetime.datetime.fromtimestamp(timestamp / 1000, tz=datetime.timezone.utc)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    seconds = abs(int((now - target).total_seconds()))
    if seconds < 60:
        return f"{seconds}秒前"
    if seconds < 3600:
        return f"{seconds // 60}分前"
    if seconds < 86400:
        return f"{seconds // 3600}時間前"
    return f"{seconds // 86400}日前"


templates.env.filters["time_ago"] = time_ago

with (package_dir / "boards.json").open(encoding="utf-8") as boards_file:
    boards = json.load(boards_file)
boards_hash = {(item[0], item[1]): item[2] for item in boards}


def get_board_name(sub_domain: str, board_dir: str) -> str:
    try:
        return boards_hash[(sub_domain, board_dir)]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Board not found") from exc


def get_history_repository(request: Request) -> D1HistoryRepository:
    return D1HistoryRepository(request.scope["env"].DB)


def history_writes_enabled(request: Request) -> bool:
    return request.scope["env"].HISTORY_WRITES == "true"


async def add_history_in_background(
    repository: D1HistoryRepository, history: History
) -> None:
    """レスポンスを失敗させずにアクセス履歴を保存する。"""
    try:
        await repository.add(history)
    except Exception:
        logger.exception("Background D1 history write failed")


def get_proxy_domain(request: Request) -> str:
    return request.headers["host"]


def get_client_ip(request: Request) -> str:
    return request.headers["cf-connecting-ip"]


def generate_ftbucket_url(
    sub_domain: str, board_dir: str, thread_id: int
) -> str | None:
    if sub_domain == "may":
        return f"https://may.ftbucket.info/may/cont/may.2chan.net_{board_dir}_res_{thread_id}/index.htm"
    if sub_domain == "img":
        return f"https://c3.ftbucket.info/img/cont/img.2chan.net_{board_dir}_res_{thread_id}/index.htm"
    if sub_domain == "jun":
        return f"https://c3.ftbucket.info/jun/cont/jun.2chan.net_{board_dir}_res_{thread_id}/index.htm"
    return None


def create_404_thread_response(
    sub_domain: str, board_dir: str, thread_id: int
) -> dict[str, Any]:
    ftbucket_url = generate_ftbucket_url(sub_domain, board_dir, thread_id)
    body_content = "このスレッドは削除されたか存在しません。"
    if ftbucket_url:
        body_content += f"<br><br>FTBucketリンクはこちら：<br>{ftbucket_url}"
    return {
        "title": "スレッドが見つかりません",
        "expire": "削除済み",
        "posts": [
            {
                "title": None,
                "image": None,
                "name": "システム",
                "mail": None,
                "date": datetime.datetime.now().strftime("%y/%m/%d(%a)%H:%M:%S"),
                "id": None,
                "no": "No.404",
                "sod": "+",
                "body": body_content,
                "quote_res": [],
            }
        ],
    }


def convert_to_shiftjis(generated_content: Response) -> Response:
    body = generated_content.body.decode("utf-8").encode("cp932", "numref")
    generated_content.body = body
    generated_content.headers["content-length"] = str(len(body))
    generated_content.headers["cache-control"] = "no-store"
    return generated_content


@app.middleware("http")
async def disable_cache(request: Request, call_next):
    response = await call_next(request)
    response.headers["cache-control"] = "no-store"
    return response


@app.get("/", response_class=HTMLResponse)
async def get(request: Request) -> Response:
    return templates.TemplateResponse(request, "index.j2", {"request": request})


@app.get("/log", response_class=HTMLResponse)
async def log(
    request: Request,
    repository: D1HistoryRepository = Depends(get_history_repository),
) -> Response:
    try:
        histories = await repository.get_recent()
        analytics = await repository.get_dashboard_analytics()
    except Exception as exc:
        logger.exception("D1 history read failed")
        raise HTTPException(
            status_code=503, detail="History database unavailable"
        ) from exc
    return templates.TemplateResponse(
        request,
        "log.j2",
        {"request": request, "histories": histories, "analytics": analytics},
    )


@app.get("/{sub_domain}/{board_dir}/")
async def board_top(request: Request, sub_domain: str, board_dir: str):
    board_name = get_board_name(sub_domain, board_dir)
    generated_content = templates.TemplateResponse(
        request,
        "board.j2",
        {
            "request": request,
            "title": board_name,
            "sub_domain": sub_domain,
            "board_dir": board_dir,
        },
    )
    generated_content.headers["content-type"] = "text/html"
    return convert_to_shiftjis(generated_content)


@app.get("/{sub_domain}/{board_dir}/SETTING.TXT")
async def setting_txt(request: Request, sub_domain: str, board_dir: str):
    board_name = get_board_name(sub_domain, board_dir)
    generated_content = templates.TemplateResponse(
        request,
        "setting.j2",
        {
            "request": request,
            "title": board_name,
            "sub_domain": sub_domain,
            "board_dir": board_dir,
        },
    )
    generated_content.headers["content-type"] = "text/plain"
    return convert_to_shiftjis(generated_content)


@app.get("/{sub_domain}/{board_dir}/subject.txt")
async def subject(request: Request, sub_domain: str, board_dir: str):
    get_board_name(sub_domain, board_dir)
    threads = await FutabaBoard().get_and_parse(sub_domain, board_dir)
    if sub_domain == "may" and board_dir == "b":
        threads = [thread for thread in threads if thread["count"] != 0]
    generated_content = templates.TemplateResponse(
        request, "subject.j2", {"request": request, "threads": threads}
    )
    generated_content.headers["content-type"] = "text/plain"
    return convert_to_shiftjis(generated_content)


@app.get("/{sub_domain}/{board_dir}/dat/{id}.dat")
async def thread(
    request: Request,
    sub_domain: str,
    board_dir: str,
    id: int,
    background_tasks: BackgroundTasks,
    repository: D1HistoryRepository = Depends(get_history_repository),
):
    board_title = get_board_name(sub_domain, board_dir)
    response = await ThreadCacheCoordinator(CloudflareThreadStateStore()).get(
        str(request.url), sub_domain, board_dir, id
    )
    if response.status_code != 200:
        if response.status_code == 404:
            parsed_thread = create_404_thread_response(sub_domain, board_dir, id)
        else:
            raise HTTPException(
                status_code=502,
                detail=f"Upstream returned HTTP {response.status_code}",
            )
    else:
        if response.opener is None or response.thread is None:
            raise HTTPException(status_code=502, detail="Upstream returned empty JSON")
        parsed_thread = await FutabaThread().parse_async(
            response.opener, response.thread, id
        )
        parsed_thread = futaba_uploader(parsed_thread)
        parsed_thread = convert_futaba_urls_to_2ch_format(
            parsed_thread, get_proxy_domain(request)
        )

    thread_uri = settings.futaba_thread_url.format(sub_domain, board_dir, id)
    board_name = f"{board_title}({sub_domain}_{board_dir})"

    if response.status_code == 200 and history_writes_enabled(request):
        background_tasks.add_task(
            add_history_in_background,
            repository,
            History(
                link=thread_uri,
                title=parsed_thread["title"],
                board=board_name,
                host=get_client_ip(request),
                created_at=int(time.time() * 1000),
            ),
        )

    generated_content = templates.TemplateResponse(
        request,
        "thread.j2",
        {
            "request": request,
            "thread": parsed_thread,
            "image_url_root": settings.futaba_image_url_root.format(sub_domain),
            "thread_uri": thread_uri,
        },
    )
    generated_content.headers["content-type"] = "text/plain"
    return convert_to_shiftjis(generated_content)


@app.get("/bbsmenu.html")
async def bbsmenu(request: Request, category: str | None = None):
    mod_boards = (
        [board for board in boards if "二次元裏" in board[2]]
        if category == "ura"
        else boards
    )
    return templates.TemplateResponse(
        request,
        "bbsmenu.j2",
        {"request": request, "boards": mod_boards},
    )
