import os

import pytest
from dotenv import load_dotenv


def test_kimi_direct_smoke():
    """LLM 直连冒烟测试（默认跳过）。

    说明：该测试需要配置真实的 OPENAI_API_KEY / OPENAI_API_BASE / MODEL_NAME，
    且会产生真实的 API 调用成本，因此默认跳过。
    """

    load_dotenv()

    if os.getenv("RUN_LLM_SMOKE") != "1":
        pytest.skip("set RUN_LLM_SMOKE=1 to enable LLM smoke test")

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_API_BASE")
    model = os.getenv("MODEL_NAME")

    if not api_key:
        pytest.skip("OPENAI_API_KEY is not set")
    if not base_url:
        pytest.skip("OPENAI_API_BASE is not set")
    if not model:
        pytest.skip("MODEL_NAME is not set")

    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手"},
            {"role": "user", "content": "你好"},
        ],
        temperature=0.3,
    )
    assert completion.choices[0].message.content
