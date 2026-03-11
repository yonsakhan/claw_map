import json
import os
from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from src.analysis.prompts import PERSONA_EXTRACTION_PROMPT
from src.config import settings

class PersonaExtractor:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.model_name
        self.base_url = base_url or settings.openai_api_base
        
        if self.api_key:
            self.llm = ChatOpenAI(
                openai_api_key=self.api_key,
                model=self.model_name,
                openai_api_base=self.base_url,
                temperature=0
            )
            self.chain = PERSONA_EXTRACTION_PROMPT | self.llm | JsonOutputParser()
        else:
            self.llm = None
            print("Warning: No OpenAI API Key provided. PersonaExtractor will return mock data.")

    def extract_persona(self, profile: Dict[str, Any], posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract structured persona from profile and posts.
        """
        if not self.llm:
            return self._mock_extraction(profile)

        try:
            # Prepare inputs
            profile_json = json.dumps(profile, ensure_ascii=False)
            posts_json = json.dumps([p['content'] for p in posts], ensure_ascii=False)
            
            result = self.chain.invoke({
                "profile_json": profile_json,
                "posts_json": posts_json
            })
            return result
        except Exception as e:
            print(f"Error extracting persona: {e}")
            return self._mock_extraction(profile)

    def _mock_extraction(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Return a mock persona for testing/development without API cost."""
        return {
            "age_group": "25-29",
            "location": profile.get("location", "Unknown"),
            "fertility_status": "Unmarried",
            "income_level": "Medium",
            "spatial_preferences": ["Commute time", "Safety"],
            "fertility_intent_score": 3,
            "is_mock": True
        }
