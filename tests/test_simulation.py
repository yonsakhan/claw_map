import unittest
from src.simulation.interviewer import VirtualInterviewer

class TestSimulation(unittest.TestCase):
    def setUp(self):
        self.interviewer = VirtualInterviewer(api_key=None)
        self.persona = {
            "age_group": "30-34",
            "location": "Beijing",
            "income_level": "High",
            "fertility_status": "Married-No-Kids",
            "spatial_preferences": ["Parks", "Good Schools"],
            "fertility_intent_score": 4
        }

    def test_real_interview(self):
        question = "How does access to parks influence your decision to have a child?"
        response = self.interviewer.interview(self.persona, question)
        print(f"\nQuestion: {question}")
        print(f"Response: {response}")
        self.assertTrue(len(response) > 20)
        self.assertNotIn("[MOCK]", response)

if __name__ == "__main__":
    unittest.main()
