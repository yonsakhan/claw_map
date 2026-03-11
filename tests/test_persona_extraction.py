import unittest
import json
import os
from src.analysis.persona_extractor import PersonaExtractor

class TestPersonaExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = PersonaExtractor(api_key=None) # Use mock mode
        self.sample_profile = {
            "id": "test_user_1",
            "bio": "Mom of 2. Living in Shanghai. Love yoga.",
            "location": "Shanghai"
        }
        self.sample_posts = [
            {"content": "Taking the kids to the park."},
            {"content": "Traffic is terrible today."}
        ]

    def test_real_extraction(self):
        result = self.extractor.extract_persona(self.sample_profile, self.sample_posts)
        self.assertIn("age_group", result)
        self.assertIn("fertility_status", result)
        print("\nReal Extraction Result:", json.dumps(result, indent=2))

if __name__ == "__main__":
    unittest.main()
