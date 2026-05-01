import unittest
from src.analysis.persona_extractor import (
    PersonaExtractor,
    PersonaExtractionConfigurationError,
    PersonaExtractionError,
)


class RaisingChain:
    def invoke(self, _payload):
        raise RuntimeError("upstream llm failure")


class TestPersonaExtractor(unittest.TestCase):
    def setUp(self):
        self.sample_feature_profile = {
            "account_id": "test_user_1",
            "features": {
                "identity_clues": {"value": {"location": "Shanghai"}},
                "life_stage_clues": {"value": {"life_stage": "Trying"}},
                "spatial_preference_clues": {"value": {"top_preferences": ["Transit"]}},
                "consumption_clues": {"value": {"consumption_level": "Medium"}},
                "activity_clues": {"value": {"activity_level": "medium"}},
            },
            "evidence_references": [{"source": "profile.bio", "snippet": "Mom of 2"}],
        }
        self.questionnaire = [{"id": "q1", "question": "哪些因素会影响你是否生育？"}]

    def test_missing_api_key_raises_without_mock_fallback(self):
        extractor = PersonaExtractor(api_key="", allow_mock_fallback=False)

        with self.assertRaises(PersonaExtractionConfigurationError):
            extractor.extract_persona_from_features(self.sample_feature_profile, self.questionnaire)

    def test_missing_api_key_returns_mock_when_explicitly_enabled(self):
        extractor = PersonaExtractor(api_key="", allow_mock_fallback=True)

        result = extractor.extract_persona_from_features(self.sample_feature_profile, self.questionnaire)
        self.assertIn("age_group", result)
        self.assertIn("fertility_status", result)
        self.assertTrue(result["is_mock"])
        self.assertEqual(result["fallback_reason"], "missing_api_key")

    def test_llm_failure_raises_without_mock_fallback(self):
        extractor = PersonaExtractor(api_key="test-key", allow_mock_fallback=False)
        extractor.chain = RaisingChain()

        with self.assertRaises(PersonaExtractionError):
            extractor.extract_persona_from_features(self.sample_feature_profile, self.questionnaire)

    def test_llm_failure_returns_mock_when_explicitly_enabled(self):
        extractor = PersonaExtractor(api_key="test-key", allow_mock_fallback=True)
        extractor.chain = RaisingChain()

        result = extractor.extract_persona_from_features(self.sample_feature_profile, self.questionnaire)
        self.assertTrue(result["is_mock"])
        self.assertEqual(result["fallback_reason"], "llm_error")

if __name__ == "__main__":
    unittest.main()
