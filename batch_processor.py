import json
import asyncio
from typing import Optional

from src.analysis.cleaner import DataCleaner
from src.analysis.persona_extractor import PersonaExtractor
from src.models.persona import AgentPersona
from src.db.session import get_session_factory


class BatchProcessor:
    def __init__(
        self,
        input_file: str,
        output_file: str,
        api_key: Optional[str] = None,
    ):
        self.input_file = input_file
        self.output_file = output_file
        self.extractor = PersonaExtractor(api_key=api_key)
        self.session_factory = get_session_factory()
        self.cleaner = DataCleaner()          # ← 接入清洗器

    async def process(
        self,
        limit: Optional[int] = None,
        skip_existing: bool = True,
    ):
        print(f"Starting batch processing from {self.input_file}...")

        processed_count = 0
        skipped_existing = 0
        skipped_bot = 0
        results = []

        session = self.session_factory()

        # 获取已存在的 ID 用于去重
        existing_ids: set = set()
        if skip_existing:
            existing_ids = {
                row[0] for row in session.query(AgentPersona.original_id).all()
            }
            print(f"Found {len(existing_ids)} existing personas in DB, will skip them.")

        try:
            with open(self.input_file, "r", encoding="utf-8") as f:
                for line in f:
                    if limit and processed_count >= limit:
                        break

                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        print("  [WARN] Skipping invalid JSON line")
                        continue

                    profile = entry.get("profile")
                    posts = entry.get("posts", [])
                    # 优先使用 entry 中记录的帖子总数（比 len(posts) 更准确）
                    posts_count = entry.get("posts_count", len(posts))

                    if not profile:
                        continue

                    original_id = str(profile.get("id", ""))

                    # ── 1. 机器人过滤 ──────────────────────────────────────
                    if self.cleaner.is_bot(profile, posts_count):
                        skipped_bot += 1
                        print(
                            f"  [SKIP-BOT] {original_id} | "
                            f"bio: {str(profile.get('bio', ''))[:40]}"
                        )
                        continue

                    # ── 2. 去重 ───────────────────────────────────────────
                    if skip_existing and original_id in existing_ids:
                        skipped_existing += 1
                        continue

                    # ── 3. 清洗（去 emoji、匿名化 ID）─────────────────────
                    cleaned_profile = self.cleaner.process_profile(profile, posts_count)
                    if cleaned_profile is None:
                        # process_profile 内部二次判定为 bot
                        skipped_bot += 1
                        continue

                    # ── 4. AI 人设推断 ────────────────────────────────────
                    persona = self.extractor.extract_persona(cleaned_profile, posts)
                    persona["original_id"] = original_id

                    results.append(persona)
                    session.add(
                        AgentPersona(
                            original_id=original_id,
                            age_group=persona.get("age_group"),
                            location=persona.get("location"),
                            fertility_status=persona.get("fertility_status"),
                            income_level=persona.get("income_level"),
                            spatial_preferences=persona.get("spatial_preferences", []),
                            fertility_intent_score=persona.get("fertility_intent_score", 0),
                            questionnaire_answers=persona.get("questionnaire_answers", []),
                            reasoning_summary=persona.get("reasoning_summary"),
                            prompt_version=persona.get("prompt_version"),
                            questionnaire_version=persona.get("questionnaire_version"),
                            model_params=persona.get("model_params"),
                            feature_snapshot=persona.get("account_feature_profile"),
                            evidence_references=persona.get("evidence_references", []),
                        )
                    )
                    processed_count += 1

                    if processed_count % 10 == 0:
                        session.commit()
                        print(f"  Processed {processed_count} profiles...")

        except FileNotFoundError:
            print(f"Input file {self.input_file} not found.")
            session.close()
            return

        session.commit()
        session.close()

        # 写入输出文件
        mode = "a" if skip_existing else "w"
        with open(self.output_file, mode, encoding="utf-8") as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")

        print("\nBatch processing complete.")
        print(f"  ✓ New personas saved  : {processed_count}")
        print(f"  ✗ Skipped (bot/ads)   : {skipped_bot}")
        print(f"  - Skipped (duplicate) : {skipped_existing}")
        print(f"  Output → {self.output_file} & PostgreSQL")


if __name__ == "__main__":
    processor = BatchProcessor(
        input_file="dummy_data.jsonl",
        output_file="structured_personas.jsonl",
    )
    asyncio.run(processor.process(limit=10, skip_existing=False))
