import unittest

from src.analysis.account_feature_profile import AccountFeatureBuilder


class TestAccountFeatureBuilder(unittest.TestCase):
    def test_build_feature_profile_with_evidence_and_completeness(self):
        builder = AccountFeatureBuilder()
        raw_document = {
            "account_id": "u_2",
            "raw_data": {
                "profile": {"id": "u_2", "location": "上海", "bio": "已婚，计划二胎"},
                "posts": [{"id": "p1", "title": "公园遛娃路线"}, {"id": "p2", "content": "通勤和学区很关键"}],
                "likes": [{"id": "l1", "title": "儿童医院就诊攻略"}],
                "favorites": [{"id": "c1", "title": "平价母婴用品清单"}],
                "follows": [{"id": "f1", "name": "本地妈妈社群"}],
            },
        }
        feature_profile = builder.build(raw_document)
        self.assertEqual(feature_profile["account_id"], "u_2")
        self.assertIn("features", feature_profile)
        self.assertIn("identity_clues", feature_profile["features"])
        self.assertIn("evidence_references", feature_profile)
        self.assertGreater(len(feature_profile["evidence_references"]), 0)
        self.assertIn("completeness", feature_profile)
        self.assertTrue(0 <= feature_profile["completeness"]["score"] <= 1)
