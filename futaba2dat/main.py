import datetime
import json
from typing import Optional

import sqlalchemy as sa
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from futaba2dat import db
from futaba2dat.db import History
from futaba2dat.futaba import FutabaBoard, FutabaThread
from futaba2dat.settings import Settings
from futaba2dat.transform import convert_futaba_urls_to_2ch_format, futaba_uploader

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# SQLAlchemyの初期設定
# cf. https://docs.sqlalchemy.org/en/14/core/engines.html
settings = Settings()
query = None
db_engine = sa.create_engine(
    sa.engine.url.URL.create(
        drivername=settings.db_drivername,
        username=settings.db_user,
        password=settings.db_pass,
        database=settings.db_name,
        host=settings.db_host,
        port=settings.db_port,
        query=query,
    ),
    echo=True,
)
db.create_table(db_engine)


def time_ago(timestamp_str: str) -> str:
    """タイムスタンプから相対時間を生成（n秒前、n分前など）"""
    try:
        # ISO形式のタイムスタンプをパース（naive datetime として扱う）
        timestamp = datetime.datetime.fromisoformat(timestamp_str.replace("Z", ""))
        now = datetime.datetime.now()
        diff = now - timestamp

        seconds = int(diff.total_seconds())

        # 負の値の場合は絶対値を取る（未来の時刻の場合）
        seconds = abs(seconds)

        if seconds < 60:
            return f"{seconds}秒前"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}分前"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours}時間前"
        else:
            days = seconds // 86400
            return f"{days}日前"
    except Exception:
        # パースエラーの場合は元の形式で表示
        try:
            return (
                timestamp_str.split("T")[0]
                + " "
                + timestamp_str.split("T")[1].split(".")[0]
            )
        except:
            return timestamp_str


templates = Jinja2Templates(directory="templates")
# カスタムフィルターを追加
templates.env.filters["time_ago"] = time_ago

boards = json.load(open("./futaba2dat/boards.json", "r"))
boards_hash = {}
for i in boards:
    boards_hash[(i[0], i[1])] = i[2]


# FastAPIのDI用のメソッド
# cf. https://fastapi.tiangolo.com/tutorial/dependencies/
def get_engine() -> sa.engine.Connectable:
    return db_engine


def get_proxy_domain(request: Request) -> str:
    """リバースプロキシのドメイン名を取得する"""
    # X-Forwarded-Hostヘッダーを最優先で確認
    forwarded_host = request.headers.get("x-forwarded-host")
    if forwarded_host:
        return forwarded_host.split(",")[0].strip()

    # 通常のHostヘッダーを確認
    host = request.headers.get("host")
    if host:
        return host

    # フォールバック
    return "localhost"


def generate_ftbucket_url(sub_domain: str, board_dir: str, thread_id: int) -> str:
    """FTBucket URLを生成する"""
    if sub_domain == "may":
        return f"https://may.ftbucket.info/may/cont/may.2chan.net_{board_dir}_res_{thread_id}/index.htm"
    elif sub_domain == "img":
        return f"https://c3.ftbucket.info/img/cont/img.2chan.net_{board_dir}_res_{thread_id}/index.htm"
    elif sub_domain == "jun":
        return f"https://c3.ftbucket.info/jun/cont/jun.2chan.net_{board_dir}_res_{thread_id}/index.htm"
    else:
        return None


