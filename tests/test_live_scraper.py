import asyncio
import sys
import os

# Ensure src is in path
sys.path.append(os.getcwd())

from src.crawler.xiaohongshu_scraper import XiaohongshuScraper

async def run_test():
    # 这是一个公开的小红书用户示例 URL
    # 如果遇到登录墙，请在浏览器中登录后获取 Cookie 或使用已登录的浏览器环境
    test_url = "https://www.xiaohongshu.com/user/profile/5b15392b4260905102559902" # 随便找的一个公开博主
    test_url = test_url.strip().strip("`").strip("'").strip('"')
    
    print(f"--- 启动小红书爬虫测试 ---")
    print(f"目标 URL: {test_url}")
    print(f"状态: 正在初始化浏览器...")
    
    # 在您的本地环境中运行可以将 headless 设为 False 观察过程
    # 这里由于是 AI 容器环境，我们保持 True，但会输出详细日志
    scraper = XiaohongshuScraper(headless=True) 
    
    print(f"状态: 开始抓取数据，请观察下方日志流...")
    result = await scraper.fetch_profile(test_url)
    
    if result:
        print(f"\n--- 抓取成功 ---")
        print(f"用户页面标题: {result.get('title')}")
        print(f"成功获取帖子数量: {len(result.get('posts', []))}")
        for i, post in enumerate(result.get('posts', []), 1):
            print(f"  {i}. {post.get('title')} (ID: {post.get('id')})")
    else:
        print(f"\n--- 抓取失败 ---")
        print(f"原因: 可能遇到了登录墙或反爬验证，请检查网络或 URL 是否有效。")

if __name__ == "__main__":
    asyncio.run(run_test())
