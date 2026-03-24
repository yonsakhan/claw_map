"""
scheduler.py — 任务调度核心（单机串行版）

设计原则：
- PostgreSQL 作为任务队列，状态字段保证断点续爬
- acquire_task 使用 asyncio.Lock 防止并发领取同一任务
  （单机串行时 Lock 无实际竞争，但保留接口供后续多 Worker 复用）
- 失败超过 MAX_RETRIES 进入 dead_letter，不再重试
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import Column, DateTime, Integer, String, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config import settings

logger = logging.getLogger("Scheduler")

Base = declarative_base()


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

class CrawlTask(Base):
    """
    爬取任务记录表。

    status 取值:
        pending     — 待执行
        running     — 执行中（Worker 已领取）
        success     — 成功完成
        failed      — 本次失败，retry_count < MAX_RETRIES 时自动回滚 pending
        dead_letter — 超过最大重试次数，需人工处理
    """
    __tablename__ = "crawl_tasks"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    url         = Column(String, unique=True, nullable=False)
    status      = Column(String, default="pending", nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    agent_id    = Column(String)                    # 领取该任务的 Worker ID
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ──────────────────────────────────────────────
# 调度器
# ──────────────────────────────────────────────

class Scheduler:
    MAX_RETRIES = 3

    def __init__(self, postgres_url: Optional[str] = None):
        url = postgres_url or settings.postgres_url
        self.engine = create_engine(url, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self._lock = asyncio.Lock()  # 单机多协程安全锁
        logger.info("Scheduler initialized, task table ready.")

    # ── 写入任务 ────────────────────────────────

    def seed_urls(self, urls: List[str]) -> int:
        """
        批量写入待爬 URL。
        已存在的 URL 自动跳过（幂等），返回实际新增数量。
        """
        session = self.Session()
        added = 0
        try:
            for url in urls:
                url = url.strip()
                if not url:
                    continue
                exists = session.query(CrawlTask).filter_by(url=url).first()
                if not exists:
                    session.add(CrawlTask(url=url, status="pending"))
                    added += 1
            session.commit()
            logger.info(f"seed_urls: added={added}, skipped={len(urls)-added}")
            return added
        finally:
            session.close()

    def seed_from_file(self, filepath: str) -> int:
        """从文本文件（每行一个 URL）批量写入。"""
        with open(filepath, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
        return self.seed_urls(urls)

    # ── 领取 / 更新任务 ─────────────────────────

    async def acquire_task(self, agent_id: str) -> Optional[CrawlTask]:
        """
        加锁领取一条 pending 任务。
        返回 None 表示队列已空。
        """
        async with self._lock:
            session = self.Session()
            try:
                task = (
                    session.query(CrawlTask)
                    .filter_by(status="pending")
                    .order_by(CrawlTask.id)       # FIFO
                    .first()
                )
                if not task:
                    return None

                task.status    = "running"
                task.agent_id  = agent_id
                task.updated_at = datetime.now(timezone.utc)
                session.commit()

                # 返回轻量副本，避免 session 关闭后 lazy-load 报错
                return _task_snapshot(task)
            finally:
                session.close()

    def mark_success(self, task_id: int):
        """标记任务成功。"""
        self._set_status(task_id, "success")
        logger.debug(f"Task {task_id} → success")

    def mark_failed(self, task_id: int):
        """
        标记任务失败。
        - retry_count < MAX_RETRIES：回滚为 pending，等待重试
        - retry_count >= MAX_RETRIES：进入 dead_letter
        """
        session = self.Session()
        try:
            task = session.query(CrawlTask).filter_by(id=task_id).first()
            if not task:
                return
            task.retry_count += 1
            if task.retry_count < self.MAX_RETRIES:
                task.status = "pending"
                logger.warning(
                    f"Task {task_id} failed, retry {task.retry_count}/{self.MAX_RETRIES}"
                )
            else:
                task.status = "dead_letter"
                logger.error(
                    f"Task {task_id} exceeded max retries → dead_letter"
                )
            task.updated_at = datetime.now(timezone.utc)
            session.commit()
        finally:
            session.close()

    # ── 统计与查询 ──────────────────────────────

    def stats(self) -> Dict[str, int]:
        """返回各状态的任务计数。"""
        session = self.Session()
        try:
            rows = session.execute(
                text("SELECT status, COUNT(*) FROM crawl_tasks GROUP BY status")
            ).fetchall()
            return {row[0]: row[1] for row in rows}
        finally:
            session.close()

    def reset_running(self):
        """
        启动时将所有 running 状态重置为 pending。
        用于处理上次异常退出遗留的僵尸任务。
        """
        session = self.Session()
        try:
            count = (
                session.query(CrawlTask)
                .filter_by(status="running")
                .update({"status": "pending", "updated_at": datetime.now(timezone.utc)})
            )
            session.commit()
            if count:
                logger.warning(f"reset_running: {count} stale tasks → pending")
        finally:
            session.close()

    # ── 内部工具 ────────────────────────────────

    def _set_status(self, task_id: int, status: str):
        session = self.Session()
        try:
            session.query(CrawlTask).filter_by(id=task_id).update(
                {"status": status, "updated_at": datetime.now(timezone.utc)}
            )
            session.commit()
        finally:
            session.close()


# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────

def _task_snapshot(task: CrawlTask) -> CrawlTask:
    """返回 ORM 对象的轻量副本（脱离 session）。"""
    snap = CrawlTask()
    snap.id          = task.id
    snap.url         = task.url
    snap.retry_count = task.retry_count
    snap.agent_id    = task.agent_id
    return snap
