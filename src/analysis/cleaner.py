import re
import hashlib
from typing import Dict, Any, Optional

class DataCleaner:
    def __init__(self, salt: str = "claw_map_salt"):
        self.salt = salt

    def clean_text(self, text: Optional[str]) -> str:
        """Remove emojis and trim whitespace from text."""
        if not text:
            return ""
        # Remove emojis (simple regex for demo purposes)
        # This regex removes most emojis and symbols
        text = re.sub(r'[^\w\s,.]', '', text)
        return text.strip()

    def is_bot(self, profile: Dict[str, Any], posts_count: int) -> bool:
        """
        Check if the user is likely a bot or marketing account.
        Criteria:
        - 0 posts
        - Keywords in bio: 'shop', 'agent', 'store', '代购', '客服'
        """
        if posts_count == 0:
            return True
        
        bio = profile.get("bio", "").lower()
        bot_keywords = ['shop', 'agent', 'store', '代购', '客服', '商务', '合作']
        
        if any(keyword in bio for keyword in bot_keywords):
            return True
            
        return False

    def anonymize(self, user_id: str) -> str:
        """Anonymize user ID using SHA-256 hash with salt."""
        if not user_id:
            return ""
        return hashlib.sha256(f"{user_id}{self.salt}".encode()).hexdigest()

    def process_profile(self, raw_profile: Dict[str, Any], posts_count: int) -> Optional[Dict[str, Any]]:
        """
        Process a raw profile: clean, check if bot, and anonymize.
        Returns None if it's a bot, otherwise returns cleaned profile.
        """
        if self.is_bot(raw_profile, posts_count):
            return None
            
        cleaned_profile = raw_profile.copy()
        cleaned_profile['bio'] = self.clean_text(raw_profile.get('bio'))
        cleaned_profile['display_name'] = self.clean_text(raw_profile.get('display_name'))
        
        # Anonymize ID but keep original for reference if needed (or remove it)
        # Here we replace the ID with the hash
        original_id = raw_profile.get('id') or raw_profile.get('user_id')
        if original_id:
            cleaned_profile['id'] = self.anonymize(str(original_id))
            
        return cleaned_profile
