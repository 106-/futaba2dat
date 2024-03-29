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
from futaba2dat.transform import futaba_uploader

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# SQLAlchemyの初期設定
# cf. https://docs.sqlalchemy.org/en/14/core/engines.html
settings = Settings()
if settings.instance_connection_name is None:
    query = None
else:
    query = {
        "unix_sock": f"{settings.db_socket_dir}/{settings.instance_connection_name}/.s.PGSQL.5432"
    }
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

templates = Jinja2Templates(directory="templates")
boards = json.load(open("./futaba2dat/boards.json", "r"))
boards_hash = {}
for i in boards:
    boards_hash[(i[0], i[1])] = i[2]


# FastAPIのDI用のメソッド
# cf. https://fastapi.tiangolo.com/tutorial/dependencies/
def get_engine() -> sa.engine.Connectable:
    return db_engine


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
    return templates.TemplateResponse("index.j2", context)


# 閲覧履歴
@app.get("/log", response_class=HTMLResponse)
async def log(
    request: Request, engine: sa.engine.Connectable = Depends(get_engine)
) -> Response:
    histories = db.get_recent(engine)
    context = {"request": request, "histories": histories}
    return templates.TemplateResponse("log.j2", context)


# chmateの場合, 板のhtml内に<title>が含まれていればそれを板の名前としている.
# そのためこのアプリでも返しておく.
@app.get("/{sub_domain}/{board_dir}/")
async def board_top(request: Request, sub_domain: str, board_dir: str):
    generated_content = templates.TemplateResponse(
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
    threads = FutabaBoard().get_and_parse(sub_domain, board_dir)

    # mayならば書き込み0件のスレを省く(スクリプト対策)
    if sub_domain == "may" and board_dir == "b":
        threads = list(filter(lambda x: x["count"] != 0, threads))

    generated_content = templates.TemplateResponse(
        "subject.j2", {"request": request, "threads": threads}
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
    response = FutabaThread().get(sub_domain, board_dir, id)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code)
    else:
        thread = FutabaThread().parse(response.text)
        thread = futaba_uploader(thread)

    thread_uri = settings.futaba_thread_url.format(sub_domain, board_dir, id)
    link_to_thread = settings.futaba_thread_url.format(sub_domain, board_dir, id)
    board_name = "{0}({1}_{2})".format(
        boards_hash[(sub_domain, board_dir)], sub_domain, board_dir
    )

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
        "bbsmenu.j2",
        {"request": request, "boards": mod_boards},
    )
    return generated_content
