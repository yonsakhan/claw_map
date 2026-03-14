import os
import random
import logging
import asyncio
from typing import Optional, List, Dict

logger = logging.getLogger("ProxyManager")

class ProxyManager:
    def __init__(self, proxy_list: Optional[List[str]] = None):
        self.proxies = proxy_list or self._load_proxies_from_env()
        self.current_index = 0
        self.lock = asyncio.Lock()
    
    def _load_proxies_from_env(self) -> List[str]:
        proxy_str = os.getenv("PROXY_LIST", "")
        if not proxy_str:
            return []
        return [p.strip() for p in proxy_str.split(",") if p.strip()]

    async def get_next_proxy(self) -> Optional[str]:
        """轮询获取下一个代理 IP。"""
        async with self.lock:
            if not self.proxies:
                return None
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            return proxy

    async def get_random_proxy(self) -> Optional[str]:
        """随机获取一个代理 IP。"""
        if not self.proxies:
            return None
        return random.choice(self.proxies)

    def add_proxy(self, proxy: str):
        if proxy and proxy not in self.proxies:
            self.proxies.append(proxy)
    
    def remove_proxy(self, proxy: str):
        if proxy in self.proxies:
            self.proxies.remove(proxy)

    def count(self) -> int:
        return len(self.proxies)
