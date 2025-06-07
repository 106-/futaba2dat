import datetime
from typing import Optional

import sqlalchemy as sa
from pydantic import BaseModel


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
        index=True,
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
            sa.select(
                history_table.c.id,
                history_table.c.title,
                history_table.c.link,
                history_table.c.board,
                history_table.c.host,
                history_table.c.created_at,
            )
            .order_by(history_table.c.created_at.desc())
            .limit(50)
        )
        return [History(**m._asdict()) for m in connection.execute(query)]


def add(engine: sa.engine.Connectable, history: History) -> None:
    """メッセージを保存する"""
    with engine.begin() as connection:
        query = history_table.insert()
        connection.execute(query, history.dict(exclude_unset=True))


def delete_all(engine: sa.engine.Connectable) -> None:
    """メッセージをすべて消す（テスト用）"""
    with engine.begin() as connection:
        connection.execute(history_table.delete())


def get_dashboard_analytics(engine: sa.engine.Connectable) -> dict:
    """ダッシュボード用の分析データを取得する"""
    with engine.connect() as connection:
        # 過去1週間の基準日時
        week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
        # 過去1日の基準日時
        day_ago = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()

        # 1. 過去1週間の人気板ランキング（アクセス数順）
        board_popularity_query = sa.text("""
            SELECT board, COUNT(*) as access_count
            FROM histories 
            WHERE created_at > :week_ago
            GROUP BY board 
            ORDER BY access_count DESC 
            LIMIT 10
        """)
        board_popularity = list(
            connection.execute(board_popularity_query, {"week_ago": week_ago})
        )

        # 2. 過去1週間の人気スレッドランキング（アクセス数順）
        thread_popularity_query = sa.text("""
            SELECT title, link, board, COUNT(*) as access_count
            FROM histories 
            WHERE created_at > :week_ago
            GROUP BY title, link, board 
            ORDER BY access_count DESC 
            LIMIT 10
        """)
        thread_popularity = list(
            connection.execute(thread_popularity_query, {"week_ago": week_ago})
        )

        # 3. 過去1日のユニークユーザー数
        unique_users_day_query = sa.text("""
            SELECT COUNT(DISTINCT host) as unique_users
            FROM histories 
            WHERE created_at > :day_ago
        """)
        unique_users_day = connection.execute(
            unique_users_day_query, {"day_ago": day_ago}
        ).scalar()

        # 4. 過去1週間のユニークユーザー数
        unique_users_week_query = sa.text("""
            SELECT COUNT(DISTINCT host) as unique_users
            FROM histories 
            WHERE created_at > :week_ago
        """)
        unique_users_week = connection.execute(
            unique_users_week_query, {"week_ago": week_ago}
        ).scalar()

        # 5. 過去1週間の総アクセス数
        total_access_week_query = sa.text("""
            SELECT COUNT(*) as total_access
            FROM histories 
            WHERE created_at > :week_ago
        """)
        total_access_week = connection.execute(
            total_access_week_query, {"week_ago": week_ago}
        ).scalar()

        # 6. 過去1日の総アクセス数
        total_access_day_query = sa.text("""
            SELECT COUNT(*) as total_access
            FROM histories 
            WHERE created_at > :day_ago
        """)
        total_access_day = connection.execute(
            total_access_day_query, {"day_ago": day_ago}
        ).scalar()

        return {
            "board_popularity": [
                {"board": row[0], "access_count": row[1]} for row in board_popularity
            ],
            "thread_popularity": [
                {
                    "title": row[0],
                    "link": row[1],
                    "board": row[2],
                    "access_count": row[3],
                }
                for row in thread_popularity
            ],
            "unique_users_day": unique_users_day or 0,
            "unique_users_week": unique_users_week or 0,
            "total_access_day": total_access_day or 0,
            "total_access_week": total_access_week or 0,
        }
