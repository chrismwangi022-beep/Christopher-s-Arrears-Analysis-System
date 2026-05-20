from google import genai
import streamlit as st


client = genai.Client(
    api_key=st.secrets["GEMINI_API_KEY"]
)


@st.cache_data(ttl=3600)
def generate_ai_insights(metrics):

    prompt = f"""
    You are a senior microfinance credit risk analyst.

    Analyze the following arrears portfolio metrics.

    Metrics:
    {metrics}

    Generate:
    1. Executive Summary
    2. Key Risks
    3. Recommendations

    Requirements:
    - Professional
    - Concise
    - Mention trends
    - Mention risk areas
    - Do NOT invent numbers
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text