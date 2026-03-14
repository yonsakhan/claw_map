import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.analysis.account_persona_pipeline import AccountPersonaPipeline
from src.analysis.persona_extractor import PersonaExtractor
from src.models.base import Base
from src.storage.result_trace_store import ResultTraceStore


class FakeRawStore:
    def __init__(self, raw_document):
        self.raw_document = raw_document

    def get_by_account_id(self, account_id: str):
        if account_id == self.raw_document.get("account_id"):
            return self.raw_document
        return None


class TestAccountPersonaPipeline(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.session_factory = sessionmaker(bind=engine)

    def test_questionnaire_joint_output_and_trace_query(self):
        raw_document = {
            "account_id": "u_3",
            "raw_data": {
                "profile": {"id": "u_3", "location": "北京", "bio": "备孕中，关注通勤与学区"},
                "posts": [{"id": "p1", "content": "希望地铁和托育更方便"}],
                "likes": [],
                "favorites": [],
                "follows": [],
            },
        }
        questionnaire = [
            {"id": "q1", "question": "哪些城市因素会影响你是否生育？"},
            {"id": "q2", "question": "你对育儿配套设施满意吗？"},
        ]
        trace_store = ResultTraceStore(
            session_factory=self.session_factory,
            raw_store=FakeRawStore(raw_document),
        )
        pipeline = AccountPersonaPipeline(
            extractor=PersonaExtractor(api_key=None),
            trace_store=trace_store,
        )
        output = pipeline.run(
            raw_account_document=raw_document,
            questionnaire_context=questionnaire,
            prompt_version="v2.1",
            questionnaire_version="q-2026-03",
            model_params={"temperature": 0},
        )
        result = output["result"]
        self.assertIn("questionnaire_answers", result)
        self.assertEqual(result["prompt_version"], "v2.1")
        self.assertEqual(result["questionnaire_version"], "q-2026-03")
        trace = pipeline.query_result_trace(output["result_id"])
        self.assertEqual(trace["account_id"], "u_3")
        self.assertEqual(trace["raw_document"]["account_id"], "u_3")
        self.assertGreaterEqual(len(trace["evidence_references"]), 1)
