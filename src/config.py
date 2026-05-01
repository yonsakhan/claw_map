import os
import getpass
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

import yaml
from dotenv import load_dotenv

# Load .env file
load_dotenv()

logger = logging.getLogger(__name__)

_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return float(default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        logger.warning("Invalid float for %s=%r, falling back to %s", name, raw, default)
        return float(default)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return int(default)
    try:
        return int(raw)
    except (TypeError, ValueError):
        logger.warning("Invalid int for %s=%r, falling back to %s", name, raw, default)
        return int(default)


def _expand_env_placeholders(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    def replacer(match: re.Match[str]) -> str:
        env_name = match.group(1)
        return os.getenv(env_name, "")

    return _ENV_PATTERN.sub(replacer, value)


@dataclass
class AgentRuntimeConfig:
    mode: str = "serial"
    num_workers: int = 1
    headless: bool = True
    throttle_seconds: float = 3.0
    max_tasks_per_run: int = 0
    postgres_url: Optional[str] = None
    mongo_url: Optional[str] = None
    proxy_enabled: bool = False
    proxy_env_prefix: str = "PROXY_LIST_WORKER_"
    seed_explore_limit: int = 0
    seed_search_keywords: list[str] | None = None
    seed_search_limit_per_keyword: int = 0
    idle_timeout: float = 300.0


def _default_agent_config_path() -> str:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "config", "agent_config.yaml")


def load_agent_runtime_config(config_path: Optional[str] = None) -> AgentRuntimeConfig:
    resolved_path = config_path or _default_agent_config_path()
    if not os.path.exists(resolved_path):
        return AgentRuntimeConfig()

    with open(resolved_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    seed = raw.get("seed", {}) or {}
    proxy = raw.get("proxy", {}) or {}
    return AgentRuntimeConfig(
        mode=str(raw.get("mode", "serial") or "serial"),
        num_workers=int(raw.get("num_workers", 1) or 1),
        headless=bool(raw.get("headless", True)),
        throttle_seconds=float(raw.get("throttle_seconds", 3.0) or 3.0),
        max_tasks_per_run=int(raw.get("max_tasks_per_run", 0) or 0),
        postgres_url=str(_expand_env_placeholders(raw.get("postgres_url"))) or None,
        mongo_url=str(_expand_env_placeholders(raw.get("mongo_url"))) or None,
        proxy_enabled=bool(proxy.get("enabled", False)),
        proxy_env_prefix=str(proxy.get("per_worker_env_prefix", "PROXY_LIST_WORKER_") or "PROXY_LIST_WORKER_"),
        seed_explore_limit=int(seed.get("explore_limit", 0) or 0),
        seed_search_keywords=[str(item) for item in (seed.get("search_keywords", []) or []) if str(item).strip()] or None,
        seed_search_limit_per_keyword=int(seed.get("search_limit_per_keyword", 0) or 0),
    )


def apply_agent_runtime_config(runtime_config: AgentRuntimeConfig):
    if runtime_config.postgres_url:
        settings.postgres_url = runtime_config.postgres_url
    if runtime_config.mongo_url:
        settings.mongo_url = runtime_config.mongo_url

class Settings:
    pg_user = os.getenv("POSTGRES_USER", getpass.getuser())
    pg_host = os.getenv("POSTGRES_HOST", "localhost")
    pg_port = os.getenv("POSTGRES_PORT", "5432")
    pg_db = os.getenv("POSTGRES_DB", "claw_map")
    postgres_url = os.getenv("POSTGRES_URL", f"postgresql+psycopg://{pg_user}@{pg_host}:{pg_port}/{pg_db}")
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    mongo_db = os.getenv("MONGO_DB", "claw_map")
    mongo_raw_collection = os.getenv("MONGO_RAW_COLLECTION", "raw_profiles")
    mongo_task_collection = os.getenv("MONGO_TASK_COLLECTION", "crawl_tasks")
    mongo_runtime_collection = os.getenv("MONGO_RUNTIME_COLLECTION", "crawler_runtime")

    # LLM Config
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    model_name = os.getenv("MODEL_NAME", "moonshot-v1-8k")  # Default to moonshot for Kimi key
    xhs_cookie = os.getenv("XHS_COOKIE")

    # 小红书采集“礼貌策略”（降低触发频控/风控的概率；不是绕过风控）
    # 建议：先用非常保守的默认值，后续按实际情况调整。
    xhs_min_delay_seconds = _env_float("XHS_MIN_DELAY_SECONDS", 8.0)
    xhs_max_delay_seconds = _env_float("XHS_MAX_DELAY_SECONDS", 15.0)
    # 一旦检测到“访问频繁/风控”（如 error_code=300013），进入冷却窗口（秒）
    xhs_rate_limit_cooldown_seconds = _env_int("XHS_RATE_LIMIT_COOLDOWN_SECONDS", 2 * 60)


settings = Settings()
