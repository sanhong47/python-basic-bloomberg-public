import json
import logging
import os
from typing import Any

DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
AI_UNAVAILABLE_MESSAGE = "현재 서비스가 원활하지 않습니다"
logger = logging.getLogger(__name__)


def get_ai_runtime_status() -> dict[str, Any]:
    return {
        "provider": "openai-placeholder" if os.getenv("OPENAI_API_KEY") else "local-placeholder",
        "model": os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
    }


def ask_analysis_copilot(context: dict[str, Any], question: str) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key == "YOUR_OPENAI_API_KEY":
        return {
            "answer": AI_UNAVAILABLE_MESSAGE,
            "source": "fallback",
        }

    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, timeout=30.0, max_retries=1)
        response = client.responses.create(
            model=model,
            instructions=(
                "당신은 종목 분석 화면을 설명하는 AI Copilot입니다. "
                "주어진 화면 데이터만 근거로 한국어로 답하세요. "
                "가격이나 지표를 새로 계산하거나, 외부 지식·시세를 사용하지 마세요. "
                "화면에 없는 정보는 확인할 수 없다고 말하고, 투자 결정을 단정적으로 권유하지 마세요."
            ),
            input=json.dumps(
                {"question": question, "screen_data": context},
                ensure_ascii=False,
                default=str,
            ),
        )
        answer = response.output_text.strip()
        if not answer:
            raise RuntimeError("OpenAI 응답에 답변 텍스트가 없습니다.")
    except Exception:
        logger.exception("OpenAI 분석 Copilot 요청에 실패했습니다.")
        return {
            "answer": AI_UNAVAILABLE_MESSAGE,
            "source": "fallback",
        }

    return {
        "answer": answer,
        "source": "openai",
    }


def summarize_ops_context(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "answer": "10-8장에서 주문 상태와 보유현황을 읽어 AI 요약을 붙일 예정입니다.",
        "key_points": ["잔고와 주문 데이터를 요약하는 흐름 구현"],
        "risk_flags": ["현재는 스켈레톤 응답입니다."],
        "unknowns": [],
        "source": "skeleton",
    }


def summarize_news_briefing(company_name: str, articles: list[dict[str, Any]]) -> dict[str, Any]:
    titles = [str(article.get("title", "")).strip() for article in articles]
    titles = [title for title in titles if title]
    if not titles:
        return {
            "summary": f"{company_name} 관련 최근 기사가 없습니다.",
            "opportunities": [],
            "warnings": [],
            "needs_confirmation": [],
            "source": "local",
        }

    fallback_summary = "최근 관련 기사: " + " / ".join(titles[:3])
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key == "YOUR_OPENAI_API_KEY":
        return {
            "summary": fallback_summary,
            "opportunities": [],
            "warnings": [],
            "needs_confirmation": [],
            "source": "local",
        }

    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, timeout=30.0, max_retries=1)
        response = client.responses.create(
            model=model,
            instructions=(
                "당신은 한국어 뉴스 브리핑 작성자입니다. 제공된 기사 제목과 요약만 사용해 "
                "종목 관련 핵심 내용을 2~3문장으로 요약하세요. 기사에 없는 사실이나 "
                "투자 조언을 만들어내지 마세요."
            ),
            input=json.dumps(
                {
                    "company_name": company_name,
                    "articles": [
                        {
                            "title": article.get("title", ""),
                            "published_at": article.get("published_at", ""),
                            "description": article.get("description", ""),
                        }
                        for article in articles[:10]
                    ],
                },
                ensure_ascii=False,
            ),
        )
        summary = response.output_text.strip()
        if not summary:
            raise RuntimeError("OpenAI 응답에 뉴스 브리핑이 없습니다.")
    except Exception:
        logger.exception("OpenAI 뉴스 브리핑 요청에 실패했습니다.")
        return {
            "summary": fallback_summary,
            "opportunities": [],
            "warnings": [],
            "needs_confirmation": [],
            "source": "local",
        }

    return {
        "summary": summary,
        "opportunities": [],
        "warnings": [],
        "needs_confirmation": [],
        "source": "openai",
    }
