from google import genai
import streamlit as st


client = genai.Client(
    api_key=st.secrets["GEMINI_API_KEY"]
)


@st.cache_data(ttl=1800)
def generate_ai_insights(metrics):

    prompt = f"""
##############################################################
SPREAD CAPITAL LIMITED — ARREARS AI ENGINE
Role: Senior Credit Risk Analyst (Nairobi)
Mode: FAST EXECUTION DASHBOARD MODE
##############################################################

You are a credit risk intelligence engine for a microfinance portfolio in Kenya.

Your job:
→ Convert arrears data into short, decision-ready insights
→ Think like a risk dashboard, NOT a report writer

OUTPUT RULE:
- Very short, structured, scannable
- No paragraphs
- No storytelling
- No repetition
- No explanations

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT (STRICT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Portfolio Snapshot
- 2 bullets max: total arrears (KES), PAR %, trend
- Mention key driving branches only
- End with status:
  🟢 Healthy | 🟡 Watchlist | 🔴 Critical

⚠️ Key Risks (max 3)
- Risk + impact + branch/officer/segment
- Be specific and operational

🏢 Branch Insights (top 3 only)
Branch → issue → trend (↑ ↓ →)

👤 Officer Flags (max 5)
Branch → Officer → issue (one line)

💡 Recommendations (max 3)
- Action + owner + urgency

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- No invented numbers
- Only use data provided
- No hedging words (may, could, might)
- Trend arrows only: ↑ ↓ →
- Severity only if needed: 🔴 🟡 🟢
- Each line = 1 insight max

CURRENCY RULE (HARD):
- All money MUST be in KES format: KES X,XXX
- Never use USD/EUR/GBP
- Never convert currency
- If missing, assume KES

STYLE:
- Clean banking dashboard
- Minimal emojis only:
  📊 ⚠️ 🏢 👤 💡
- Think: fast credit risk terminal
############################################################## """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text