from typing import Optional

import sqlalchemy as sa
from pydantic import BaseModel
import datetime


class History(BaseModel):
    """datの閲覧履歴"""

    id: Optional[int]
    title: str
    link: str
    board: str
    host: str
    created_at: str


# SQLAlchemyの機能を使ってDBのテーブル定義をします
# cf. https://docs.sqlalchemy.org/en/14/core/schema.html
metadata = sa.MetaData()
history_table = sa.Table(
    "histories",
    metadata,
    sa.Column(
        "id",
        sa.Integer,
        sa.Identity(start=1, cycle=True),
        primary_key=True,
        autoincrement=True,
    ),
    sa.Column("title", sa.String(1024), nullable=False),
    sa.Column("link", sa.String(256), nullable=False),
    sa.Column("board", sa.String(256), nullable=False),
    sa.Column("host", sa.String(256), nullable=False),
    sa.Column(
        "created_at",
        sa.String(256),
        nullable=False,
    ),
)


def create_table(engine: sa.engine.Connectable) -> None:
    """テーブル定義に従ってテーブル作成をする"""
    metadata.create_all(engine)


# SQLの実行はSQLAlchemy Core APIを使っています
# cf. https://docs.sqlalchemy.org/en/14/core/tutorial.html
def get_recent(engine: sa.engine.Connectable) -> list[History]:
    """すべてのメッセージを取得する"""
    with engine.connect() as connection:
        query = (
            sa.sql.select(
                (
                    history_table.c.id,
                    history_table.c.title,
                    history_table.c.link,
                    history_table.c.board,
                    history_table.c.host,
                    history_table.c.created_at,
                )
            )
            .order_by(history_table.c.created_at.desc())
            .limit(50)
        )
        return [History(**m) for m in connection.execute(query)]


def add(engine: sa.engine.Connectable, history: History) -> None:
    """メッセージを保存する"""
    with engine.connect() as connection:
        query = history_table.insert()
        connection.execute(query, history.dict(exclude_unset=True))


def delete_all(engine: sa.engine.Connectable) -> None:
    """メッセージをすべて消す（テスト用）"""
    with engine.connect() as connection:
        connection.execute(history_table.delete())
