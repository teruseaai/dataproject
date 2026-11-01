import concurrent.futures
import os

import requests
from dotenv import load_dotenv

load_dotenv()

URL = "https://openrouter.ai/api/v1/chat/completions"


def _request(model, prompt):
    resp = requests.post(
        URL,
        headers={"Authorization": "Bearer " + os.getenv("OPENROUTER_API_KEY", "")},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000,
            "reasoning": {"effort": "low"},
        },
        timeout=120,
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    if not text or not text.strip():
        raise RuntimeError("빈 응답")
    return text


def call_model(model, prompt, limit=120):
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = pool.submit(_request, model, prompt)
    try:
        return future.result(timeout=limit)
    finally:
        pool.shutdown(wait=False)

def run_with_fallback(models, prompt, check, call=None, limit=120, progress=None):
    """
    models: 모델 이름 목록 (1차, 2차, 3차 순서)
    prompt: AI에게 보낼 글
    check: 응답 글을 받아 (통과 여부, 이유)를 돌려주는 함수
    call: 모델을 부르는 함수(시험용으로 바꿀 수 있음). 기본은 call_model
    성공하면 (응답, 몇 차 모델, 기록)을, 모두 실패하면 (None, None, 기록)을 돌려줌
    """
    call = call or call_model
    log = []
    for number, model in enumerate(models, 1):
        if progress:
            progress(number)
        try:
            text = call(model, prompt, limit)
        except concurrent.futures.TimeoutError:
            log.append(f"{number}차 모델: {limit}초 안에 응답하지 않아 다음 모델로 넘어감")
            continue
        except Exception as e:
            log.append(f"{number}차 모델: 실패({type(e).__name__})하여 다음 모델로 넘어감")
            continue

        ok, reason = check(text)
        if ok:
            log.append(f"{number}차 모델: 배정안이 검사를 통과함")
            return text, number, log
        log.append(f"{number}차 모델: 배정안이 검사를 통과하지 못해 다음 모델로 넘어감({reason})")

    return None, None, log