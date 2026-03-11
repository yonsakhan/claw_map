import os
import json
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.config import settings

INTERVIEW_PROMPT = ChatPromptTemplate.from_template("""
You are a role-playing AI. You are simulating a specific resident in a megacity based on the following persona profile.

**Your Persona:**
- Age: {age_group}
- Location: {location}
- Income Level: {income_level}
- Family Status: {fertility_status}
- Spatial Preferences: {spatial_preferences}
- Fertility Intent Score: {fertility_intent_score}/5

**The Scenario:**
An urban planner is interviewing you about how city infrastructure affects your decision to have children (or more children).

**Question:**
{question}

**Instructions:**
Answer the question in the first person ("I"). 
Be consistent with your persona's demographics and preferences. 
If you have low income, mention cost concerns. 
If you value parks, mention that.
Keep the answer concise (under 100 words).
""")

class VirtualInterviewer:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.model_name
        self.base_url = base_url or settings.openai_api_base
        
        if self.api_key:
            self.llm = ChatOpenAI(
                openai_api_key=self.api_key, 
                model=self.model_name, 
                openai_api_base=self.base_url,
                temperature=0.7
            )
            self.chain = INTERVIEW_PROMPT | self.llm | StrOutputParser()
        else:
            self.llm = None
            print("Warning: No OpenAI API Key provided. VirtualInterviewer will return mock responses.")

    def interview(self, persona: Dict[str, Any], question: str) -> str:
        """
        Conduct a virtual interview with the persona.
        """
        if not self.llm:
            return self._mock_response(persona, question)

        try:
            spatial_prefs = ", ".join(persona.get("spatial_preferences", []))
            
            response = self.chain.invoke({
                "age_group": persona.get("age_group", "Unknown"),
                "location": persona.get("location", "Unknown"),
                "income_level": persona.get("income_level", "Unknown"),
                "fertility_status": persona.get("fertility_status", "Unknown"),
                "spatial_preferences": spatial_prefs,
                "fertility_intent_score": persona.get("fertility_intent_score", 0),
                "question": question
            })
            return response
        except Exception as e:
            print(f"Error in interview: {e}")
            return self._mock_response(persona, question)

    def _mock_response(self, persona: Dict[str, Any], question: str) -> str:
        """Return a mock response."""
        return f"[MOCK] As a {persona.get('age_group')} year old in {persona.get('location')}, I think... (Response to: {question})"
