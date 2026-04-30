import difflib
from reflection.prompts import (
    REFLECTION_HEADER,
    REFLECTION_TEMPLATE,
    CRITIC_SYSTEM_PROMPT,
    PRODUCER_SYSTEM_PROMPT,
)
from utils.llm import call_llm_async
from utils.json_parser import clean_llm_json


def _confidence_summary(previous_results: list[dict]) -> str:
    confidences = [
        r.get("result", {}).get("confidence", 0.0)
        for r in previous_results
        if isinstance(r, dict) and isinstance(r.get("result"), dict)
    ]
    if not confidences:
        return "No prior confidence available."

    avg = sum(confidences) / len(confidences)
    return f"avg={avg:.2f}, count={len(confidences)}"


def _infer_weaknesses(previous_results: list[dict]) -> str:
    low_conf = [
        r for r in previous_results
        if isinstance(r, dict)
        and isinstance(r.get("result"), dict)
        and r["result"].get("confidence", 0.0) < 0.5
    ]
    if not previous_results:
        return "No prior outputs."
    if low_conf:
        return "Some previous outputs had low confidence or weak relevance."
    return "Minor consistency and evidence gaps may remain."


def _infer_improvements(previous_results: list[dict]) -> str:
    if not previous_results:
        return (
            "Give a direct answer with key metrics, then risks, then near-term outlook."
        )
    return (
        "Use concrete metrics, avoid speculative claims, and include clear risk notes "
        "with brief uncertainty statements."
    )


def build_reflection_block(previous_results: list[dict]) -> str:
    confidence_summary = _confidence_summary(previous_results)
    weaknesses = _infer_weaknesses(previous_results)
    improvements = _infer_improvements(previous_results)

    return REFLECTION_HEADER + REFLECTION_TEMPLATE.format(
        confidence_summary=confidence_summary,
        weaknesses=weaknesses,
        improvements=improvements
    )


def inject_reflection(prompt: str, previous_results: list[dict]) -> str:
    reflection = build_reflection_block(previous_results)
    return f"{reflection}\nTask:\n{prompt}"


def _aggregate_score(scores: dict) -> float:
    keys = [
        "factual_grounding",
        "completeness",
        "internal_consistency",
        "domain_tone",
        "unsupported_claims_control",
    ]
    vals = [float(scores.get(k, 0.0)) for k in keys]
    return sum(vals) / len(vals)


async def _critic_evaluate(domain: str, draft: str, critic_model: str) -> dict:
    user_prompt = (
        f"Domain: {domain}\n\n"
        f"Draft:\n{draft}\n\n"
        "Evaluate with the required rubric and return strict JSON only."
    )
    response = await call_llm_async(
        critic_model,
        [
            {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    parsed = clean_llm_json(response)
    if not isinstance(parsed, dict):
        return {
            "scores": {
                "factual_grounding": 0,
                "completeness": 0,
                "internal_consistency": 0,
                "domain_tone": 0,
                "unsupported_claims_control": 0,
            },
            "revision_instructions": [
                "Critic response was invalid JSON. Improve factual grounding and consistency."
            ],
            "unsupported_claims": [],
            "summary": "Critic parse failure.",
        }
    return parsed


async def _producer_rewrite(
    domain: str, draft: str, revision_instructions: list[str], producer_model: str
) -> str:
    instructions = "\n".join(f"- {x}" for x in revision_instructions) or "- Improve clarity."
    user_prompt = (
        f"Domain: {domain}\n\n"
        f"Current draft:\n{draft}\n\n"
        f"Revision instructions:\n{instructions}\n\n"
        "Return the revised brief only."
    )
    response = await call_llm_async(
        producer_model,
        [
            {"role": "system", "content": PRODUCER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response if isinstance(response, str) else str(response)


async def run_reflexion_loop(
    domain: str,
    initial_draft: str,
    producer_model: str,
    critic_model: str,
    threshold: float = 8.0,
    max_iterations: int = 3,
) -> tuple[str, list[float]]:
    current = initial_draft
    score_history: list[float] = []
    best_score = -1.0
    stalled = 0

    for i in range(1, max_iterations + 1):
        critic = await _critic_evaluate(domain, current, critic_model)
        scores = critic.get("scores", {})
        agg = _aggregate_score(scores)
        score_history.append(agg)

        print(
            f"[REFLEXION] Iteration {i} scores: "
            f"factual={scores.get('factual_grounding', 0)}, "
            f"complete={scores.get('completeness', 0)}, "
            f"consistency={scores.get('internal_consistency', 0)}, "
            f"tone={scores.get('domain_tone', 0)}, "
            f"unsupported_ctrl={scores.get('unsupported_claims_control', 0)}, "
            f"aggregate={agg:.2f}"
        )

        if agg >= threshold:
            print(f"[REFLEXION] Stop: threshold reached ({agg:.2f} >= {threshold}).")
            break

        if agg <= best_score + 1e-6:
            stalled += 1
        else:
            stalled = 0
            best_score = agg

        if stalled >= 1:
            print("[REFLEXION] Stop: plateau/regression detected.")
            break

        instructions = critic.get("revision_instructions", [])
        revised = await _producer_rewrite(domain, current, instructions, producer_model)

        diff = difflib.unified_diff(
            current.splitlines(),
            revised.splitlines(),
            fromfile=f"iter_{i}_before",
            tofile=f"iter_{i}_after",
            lineterm="",
        )
        print("[REFLEXION] Draft diff:")
        for line in diff:
            print(line)

        current = revised

    return current, score_history


async def apply_reflexion_to_result(
    domain: str, result: dict, producer_model: str, critic_model: str
) -> dict:
    if not isinstance(result, dict):
        return result

    answer = result.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return result

    improved_answer, score_history = await run_reflexion_loop(
        domain=domain,
        initial_draft=answer,
        producer_model=producer_model,
        critic_model=critic_model,
        threshold=8.0,
        max_iterations=3,
    )
    result["answer"] = improved_answer
    result["reflection_scores"] = score_history
    return result
