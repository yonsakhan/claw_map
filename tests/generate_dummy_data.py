import json
import random
import os
from datetime import datetime

def generate_dummy_data(output_file: str = "dummy_data.jsonl", num_profiles: int = 50):
    """Generate dummy user profiles and posts for testing."""
    
    locations = ["Shanghai", "Beijing", "Shenzhen", "Guangzhou", "Hangzhou"]
    bio_templates = [
        "Loving life in {loc}. 👶 Mom of 1.",
        "Work hard play hard. 💼",
        "Fashion | Beauty | Lifestyle 💄",
        "Just a normal person.",
        "Official store for baby products. 🛒", # Bot example
        "Digital nomad. 💻",
        "New mom, looking for advice. 🍼",
        "Planning for a baby soon. ❤️",
        "No kids, just cats. 🐱",
        "Professional agent for overseas study. 📚" # Bot example
    ]
    
    data = []
    
    for i in range(num_profiles):
        user_id = f"user_{i}"
        loc = random.choice(locations)
        is_bot = random.random() < 0.1 # 10% chance of being a bot-like profile
        
        if is_bot:
            bio = random.choice([b for b in bio_templates if "store" in b or "agent" in b])
        else:
            bio = random.choice([b for b in bio_templates if "store" not in b and "agent" not in b]).format(loc=loc)
            
        profile = {
            "id": user_id,
            "username": f"user_{i}_name",
            "display_name": f"User {i} {random.choice(['🌟', '❤️', '😊'])}",
            "bio": bio,
            "location": loc,
            "created_at": datetime.now().isoformat()
        }
        
        posts_count = 0 if random.random() < 0.1 else random.randint(1, 20)
        
        posts = []
        for j in range(posts_count):
            posts.append({
                "id": f"post_{i}_{j}",
                "user_id": user_id,
                "content": f"This is post {j} from user {i}. I love {loc}! #life #happy",
                "created_at": datetime.now().isoformat()
            })
            
        data.append({
            "profile": profile,
            "posts": posts,
            "posts_count": posts_count
        })
        
    with open(output_file, "w", encoding="utf-8") as f:
        for entry in data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
    print(f"Generated {num_profiles} profiles in {output_file}")

if __name__ == "__main__":
    generate_dummy_data()
