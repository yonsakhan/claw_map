import json
import logging
from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from src.analysis.account_feature_profile import legacy_profile_posts_to_feature_profile
from src.analysis.prompts import (
    ACCOUNT_FEATURE_QUESTIONNAIRE_PROMPT,
    PERSONA_EXTRACTION_PROMPT,
    XHS_PERSONA_EXTRACTION_PROMPT,
    XHS_QUESTIONNAIRE_PROMPT,
)
from src.config import settings

logger = logging.getLogger(__name__)


class PersonaExtractionError(RuntimeError):
    """Raised when persona extraction cannot complete successfully."""


class PersonaExtractionConfigurationError(PersonaExtractionError):
    """Raised when persona extraction is requested without usable LLM config."""


class PersonaExtractor:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        allow_mock_fallback: bool = False,
        use_chinese_prompt: bool = True,  # 新增：是否使用中文 Prompt
    ):
        self.api_key = settings.openai_api_key if api_key is None else api_key
        self.model_name = settings.model_name if model_name is None else model_name
        self.base_url = settings.openai_api_base if base_url is None else base_url
        self.allow_mock_fallback = allow_mock_fallback
        self.use_chinese_prompt = use_chinese_prompt

        if self.api_key:
            self.llm = ChatOpenAI(
                openai_api_key=self.api_key,
                model=self.model_name,
                openai_api_base=self.base_url,
                temperature=0
            )
            # 根据语言偏好选择 Prompt
            if self.use_chinese_prompt:
                self.chain = XHS_PERSONA_EXTRACTION_PROMPT | self.llm | JsonOutputParser()
                self.questionnaire_chain = XHS_QUESTIONNAIRE_PROMPT | self.llm | JsonOutputParser()
            else:
                self.chain = PERSONA_EXTRACTION_PROMPT | self.llm | JsonOutputParser()
                self.questionnaire_chain = ACCOUNT_FEATURE_QUESTIONNAIRE_PROMPT | self.llm | JsonOutputParser()
        else:
            self.llm = None
            self.chain = None
            self.questionnaire_chain = None
            if self.allow_mock_fallback:
                logger.warning(
                    "No OpenAI API key provided; PersonaExtractor will use explicit mock fallback mode."
                )

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
            if self.allow_mock_fallback:
                return self._mock_extraction(
                    account_feature_profile,
                    questionnaire_context,
                    prompt_version,
                    questionnaire_version,
                    model_params,
                    fallback_reason="missing_api_key",
                )
            raise PersonaExtractionConfigurationError(
                "OPENAI_API_KEY is not configured for PersonaExtractor and mock fallback is disabled."
            )
        try:
            feature_json = json.dumps(account_feature_profile, ensure_ascii=False)
            questionnaire_json = json.dumps(questionnaire_context, ensure_ascii=False)
            model_params_json = json.dumps(model_params, ensure_ascii=False)
            
            # 根据是否有问卷上下文选择不同的 chain
            if questionnaire_context:
                result = self.questionnaire_chain.invoke({
                    "account_feature_profile_json": feature_json,
                    "questionnaire_context_json": questionnaire_json,
                    "model_params_json": model_params_json,
                })
            else:
                result = self.chain.invoke({
                    "account_feature_profile_json": feature_json,
                    "questionnaire_context_json": questionnaire_json,
                    "model_params_json": model_params_json,
                })
            
            # 标准化输出格式
            result = self._normalize_output(result)
            
            result["account_id"] = account_id
            result["account_feature_profile"] = account_feature_profile
            result["prompt_version"] = prompt_version
            result["questionnaire_version"] = questionnaire_version
            result["model_params"] = model_params
            result["evidence_references"] = account_feature_profile.get("evidence_references", [])
            return result
        except Exception as e:
            logger.exception("Persona extraction failed for account_id=%s", account_id)
            if self.allow_mock_fallback:
                return self._mock_extraction(
                    account_feature_profile,
                    questionnaire_context,
                    prompt_version,
                    questionnaire_version,
                    model_params,
                    fallback_reason="llm_error",
                )
            raise PersonaExtractionError(f"Persona extraction failed for account_id={account_id}") from e

    def _normalize_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化输出格式，确保所有字段都存在"""
        normalized = {
            "age_group": result.get("age_group", "Unknown"),
            "location": result.get("location", "Unknown"),
            "fertility_status": result.get("fertility_status", "Unknown"),
            "income_level": result.get("income_level", "Unknown"),
            "spatial_preferences": result.get("spatial_preferences", []),
            "fertility_intent_score": result.get("fertility_intent_score", 0),
            "reasoning_summary": result.get("reasoning_summary", ""),
            "confidence": result.get("confidence", 0.0),
            "evidence_summary": result.get("evidence_summary", {}),
        }
        
        # 处理问卷答案
        if "questionnaire_answers" in result:
            normalized["questionnaire_answers"] = result["questionnaire_answers"]
        
        return normalized

    def _mock_extraction(
        self,
        account_feature_profile: Dict[str, Any],
        questionnaire_context: List[Dict[str, Any]],
        prompt_version: str,
        questionnaire_version: str,
        model_params: Dict[str, Any],
        fallback_reason: str,
    ) -> Dict[str, Any]:
        # 从特征画像中提取信息
        features = account_feature_profile.get("features", {})
        
        # 身份信息
        identity = features.get("identity_clues", {}).get("value", {})
        location = identity.get("location", "Unknown")
        display_name = identity.get("display_name", "")
        
        # 生活阶段
        life_stage = features.get("life_stage_clues", {}).get("value", {})
        fertility_status = life_stage.get("life_stage", "Unknown")
        
        # 空间偏好
        spatial = features.get("spatial_preference_clues", {}).get("value", {})
        spatial_preferences = spatial.get("top_preferences", ["Unknown"])
        
        # 消费水平
        consumption = features.get("consumption_clues", {}).get("value", {})
        income_level = consumption.get("consumption_level", "Medium")
        
        # 活跃度
        activity = features.get("activity_clues", {}).get("value", {})
        activity_level = activity.get("activity_level", "low")
        
        # 年龄段
        age = features.get("age_clues", {}).get("value", {})
        age_group = age.get("age_group", "Unknown")
        
        # 生育意愿
        fertility = features.get("fertility_clues", {}).get("value", {})
        fertility_intent = fertility.get("fertility_intent", "unknown")
        fertility_score = fertility.get("fertility_score", 0)
        
        # 根据生育状态调整评分
        if fertility_status == "备孕中":
            fertility_score = max(fertility_score, 4)
        elif fertility_status == "怀孕中":
            fertility_score = max(fertility_score, 4)
        elif fertility_status in ["已育1孩", "已育2孩+"]:
            fertility_score = max(fertility_score, 3)
        elif fertility_status == "未婚":
            fertility_score = min(fertility_score, 2)
        
        # 构建问卷答案
        questionnaire_answers = []
        for idx, item in enumerate(questionnaire_context):
            question_id = str(item.get("id", idx + 1))
            question = str(item.get("question", ""))
            tendency_score = 3 if activity_level in {"medium", "high"} else 2
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
        
        # 构建证据摘要
        evidence_summary = {
            "age_evidence": features.get("age_clues", {}).get("evidence", [])[:2],
            "fertility_evidence": features.get("fertility_clues", {}).get("evidence", [])[:2],
            "income_evidence": features.get("consumption_clues", {}).get("evidence", [])[:2],
            "spatial_evidence": features.get("spatial_preference_clues", {}).get("evidence", [])[:2],
        }
        
        return {
            "age_group": age_group,
            "location": location,
            "fertility_status": fertility_status,
            "income_level": income_level,
            "spatial_preferences": spatial_preferences,
            "fertility_intent_score": fertility_score,
            "questionnaire_answers": questionnaire_answers,
            "reasoning_summary": "基于账号特征线索生成模拟结果。",
            "confidence": 0.6,
            "evidence_summary": evidence_summary,
            "account_id": account_feature_profile.get("account_id", ""),
            "account_feature_profile": account_feature_profile,
            "prompt_version": prompt_version,
            "questionnaire_version": questionnaire_version,
            "model_params": model_params,
            "evidence_references": account_feature_profile.get("evidence_references", []),
            "is_mock": True,
            "fallback_reason": fallback_reason,
        }
