import json
import asyncio
from typing import Optional
from src.analysis.persona_extractor import PersonaExtractor
from src.models.persona import AgentPersona
from src.db.session import get_session_factory

class BatchProcessor:
    def __init__(self, input_file: str, output_file: str, api_key: Optional[str] = None):
        self.input_file = input_file
        self.output_file = output_file
        self.extractor = PersonaExtractor(api_key=api_key)
        self.session_factory = get_session_factory()

    async def process(self, limit: Optional[int] = None, skip_existing: bool = True):
        print(f"Starting batch processing from {self.input_file}...")
        processed_count = 0
        skipped_count = 0
        results = []
        session = self.session_factory()
        
        # Get existing IDs if skipping
        existing_ids = set()
        if skip_existing:
            existing_ids = {row[0] for row in session.query(AgentPersona.original_id).all()}
            print(f"Found {len(existing_ids)} existing personas in database. Will skip them.")

        try:
            with open(self.input_file, "r", encoding="utf-8") as f:
                for line in f:
                    if limit and processed_count >= limit:
                        break
                    try:
                        entry = json.loads(line)
                        profile = entry.get("profile")
                        posts = entry.get("posts", [])
                        if not profile:
                            continue
                        
                        original_id = str(profile.get("id", ""))
                        if skip_existing and original_id in existing_ids:
                            skipped_count += 1
                            continue

                        persona = self.extractor.extract_persona(profile, posts)
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
                        
                        # Commit every 10 for safety
                        if processed_count % 10 == 0:
                            session.commit()
                            print(f"Processed {processed_count} profiles...")
                    except json.JSONDecodeError:
                        print("Skipping invalid JSON line")
                        continue
        except FileNotFoundError:
            print(f"Input file {self.input_file} not found.")
            session.close()
            return
        
        session.commit()
        session.close()
        
        # Append results to file if it exists, otherwise write
        mode = "a" if skip_existing else "w"
        with open(self.output_file, mode, encoding="utf-8") as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
        
        print(f"Batch processing complete.")
        print(f"  - New personas: {processed_count}")
        print(f"  - Skipped (existing): {skipped_count}")
        print(f"  - Results saved to {self.output_file} and PostgreSQL")

if __name__ == "__main__":
    processor = BatchProcessor(
        input_file="dummy_data.jsonl",
        output_file="structured_personas.jsonl",
    )
    asyncio.run(processor.process(limit=10, skip_existing=False))
