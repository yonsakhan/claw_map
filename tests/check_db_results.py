import os
import json
from pymongo import MongoClient
from sqlalchemy import create_engine, text
from src.config import settings
from dotenv import load_dotenv

load_dotenv()

def check_databases():
    print("="*50)
    print("🔍 数据库结果自检报告")
    print("="*50)

    # 1. Check MongoDB (Raw Data)
    print("\n[1] MongoDB (原始抓取数据):")
    try:
        mongo_client = MongoClient(settings.mongo_url)
        db = mongo_client[settings.mongo_db]
        collection = db[settings.mongo_raw_collection]
        
        count = collection.count_documents({})
        print(f"✅ 成功连接 MongoDB")
        print(f"📊 原始数据集合 ({settings.mongo_raw_collection}) 总数: {count}")
        
        if count > 0:
            print("\n最近导入的 1 条原始数据预览:")
            latest = collection.find_one(sort=[('_id', -1)])
            raw_data = latest.get("raw_data", {})
            profile = raw_data.get("profile") or latest.get("profile", {})
            posts = raw_data.get("posts") or latest.get("posts", [])
            status = latest.get("collection_status", "unknown")
            retry = latest.get("retry", {})
            failure = latest.get("failure", {})
            print(f"   - 账号 ID: {latest.get('account_id') or profile.get('id')}")
            print(f"   - 采集状态: {status}")
            print(f"   - 帖子抓取数量: {len(posts)}")
            print(f"   - 可重试: {retry.get('retryable', False)} | 已重试: {retry.get('retry_count', 0)}")
            if failure.get("error_code") and failure.get("error_code") != "none":
                print(f"   - 失败码: {failure.get('error_code')} | 失败信息: {failure.get('error_message')}")
    except Exception as e:
        print(f"❌ MongoDB 连接或查询失败: {e}")

    # 2. Check PostgreSQL (Structured Personas)
    print("\n" + "-"*30)
    print("\n[2] PostgreSQL (结构化 AI 画像):")
    try:
        engine = create_engine(settings.postgres_url)
        with engine.connect() as conn:
            # 查询总数
            result = conn.execute(text("SELECT COUNT(*) FROM agent_personas"))
            count = result.scalar()
            print(f"✅ 成功连接 PostgreSQL")
            print(f"📊 结构化画像表 (agent_personas) 总数: {count}")
            
            if count > 0:
                print("\n最新生成的 3 条 AI 画像结果:")
                result = conn.execute(text("""
                    SELECT original_id, age_group, location, fertility_status, fertility_intent_score 
                    FROM agent_personas 
                    ORDER BY id DESC LIMIT 3
                """))
                for row in result:
                    print(f"   - 用户 {row[0]}: {row[1]} | {row[2]} | {row[3]} | 意愿分: {row[4]}")
    except Exception as e:
        print(f"❌ PostgreSQL 连接或查询失败: {e}")
    
    print("\n" + "="*50)

if __name__ == "__main__":
    check_databases()
