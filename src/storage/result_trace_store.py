from typing import Any, Dict, Optional

from src.db.session import get_session_factory
from src.models.persona import AgentPersona
from src.storage.mongo_store import MongoRawStore


class ResultTraceStore:
    def __init__(self, session_factory=None, raw_store: Optional[MongoRawStore] = None):
        self.session_factory = session_factory or get_session_factory()
        self.raw_store = raw_store or MongoRawStore()

    def save_result(self, result: Dict[str, Any]) -> int:
        session = self.session_factory()
        try:
            raw_account_id = str(result.get("original_id") or result.get("account_id") or "")
            row = AgentPersona(
                original_id=raw_account_id,
                age_group=result.get("age_group"),
                location=result.get("location"),
                fertility_status=result.get("fertility_status"),
                income_level=result.get("income_level"),
                spatial_preferences=result.get("spatial_preferences", []),
                fertility_intent_score=result.get("fertility_intent_score", 0),
                questionnaire_answers=result.get("questionnaire_answers", []),
                reasoning_summary=result.get("reasoning_summary"),
                prompt_version=result.get("prompt_version"),
                questionnaire_version=result.get("questionnaire_version"),
                model_params=result.get("model_params"),
                feature_snapshot=result.get("account_feature_profile"),
                evidence_references=result.get("evidence_references", []),
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return int(row.id)
        finally:
            session.close()

    def query_trace(self, result_id: int) -> Optional[Dict[str, Any]]:
        session = self.session_factory()
        try:
            row = session.query(AgentPersona).filter(AgentPersona.id == int(result_id)).one_or_none()
            if not row:
                return None
            feature_snapshot = row.feature_snapshot or {}
            raw_lookup_id = str(feature_snapshot.get("account_id") or row.original_id)
            raw_document = self.raw_store.get_by_account_id(raw_lookup_id)
            return {
                "result_id": row.id,
                "account_id": row.original_id,
                "prompt_version": row.prompt_version,
                "questionnaire_version": row.questionnaire_version,
                "model_params": row.model_params,
                "evidence_references": row.evidence_references or [],
                "feature_snapshot": feature_snapshot,
                "questionnaire_answers": row.questionnaire_answers or [],
                "raw_document": raw_document,
            }
        finally:
            session.close()
