"""
Spread Capital Limited — AI Arrears Intelligence Personas
src/ai_agents/__init__.py (Refactored to Package)

Strictly for interpretation instructions and system prompts.
No mathematical logic allowed.
"""

import json
from typing import Any
import streamlit as st

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# Relative imports now resolve correctly within the ai_agents package
from src.ai_agents.branch_agent import BRANCH_AGENT_SYSTEM_PROMPT, BRANCH_PERFORMANCE_ANALYST_PROMPT
from src.ai_agents.risk_agent import RISK_ANALYSIS_AGENT_PROMPT
from src.ai_agents.recovery_agent import RECOVERY_STRATEGY_AGENT_PROMPT
from src.ai_agents.recovery_manager_agent import RECOVERY_MANAGER_PROMPT

RISK_ANALYST_SYSTEM_PROMPT = """
SPREAD CAPITAL LIMITED — ARREARS AI ENGINE

ROLE:
Senior Microfinance Credit Risk Analyst (Kenya)

MODE:
Fast Execution Data Interpreter (Executive Terminal)

CORE DIRECTIVE:
Convert arrears portfolio metrics into:
- short
- precise
- decision-ready insights

CRITICAL CONSTRAINTS:
- DO NOT perform any calculations or math.
- DO NOT verify or recompute percentages.
- TRUST all numbers in the provided JSON as absolute truth.
- NEVER invent branch names, officer names, or metrics not present in the data.

DO NOT:
- write reports
- narrate
- explain excessively
- repeat insights

━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Portfolio Snapshot
- Max 2 bullets
- Mention:
  total arrears
  PAR %
  trend
  key affected branches

- End with:
  🟢 Healthy
  🟡 Watchlist
  🔴 Critical

⚠️ Key Risks
- Max 3 bullets
- Risk + impact + branch/officer

🏢 Branch Insights
- Top 3 affected branches only
- Format:
  Branch → issue → trend

👤 Officer Flags
- Only risky officers
- Format:
  Branch → Officer → issue

💡 Recommendations
- Max 3 actions
- Operational only

━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━

- No paragraphs
- Use trend arrows: ↑ worsening, ↓ improving, → stable.
- Money values MUST use: KES X,XXX
"""

MODEL_NAME = "gemini-2.0-flash"

def _call_gemini(data: dict[str, Any], system_prompt: str) -> str:
    """Private shared runner to execute AI interpretation without logic duplication."""
    if not HAS_GENAI:
        return "⚠️ AI Engine library missing from environment."
        
    try:
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        # Strictly JSON-in, String-out interpretation
        prompt = f"INPUT DATA (JSON):\n{json.dumps(data)}\n\nTASK: Interpret this data."
        
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[system_prompt, prompt]
        )
        text = response.text
        return text.strip() if text else ""
    except Exception as e:
        return f"Interpretation Error: {str(e)}"

def run_risk_agent(data: dict[str, Any]) -> str:
    """Interprets systemic portfolio risk."""
    return _call_gemini(data, RISK_ANALYSIS_AGENT_PROMPT)

def run_recovery_agent(data: dict[str, Any]) -> str:
    """Interprets tactical recovery actions."""
    return _call_gemini(data, RECOVERY_STRATEGY_AGENT_PROMPT)

def run_branch_agent(data: dict[str, Any]) -> str:
    """Interprets branch-level performance disparities."""
    return _call_gemini(data, BRANCH_PERFORMANCE_ANALYST_PROMPT)

def run_standard_analyst(data: dict[str, Any]) -> str:
    """Standard executive summary interpreter."""
    return _call_gemini(data, RISK_ANALYST_SYSTEM_PROMPT)