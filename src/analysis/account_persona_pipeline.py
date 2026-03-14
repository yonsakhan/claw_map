from typing import Any, Dict, List, Optional

from src.analysis.account_feature_profile import AccountFeatureBuilder
from src.analysis.persona_extractor import PersonaExtractor
from src.storage.result_trace_store import ResultTraceStore


class AccountPersonaPipeline:
    def __init__(
        self,
        extractor: Optional[PersonaExtractor] = None,
        feature_builder: Optional[AccountFeatureBuilder] = None,
        trace_store: Optional[ResultTraceStore] = None,
    ):
        self.extractor = extractor or PersonaExtractor()
        self.feature_builder = feature_builder or AccountFeatureBuilder()
        self.trace_store = trace_store or ResultTraceStore()

    def run(
        self,
        raw_account_document: Dict[str, Any],
        questionnaire_context: List[Dict[str, Any]],
        prompt_version: str = "v2",
        questionnaire_version: str = "v1",
        model_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        feature_profile = self.feature_builder.build(raw_account_document)
        result = self.extractor.extract_persona_from_features(
            account_feature_profile=feature_profile,
            questionnaire_context=questionnaire_context,
            prompt_version=prompt_version,
            questionnaire_version=questionnaire_version,
            model_params=model_params,
        )
        result_id = self.trace_store.save_result(result)
        return {
            "result_id": result_id,
            "result": result,
            "feature_profile": feature_profile,
        }

    def query_result_trace(self, result_id: int) -> Optional[Dict[str, Any]]:
        return self.trace_store.query_trace(result_id)
