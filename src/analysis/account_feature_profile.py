from datetime import datetime, timezone
from typing import Any, Dict, List


class AccountFeatureBuilder:
    def build(self, raw_document: Dict[str, Any]) -> Dict[str, Any]:
        account_id = str(raw_document.get("account_id", ""))
        raw_data = raw_document.get("raw_data", {}) or raw_document
        profile = raw_data.get("profile", {}) or {}
        posts = raw_data.get("posts", []) or []
        likes = raw_data.get("likes", []) or []
        favorites = raw_data.get("favorites", []) or []
        follows = raw_data.get("follows", []) or []

        identity = self._identity_clues(profile)
        life_stage = self._life_stage_clues(profile, posts)
        spatial = self._spatial_clues(posts, likes, favorites)
        consumption = self._consumption_clues(profile, posts, likes, favorites)
        activity = self._activity_clues(posts, likes, favorites, follows)

        features = {
            "identity_clues": identity,
            "life_stage_clues": life_stage,
            "spatial_preference_clues": spatial,
            "consumption_clues": consumption,
            "activity_clues": activity,
        }
        completeness = self._completeness(features)
        return {
            "account_id": account_id,
            "feature_schema_version": "v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "features": features,
            "completeness": completeness,
            "evidence_references": self._evidence_references(features),
        }

    def _identity_clues(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        location = profile.get("location") or "Unknown"
        display_name = profile.get("display_name") or ""
        bio = profile.get("bio") or ""
        evidence = [item for item in [display_name, bio, location] if item]
        return self._feature_value(
            {"location": location, "display_name": display_name},
            evidence,
            {"profile_fields_present": len([i for i in [location, display_name, bio] if i])},
        )

    def _life_stage_clues(self, profile: Dict[str, Any], posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        snippets = self._extract_text_snippets(profile, posts, [])
        stage = "Unknown"
        rules = [
            ("pregnan", "Pregnant"),
            ("备孕", "Trying"),
            ("宝宝", "Parent"),
            ("孩子", "Parent"),
            ("单身", "Unmarried"),
            ("结婚", "Married"),
        ]
        merged = " ".join(snippets).lower()
        for keyword, value in rules:
            if keyword in merged:
                stage = value
                break
        return self._feature_value(
            {"life_stage": stage},
            snippets[:3],
            {"matched_rules": 0 if stage == "Unknown" else 1},
        )

    def _spatial_clues(
        self, posts: List[Dict[str, Any]], likes: List[Dict[str, Any]], favorites: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        snippets = self._extract_text_snippets({}, posts, likes + favorites)
        vocab = {
            "通勤": "Commute",
            "地铁": "Transit",
            "公园": "Parks",
            "医院": "Hospitals",
            "学校": "Schools",
            "安全": "Safety",
        }
        matched = []
        corpus = " ".join(snippets)
        for keyword, label in vocab.items():
            if keyword in corpus:
                matched.append(label)
        if not matched:
            matched = ["Unknown"]
        return self._feature_value(
            {"top_preferences": matched[:3]},
            snippets[:4],
            {"matched_keywords": len([m for m in matched if m != "Unknown"])},
        )

    def _consumption_clues(
        self,
        profile: Dict[str, Any],
        posts: List[Dict[str, Any]],
        likes: List[Dict[str, Any]],
        favorites: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        snippets = self._extract_text_snippets(profile, posts, likes + favorites)
        corpus = " ".join(snippets)
        high_keywords = ["奢侈", "高端", "五星", "名牌", "豪华"]
        low_keywords = ["平价", "省钱", "优惠", "折扣", "团购"]
        level = "Medium"
        if any(word in corpus for word in high_keywords):
            level = "High"
        if any(word in corpus for word in low_keywords):
            level = "Low"
        return self._feature_value(
            {"consumption_level": level},
            snippets[:3],
            {"signal_count": int(level != "Medium")},
        )

    def _activity_clues(
        self,
        posts: List[Dict[str, Any]],
        likes: List[Dict[str, Any]],
        favorites: List[Dict[str, Any]],
        follows: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        post_count = len(posts)
        like_count = len(likes)
        favorite_count = len(favorites)
        follow_count = len(follows)
        total = post_count + like_count + favorite_count + follow_count
        level = "low"
        if total >= 20:
            level = "high"
        elif total >= 8:
            level = "medium"
        evidence = [
            f"posts={post_count}",
            f"likes={like_count}",
            f"favorites={favorite_count}",
            f"follows={follow_count}",
        ]
        return self._feature_value(
            {"activity_level": level},
            evidence,
            {
                "posts_count": post_count,
                "likes_count": like_count,
                "favorites_count": favorite_count,
                "follows_count": follow_count,
                "total_interactions": total,
            },
        )

    def _feature_value(self, value: Dict[str, Any], evidence: List[str], stats: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "value": value,
            "evidence": evidence if evidence else ["fallback:insufficient_evidence"],
            "stats": stats,
            "is_fallback": len(evidence) == 0,
        }

    def _completeness(self, features: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        missing: List[str] = []
        for key, feature in features.items():
            if feature.get("is_fallback"):
                missing.append(key)
        total = len(features)
        score = round((total - len(missing)) / total, 2) if total else 0
        return {
            "score": score,
            "missing_feature_keys": missing,
            "is_complete": len(missing) == 0,
        }

    def _evidence_references(self, features: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        refs: List[Dict[str, Any]] = []
        for feature_key, feature in features.items():
            for idx, snippet in enumerate(feature.get("evidence", [])[:3]):
                refs.append(
                    {
                        "feature_key": feature_key,
                        "evidence_id": f"{feature_key}_{idx}",
                        "snippet": snippet,
                    }
                )
        return refs

    def _extract_text_snippets(
        self,
        profile: Dict[str, Any],
        posts: List[Dict[str, Any]],
        interactions: List[Dict[str, Any]],
    ) -> List[str]:
        snippets: List[str] = []
        for text in [profile.get("bio"), profile.get("display_name"), profile.get("location")]:
            if text:
                snippets.append(str(text))
        snippets.extend(self._extract_post_text(posts))
        snippets.extend(self._extract_post_text(interactions))
        return snippets

    def _extract_post_text(self, items: List[Dict[str, Any]]) -> List[str]:
        values: List[str] = []
        for item in items:
            text = item.get("content") or item.get("title") or item.get("text")
            if text:
                values.append(str(text))
        return values


def legacy_profile_posts_to_feature_profile(profile: Dict[str, Any], posts: List[Dict[str, Any]]) -> Dict[str, Any]:
    raw = {
        "account_id": str(profile.get("id", "")),
        "raw_data": {
            "profile": profile,
            "posts": posts,
            "likes": [],
            "favorites": [],
            "follows": [],
        },
    }
    return AccountFeatureBuilder().build(raw)
