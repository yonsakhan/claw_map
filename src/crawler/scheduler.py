import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import Column, DateTime, Integer, String, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config import settings


logger = logging.getLogger("Scheduler")

Base = declarative_base()


class CrawlTask(Base):
    __tablename__ = "crawl_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True, nullable=False)
    status = Column(String, default="pending", nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    agent_id = Column(String)
    last_error = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


def _task_snapshot(task: CrawlTask) -> CrawlTask:
    snap = CrawlTask()
    snap.id = task.id
    snap.url = task.url
    snap.status = task.status
    snap.retry_count = task.retry_count
    snap.max_retries = task.max_retries
    snap.agent_id = task.agent_id
    snap.last_error = task.last_error
    return snap


class Scheduler:
    def __init__(self, postgres_url: Optional[str] = None):
        url = postgres_url or settings.postgres_url
        self.engine = create_engine(url, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self._lock = asyncio.Lock()

    def seed_urls(self, urls: List[str]) -> int:
        session = self.Session()
        added = 0
        try:
            for url in urls:
                url = (url or "").strip()
                if not url:
                    continue
                exists = session.query(CrawlTask).filter_by(url=url).first()
                if exists:
                    continue
                session.add(CrawlTask(url=url, status="pending"))
                added += 1
            session.commit()
            return added
        finally:
            session.close()

    def seed_from_file(self, filepath: str) -> int:
        with open(filepath, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
        return self.seed_urls(urls)

    async def acquire_task(self, agent_id: str) -> Optional[CrawlTask]:
        async with self._lock:
            session = self.Session()
            now = datetime.now(timezone.utc)
            try:
                sql = text(
                    """
                    WITH cte AS (
                      SELECT id
                      FROM crawl_tasks
                      WHERE status = 'pending'
                      ORDER BY id
                      FOR UPDATE SKIP LOCKED
                      LIMIT 1
                    )
                    UPDATE crawl_tasks
                    SET status = 'running',
                        agent_id = :agent_id,
                        updated_at = :now
                    WHERE id IN (SELECT id FROM cte)
                    RETURNING id, url, status, retry_count, max_retries, agent_id, last_error
                    """
                )
                row = session.execute(sql, {"agent_id": str(agent_id), "now": now}).fetchone()
                session.commit()
                if not row:
                    return None
                task = CrawlTask()
                task.id = row[0]
                task.url = row[1]
                task.status = row[2]
                task.retry_count = row[3]
                task.max_retries = row[4]
                task.agent_id = row[5]
                task.last_error = row[6]
                return _task_snapshot(task)
            finally:
                session.close()

    def mark_success(self, task_id: int):
        session = self.Session()
        try:
            session.query(CrawlTask).filter_by(id=int(task_id)).update(
                {"status": "success", "last_error": None, "updated_at": datetime.now(timezone.utc)}
            )
            session.commit()
        finally:
            session.close()

    def mark_failed(self, task_id: int, error: Optional[str] = None):
        session = self.Session()
        try:
            task = session.query(CrawlTask).filter_by(id=int(task_id)).first()
            if not task:
                return
            task.retry_count = int(task.retry_count or 0) + 1
            task.last_error = (error or "")[:800] if error else task.last_error
            if task.retry_count < int(task.max_retries or 3):
                task.status = "pending"
            else:
                task.status = "dead_letter"
            task.updated_at = datetime.now(timezone.utc)
            session.commit()
        finally:
            session.close()

    def reset_running(self):
        session = self.Session()
        try:
            session.query(CrawlTask).filter_by(status="running").update(
                {"status": "pending", "updated_at": datetime.now(timezone.utc)}
            )
            session.commit()
        finally:
            session.close()

    def stats(self) -> Dict[str, int]:
        session = self.Session()
        try:
            rows = session.execute(text("SELECT status, COUNT(*) FROM crawl_tasks GROUP BY status")).fetchall()
            return {row[0]: int(row[1]) for row in rows}
        finally:
            session.close()
