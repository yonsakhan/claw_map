import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.analysis.account_persona_pipeline import AccountPersonaPipeline
from src.models.base import Base
from src.storage.result_trace_store import ResultTraceStore


class FakeRawStore:
    def __init__(self, raw_document):
        self.raw_document = raw_document

    def get_by_account_id(self, account_id: str):
        if account_id == self.raw_document.get("account_id"):
            return self.raw_document
        return None


class FakeExtractor:
    def extract_persona_from_features(
        self,
        account_feature_profile,
        questionnaire_context,
        prompt_version="v2",
        questionnaire_version="v1",
        model_params=None,
    ):
        model_params = model_params or {"temperature": 0}
        return {
            "age_group": "25-29",
            "location": "北京",
            "fertility_status": "Trying",
            "income_level": "Medium",
            "spatial_preferences": ["Transit", "Schools"],
            "fertility_intent_score": 3,
            "questionnaire_answers": [
                {
                    "question_id": str(item.get("id")),
                    "question": str(item.get("question")),
                    "answer": "我会重点考虑通勤、托育和学区配套。",
                    "reason_summary": "通勤与育儿设施是主要影响因素。",
                    "tendency_score": 3,
                    "confidence": 0.7,
                }
                for item in questionnaire_context
            ],
            "reasoning_summary": "基于 mock extractor 生成离线测试结果。",
            "account_id": account_feature_profile.get("account_id", ""),
            "account_feature_profile": account_feature_profile,
            "prompt_version": prompt_version,
            "questionnaire_version": questionnaire_version,
            "model_params": model_params,
            "evidence_references": account_feature_profile.get("evidence_references", []),
            "is_mock": True,
        }


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
            extractor=FakeExtractor(),
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
        self.assertTrue(result["is_mock"])
        self.assertEqual(result["prompt_version"], "v2.1")
        self.assertEqual(result["questionnaire_version"], "q-2026-03")
        trace = pipeline.query_result_trace(output["result_id"])
        self.assertEqual(trace["account_id"], "u_3")
        self.assertEqual(trace["raw_document"]["account_id"], "u_3")
        self.assertGreaterEqual(len(trace["evidence_references"]), 1)
