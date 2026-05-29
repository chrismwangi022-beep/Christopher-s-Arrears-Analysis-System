"""
Gemini AI Client Wrapper
src/gemini_client.py

A minimal, production-safe client for interacting with the Google Gemini API.
"""

import streamlit as st
from google import genai
from google.genai import types
import logging

logger = logging.getLogger(__name__)

def generate_gemini_response(prompt: str) -> str:
    """
    Sends a prompt to the Gemini-2.5-Flash model and returns the response.
    
    Includes robust error handling for API failures and quota limits, 
    providing a safe fallback message to ensure UI stability.
    """
    try:
        # Requirement 1: Initialize using st.secrets
        api_key = st.secrets["GEMINI_API_KEY"]
        
        # Use session state to persist the client instance across Streamlit re-runs
        if "gemini_client_instance" not in st.session_state:
            st.session_state.gemini_client_instance = genai.Client(api_key=api_key)
        
        client = st.session_state.gemini_client_instance

        # Requirement 2 & 3: Model usage and generation function
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=1024,
            )
        )

        return response.text.strip() if response.text else "🛡️ AI returned an empty response."

    except Exception as e:
        # Requirement 4: Error handling and fallback messages
        error_str = str(e).lower()
        logger.error(f"Gemini API Error: {error_str}")

        if "429" in error_str or "quota" in error_str:
            return "🕒 AI Service quota reached. Please try again in a few moments."
        
        if "api_key" in error_str or "not found" in error_str:
            return "⚠️ AI Configuration error: API Key invalid or missing."

        return "🛡️ AI Service is temporarily unavailable. Proceeding with standard analytics."