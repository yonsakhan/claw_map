import json
import tempfile
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.analysis.batch_processor import BatchProcessor
from src.models.base import Base
from src.models.persona import AgentPersona


class FakeExtractor:
    def extract_persona(self, profile, _posts):
        original_id = str(profile.get("id", ""))
        if str(profile.get("display_name", "")).strip() == "B":
            raise RuntimeError("synthetic extractor failure")
        return {
            "age_group": "25-29",
            "location": "北京",
            "fertility_status": "Trying",
            "income_level": "Medium",
            "spatial_preferences": ["Transit"],
            "fertility_intent_score": 3,
            "questionnaire_answers": [],
            "reasoning_summary": "offline test persona",
            "prompt_version": "test",
            "questionnaire_version": "test",
            "model_params": {"temperature": 0},
            "account_feature_profile": {"account_id": original_id},
            "evidence_references": [],
        }


class TestBatchProcessor(unittest.IsolatedAsyncioTestCase):
    async def test_process_continues_after_single_record_failure(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine)

        entries = [
            {
                "profile": {"id": "user_good_1", "bio": "记录通勤和生活", "display_name": "A"},
                "posts": [{"id": "p1", "content": "地铁很方便"}],
            },
            {
                "profile": {"id": "user_bad", "bio": "记录通勤和生活", "display_name": "B"},
                "posts": [{"id": "p2", "content": "希望托育更方便"}],
            },
            {
                "profile": {"id": "user_good_2", "bio": "记录通勤和生活", "display_name": "C"},
                "posts": [{"id": "p3", "content": "学区和公园都重要"}],
            },
        ]

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as input_fp:
            for entry in entries:
                input_fp.write(json.dumps(entry, ensure_ascii=False) + "\n")
            input_path = input_fp.name

        with tempfile.NamedTemporaryFile("r", encoding="utf-8", suffix=".jsonl", delete=False) as output_fp:
            output_path = output_fp.name

        processor = BatchProcessor(input_file=input_path, output_file=output_path, api_key=None)
        processor.session_factory = session_factory
        processor.extractor = FakeExtractor()

        await processor.process(skip_existing=False)

        with open(output_path, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        self.assertEqual([item["original_id"] for item in lines], ["user_good_1", "user_good_2"])

        session = session_factory()
        try:
            saved_ids = [row[0] for row in session.query(AgentPersona.original_id).order_by(AgentPersona.original_id).all()]
        finally:
            session.close()

        self.assertEqual(saved_ids, ["user_good_1", "user_good_2"])


if __name__ == "__main__":
    unittest.main()
