"""LLM-as-reranker via OpenRouter."""

import json
import re

from langchain_openai import ChatOpenAI

from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, RERANKER_LLM_MODEL
from utils.json_parser import parse_llm_response


class LLMReranker:
    def __init__(self, model: str | None = None):
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is required for LLM reranking.")
        self.model = model or RERANKER_LLM_MODEL
        self.llm = ChatOpenAI(
            model=self.model,
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
            temperature=0,
        )

    def rerank(self, query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
        if not candidates:
            return []

        numbered = []
        for i, candidate in enumerate(candidates, start=1):
            text = candidate["text"][:500]
            numbered.append(f"{i}. {text}")

        prompt = (
            "Rate each passage for relevance to the query on a scale of 0-10 "
            "(10 = directly answers the query).\n"
            "Return ONLY a JSON array of objects: "
            '[{"index": 1, "score": 8.5}, ...] including every passage index.\n\n'
            f"Query: {query}\n\nPassages:\n" + "\n".join(numbered)
        )
        response = self.llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        scores_by_index = self._parse_scores(content, len(candidates))

        ranked = []
        for i, candidate in enumerate(candidates, start=1):
            score = scores_by_index.get(i, 0.0)
            ranked.append({**candidate, "rerank_score": float(score)})

        ranked.sort(key=lambda item: item["rerank_score"], reverse=True)
        return ranked[:top_k]

    @staticmethod
    def _parse_scores(content: str, expected: int) -> dict[int, float]:
        parsed = parse_llm_response(content)
        scores: dict[int, float] = {}

        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and "index" in item:
                    scores[int(item["index"])] = float(item.get("score", 0))
        elif isinstance(parsed, dict):
            for key, value in parsed.items():
                if str(key).isdigit():
                    scores[int(key)] = float(value)

        if not scores:
            match = re.search(r"\[.*\]", content, re.DOTALL)
            if match:
                try:
                    items = json.loads(match.group())
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict) and "index" in item:
                                scores[int(item["index"])] = float(item.get("score", 0))
                except json.JSONDecodeError:
                    pass

        if not scores:
            for i in range(1, expected + 1):
                scores[i] = 0.0
        return scores