def create_404_thread_response(sub_domain: str, board_dir: str, thread_id: int) -> dict:
    """404エラー時のスレッドレスポンスを生成する"""
    ftbucket_url = generate_ftbucket_url(sub_domain, board_dir, thread_id)

    if ftbucket_url:
        # FTBucketのURLがある場合
        thread_title = "スレッドが見つかりません"
        body_content = f"このスレッドは削除されたか存在しません。<br><br>FTBucketリンクはこちら：<br>{ftbucket_url}"
    else:
        # may/img/jun以外の場合
        thread_title = "スレッドが見つかりません"
        body_content = "このスレッドは削除されたか存在しません。"

    return {
        "title": thread_title,
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


def convert_to_shiftjis(generated_content):
    # テンプレートから生成された文字列をshift-jisにエンコードする. 同時にcontent-lengthも変える
    generated_content.body = generated_content.body.decode("utf-8").encode(
        "shift-jis", "ignore"
    )
    generated_content.headers["content-length"] = str(len(generated_content.body))
    return generated_content


# トップページには閲覧履歴と簡単な説明が載っている
@app.get("/", response_class=HTMLResponse)
async def get(
    request: Request, engine: sa.engine.Connectable = Depends(get_engine)
) -> Response:
    context = {"request": request}
    return templates.TemplateResponse(request, "index.j2", context)


# 閲覧履歴とダッシュボード
@app.get("/log", response_class=HTMLResponse)
async def log(
    request: Request, engine: sa.engine.Connectable = Depends(get_engine)
) -> Response:
    histories = db.get_recent(engine)
    analytics = db.get_dashboard_analytics(engine)
    context = {"request": request, "histories": histories, "analytics": analytics}
    return templates.TemplateResponse(request, "log.j2", context)


# chmateの場合, 板のhtml内に<title>が含まれていればそれを板の名前としている.
# そのためこのアプリでも返しておく.
@app.get("/{sub_domain}/{board_dir}/")
async def board_top(request: Request, sub_domain: str, board_dir: str):
    generated_content = templates.TemplateResponse(
        request,
        "board.j2",
        {
            "request": request,
            "title": boards_hash[(sub_domain, board_dir)],
            "sub_domain": sub_domain,
            "board_dir": board_dir,
        },
    )
    generated_content.headers["content-type"] = "text/html"
    generated_content = convert_to_shiftjis(generated_content)
    return generated_content


# 板の名前が含まれているファイル. これが無いとChmateはエラーを起こす.
@app.get("/{sub_domain}/{board_dir}/SETTING.TXT")
async def setting_txt(request: Request, sub_domain: str, board_dir: str):
    generated_content = templates.TemplateResponse(
        request,
        "setting.j2",
        {
            "request": request,
            "title": boards_hash[(sub_domain, board_dir)],
            "sub_domain": sub_domain,
            "board_dir": board_dir,
        },
    )
    generated_content.headers["content-type"] = "text/plain"
    generated_content = convert_to_shiftjis(generated_content)
    return generated_content


# スレッド一覧を表すファイル.
@app.get("/{sub_domain}/{board_dir}/subject.txt")
async def subject(request: Request, sub_domain: str, board_dir: str):
    threads = await FutabaBoard().get_and_parse(sub_domain, board_dir)

    # mayならば書き込み0件のスレを省く(スクリプト対策)
    if sub_domain == "may" and board_dir == "b":
        threads = list(filter(lambda x: x["count"] != 0, threads))

    generated_content = templates.TemplateResponse(
        request, "subject.j2", {"request": request, "threads": threads}
    )
    generated_content.headers["content-type"] = "text/plain"
    generated_content = convert_to_shiftjis(generated_content)
    return generated_content


# DAT形式のスレッドを返すアドレス.
@app.get("/{sub_domain}/{board_dir}/dat/{id}.dat")
async def thread(
    request: Request,
    sub_domain: str,
    board_dir: str,
    id: int,
    engine: sa.engine.Connectable = Depends(get_engine),
):
    response = await FutabaThread().get(sub_domain, board_dir, id)
    if response.status_code != 200:
        # 404の場合はFTBucket URLを含む特別なレスポンスを返す
        if response.status_code == 404:
            thread = create_404_thread_response(sub_domain, board_dir, id)
        else:
            raise HTTPException(status_code=response.status_code)
    else:
        thread = await FutabaThread().parse_async(response.text)
        thread = futaba_uploader(thread)

        # プロキシドメインを取得してふたばURLを2ch形式に変換
        proxy_domain = get_proxy_domain(request)
        thread = convert_futaba_urls_to_2ch_format(thread, proxy_domain)

    thread_uri = settings.futaba_thread_url.format(sub_domain, board_dir, id)
    link_to_thread = settings.futaba_thread_url.format(sub_domain, board_dir, id)
    board_name = "{0}({1}_{2})".format(
        boards_hash[(sub_domain, board_dir)], sub_domain, board_dir
    )

    # 404エラーの場合はログを記録しない
    if response.status_code == 200:
        host = request.headers.get("x-forwarded-for", None)
        if host:
            host = host.split(",")[0]
        else:
            host = request.client.host

        db.add(
            engine,
            History(
                link=link_to_thread,
                title=thread["title"],
                board=board_name,
                host=host,
                created_at=datetime.datetime.now().isoformat(),
            ),
        )

    image_url_root = Settings().futaba_image_url_root.format(sub_domain, board_dir)
    generated_content = templates.TemplateResponse(
        request,
        "thread.j2",
        {
            "request": request,
            "thread": thread,
            "image_url_root": image_url_root,
            "thread_uri": thread_uri,
        },
    )

    generated_content.headers["content-type"] = "text/plain"
    generated_content = convert_to_shiftjis(generated_content)
    return generated_content


# BBSMENUを返すページ
@app.get("/bbsmenu.html")
async def bbsmenu(
    request: Request,
    category: Optional[str] = None,
):
    if category == "ura":
        mod_boards = list(filter(lambda x: "二次元裏" in x[2], boards))
    else:
        mod_boards = boards

    generated_content = templates.TemplateResponse(
        request,
        "bbsmenu.j2",
        {"request": request, "boards": mod_boards},
    )
    return generated_content
