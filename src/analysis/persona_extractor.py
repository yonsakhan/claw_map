import json
from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from src.analysis.account_feature_profile import legacy_profile_posts_to_feature_profile
from src.analysis.prompts import ACCOUNT_FEATURE_QUESTIONNAIRE_PROMPT
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
            self.chain = ACCOUNT_FEATURE_QUESTIONNAIRE_PROMPT | self.llm | JsonOutputParser()
        else:
            self.llm = None
            print("Warning: No OpenAI API Key provided. PersonaExtractor will return mock data.")

    def extract_persona(self, profile: Dict[str, Any], posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        account_feature_profile = legacy_profile_posts_to_feature_profile(profile, posts)
        return self.extract_persona_from_features(
            account_feature_profile=account_feature_profile,
            questionnaire_context=[],
            prompt_version="v2",
            questionnaire_version="legacy-v1",
            model_params={"temperature": 0},
        )

    def extract_persona_from_features(
        self,
        account_feature_profile: Dict[str, Any],
        questionnaire_context: List[Dict[str, Any]],
        prompt_version: str = "v2",
        questionnaire_version: str = "v1",
        model_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        model_params = model_params or {"temperature": 0}
        account_id = account_feature_profile.get("account_id", "")
        if not self.llm:
            return self._mock_extraction(account_feature_profile, questionnaire_context, prompt_version, questionnaire_version, model_params)
        try:
            feature_json = json.dumps(account_feature_profile, ensure_ascii=False)
            questionnaire_json = json.dumps(questionnaire_context, ensure_ascii=False)
            model_params_json = json.dumps(model_params, ensure_ascii=False)
            result = self.chain.invoke({
                "account_feature_profile_json": feature_json,
                "questionnaire_context_json": questionnaire_json,
                "model_params_json": model_params_json,
            })
            result["account_id"] = account_id
            result["account_feature_profile"] = account_feature_profile
            result["prompt_version"] = prompt_version
            result["questionnaire_version"] = questionnaire_version
            result["model_params"] = model_params
            result["evidence_references"] = account_feature_profile.get("evidence_references", [])
            return result
        except Exception as e:
            print(f"Error extracting persona: {e}")
            return self._mock_extraction(account_feature_profile, questionnaire_context, prompt_version, questionnaire_version, model_params)

    def _mock_extraction(
        self,
        account_feature_profile: Dict[str, Any],
        questionnaire_context: List[Dict[str, Any]],
        prompt_version: str,
        questionnaire_version: str,
        model_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        identity = account_feature_profile.get("features", {}).get("identity_clues", {}).get("value", {})
        life_stage = account_feature_profile.get("features", {}).get("life_stage_clues", {}).get("value", {})
        spatial = account_feature_profile.get("features", {}).get("spatial_preference_clues", {}).get("value", {})
        consumption = account_feature_profile.get("features", {}).get("consumption_clues", {}).get("value", {})
        activity = account_feature_profile.get("features", {}).get("activity_clues", {}).get("value", {})
        questionnaire_answers = []
        for idx, item in enumerate(questionnaire_context):
            question_id = str(item.get("id", idx + 1))
            question = str(item.get("question", ""))
            tendency_score = 3 if activity.get("activity_level") in {"medium", "high"} else 2
            questionnaire_answers.append(
                {
                    "question_id": question_id,
                    "question": question,
                    "answer": "我会综合居住成本、通勤和育儿支持再决定。",
                    "reason_summary": "特征显示对空间便利与生活成本有持续关注。",
                    "tendency_score": tendency_score,
                    "confidence": 0.62,
                }
            )
        return {
            "age_group": "25-29",
            "location": identity.get("location", "Unknown"),
            "fertility_status": life_stage.get("life_stage", "Unknown"),
            "income_level": consumption.get("consumption_level", "Medium"),
            "spatial_preferences": spatial.get("top_preferences", ["Unknown"]),
            "fertility_intent_score": 3 if activity.get("activity_level") != "low" else 2,
            "questionnaire_answers": questionnaire_answers,
            "reasoning_summary": "基于账号特征线索生成模拟结果。",
            "account_id": account_feature_profile.get("account_id", ""),
            "account_feature_profile": account_feature_profile,
            "prompt_version": prompt_version,
            "questionnaire_version": questionnaire_version,
            "model_params": model_params,
            "evidence_references": account_feature_profile.get("evidence_references", []),
            "is_mock": True,
        }
