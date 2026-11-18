"""외부 LLM 호출을 한 곳에 모아 둔 파일. 나중에 다른 회사의 모델로 바꿔도 이 파일만 고치면 된다.
키와 모델 이름은 코드에 적지 않고 .env 에서 읽는다.
  OPENAI_API_KEY=sk-...      (없으면 AI 기능은 '설정 안 됨' 오류를 돌려주고, 가짜 결과를 만들어 내지 않는다)
  LLM_MODEL=gpt-4o-mini      (선택. 기본값. 쓸 수 있는 모델 이름은 OpenAI 문서에서 확인한다)
  LLM_TIMEOUT=15             (선택. 초)"""
import os


class LLMNotConfigured(Exception):
    """API 키가 없을 때."""


def complete(system, user, max_tokens=400):
    """system/user 문장을 보내고 모델이 쓴 글자만 돌려준다. 답은 JSON 한 덩어리로 받는다."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise LLMNotConfigured()
    from openai import OpenAI    # 키가 없는 환경에서도 서버가 뜨도록 여기서 불러온다
    client = OpenAI(api_key=key, timeout=float(os.getenv("LLM_TIMEOUT", "15")), max_retries=1)
    resp = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_completion_tokens=max_tokens,
        response_format={"type": "json_object"},     # 프롬프트에 'JSON' 이라는 말이 들어 있어야 한다
    )
    return resp.choices[0].message.content or ""
