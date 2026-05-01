import asyncio
import json
from typing import List, Optional, Tuple

from src.analysis.cleaner import DataCleaner
from src.analysis.persona_extractor import PersonaExtractor
from src.db.session import get_session_factory
from src.models.persona import AgentPersona


class BatchProcessor:
    def __init__(
        self,
        input_file: str,
        output_file: str,
        api_key: Optional[str] = None,
        use_chinese_prompt: bool = True,  # 新增：是否使用中文 Prompt
    ):
        self.input_file = input_file
        self.output_file = output_file
        self.extractor = PersonaExtractor(
            api_key=api_key,
            use_chinese_prompt=use_chinese_prompt,
        )
        self.session_factory = get_session_factory()
        self.cleaner = DataCleaner()

    def _build_persona_row(self, original_id: str, persona: dict) -> AgentPersona:
        return AgentPersona(
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

    def _flush_pending(
        self,
        session,
        pending_rows: List[Tuple[str, AgentPersona]],
        pending_results: List[dict],
        committed_results: List[dict],
    ) -> int:
        if not pending_rows:
            return 0

        committed = 0
        try:
            for _, row in pending_rows:
                session.add(row)
            session.commit()
            committed_results.extend(pending_results)
            committed = len(pending_rows)
        except Exception as exc:
            session.rollback()
            print(f"  [WARN] Batch commit failed, fallback to per-row commit: {exc}")
            for (original_id, row), persona in zip(pending_rows, pending_results):
                try:
                    session.add(row)
                    session.commit()
                    committed_results.append(persona)
                    committed += 1
                except Exception as row_exc:
                    session.rollback()
                    print(f"  [WARN] Skipping {original_id} due to DB error: {row_exc}")
        finally:
            pending_rows.clear()
            pending_results.clear()

        return committed

    async def process(
        self,
        limit: Optional[int] = None,
        skip_existing: bool = True,
    ):
        print(f"Starting batch processing from {self.input_file}...")
        print(f"  Using {'Chinese' if self.extractor.use_chinese_prompt else 'English'} prompt")

        processed_count = 0
        skipped_existing = 0
        skipped_bot = 0
        failed_count = 0
        results = []
        pending_rows: List[Tuple[str, AgentPersona]] = []
        pending_results: List[dict] = []

        session = self.session_factory()

        existing_ids: set = set()
        try:
            if skip_existing:
                existing_ids = {row[0] for row in session.query(AgentPersona.original_id).all()}
                print(f"Found {len(existing_ids)} existing personas in DB, will skip them.")

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
                    posts_count = entry.get("posts_count", len(posts))

                    if not profile:
                        continue

                    original_id = str(profile.get("id", ""))
                    if self.cleaner.is_bot(profile, posts_count):
                        skipped_bot += 1
                        print(f"  [SKIP-BOT] {original_id} | bio: {str(profile.get('bio', ''))[:40]}")
                        continue

                    if skip_existing and original_id in existing_ids:
                        skipped_existing += 1
                        continue

                    cleaned_profile = self.cleaner.process_profile(profile, posts_count)
                    if cleaned_profile is None:
                        skipped_bot += 1
                        continue

                    try:
                        persona = self.extractor.extract_persona(cleaned_profile, posts)
                        persona["original_id"] = original_id
                        pending_results.append(persona)
                        pending_rows.append((original_id, self._build_persona_row(original_id, persona)))
                    except Exception as exc:
                        failed_count += 1
                        session.rollback()
                        print(f"  [WARN] Skipping {original_id} due to processing error: {exc}")
                        continue

                    if len(pending_rows) >= 10:
                        committed = self._flush_pending(session, pending_rows, pending_results, results)
                        processed_count += committed
                        print(f"  Processed {processed_count} profiles...")
                        if committed > 0:
                            existing_ids.update(result.get("original_id", "") for result in results[-committed:])

        except FileNotFoundError:
            print(f"Input file {self.input_file} not found.")
            return
        finally:
            if pending_rows:
                committed = self._flush_pending(session, pending_rows, pending_results, results)
                processed_count += committed
                if committed > 0:
                    existing_ids.update(result.get("original_id", "") for result in results[-committed:])
            session.close()

        mode = "a" if skip_existing else "w"
        with open(self.output_file, mode, encoding="utf-8") as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")

        print("\nBatch processing complete.")
        print(f"  ✓ New personas saved  : {processed_count}")
        print(f"  ✗ Skipped (bot/ads)   : {skipped_bot}")
        print(f"  - Skipped (duplicate) : {skipped_existing}")
        print(f"  ! Skipped (errors)    : {failed_count}")
        print(f"  Output → {self.output_file} & PostgreSQL")


if __name__ == "__main__":
    processor = BatchProcessor(
        input_file="dummy_data.jsonl",
        output_file="structured_personas.jsonl",
        use_chinese_prompt=True,  # 默认使用中文 Prompt
    )
    asyncio.run(processor.process(limit=10, skip_existing=False))
