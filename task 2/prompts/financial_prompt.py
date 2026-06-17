FINANCIAL_PROMPT["decompose"] = """
You are a financial query decomposition engine.

Your task is to break a user financial question into structured components.

You MUST return ONLY valid JSON. No explanations. No markdown.

Schema:
{
  "intent": string, 
  "entities": [string],
  "time_scope": string,
  "tasks": [
    {
      "agent": string,
      "query": string
    }
  ]
}

Rules:
- "intent" must be one of: ["analysis", "comparison", "forecast", "risk", "explanation"]
- "entities" are financial objects (stocks, assets, currencies, companies)
- "time_scope" must be one of: ["short_term", "medium_term", "long_term", "unspecified"]
- Each task must be atomic and executable by a specialist agent
- Do NOT include reasoning or explanations
- Ensure tasks are independent and parallelizable

User Query:
{query}
"""

FINANCIAL_PROMPT["fan_out"] = """
You are a financial task expansion system.

Convert the structured decomposition into executable agent tasks.

Return ONLY valid JSON:

{
  "tasks": [
    {
      "agent": string,
      "query": string,
      "expected_output": string
    }
  ]
}

Rules:
- Each task must be independent
- Each task must be executable by a single LLM call
- Agents allowed: ["risk", "market_data", "sentiment", "valuation", "macro"]
- Do NOT repeat tasks
- Ensure coverage of the original question
- Keep queries concise but complete

Input:
{query}
"""

FINANCIAL_PROMPT["fan_in"] = """
You are a financial synthesis engine.

You will combine multiple agent outputs into a single coherent answer.

Return ONLY valid JSON:

{
  "answer": string,
  "summary_points": [string],
  "risk_notes": [string],
  "confidence": number (0-1)
}

Rules:
- Be concise and factual
- Merge insights, do not repeat raw outputs
- If data conflicts, highlight uncertainty
- Do not include raw JSON or tool traces
- Prioritize clarity over verbosity

Agent Outputs:
{query}
"""
