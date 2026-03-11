import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_API_BASE")
model = os.getenv("MODEL_NAME")

print(f"Testing with Model: {model}")
print(f"Base URL: {base_url}")

client = OpenAI(
    api_key=api_key,
    base_url=base_url,
)

try:
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手"},
            {"role": "user", "content": "你好"}
        ],
        temperature=0.3,
    )
    print("Response:", completion.choices[0].message.content)
except Exception as e:
    print("Error:", e)
