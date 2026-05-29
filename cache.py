"""
Recovery Engine Cache

Streamlit-compatible caching layer for recovery reports.
"""

import streamlit as st
from typing import Optional
from .schema import RecoveryReport

class RecoveryCache:
    """Handles persistence of generated reports in session state or memory."""

    @staticmethod
    def get_report(cache_key: str) -> Optional[RecoveryReport]:
        """Retrieves a report from the cache."""
        if "recovery_engine_cache" not in st.session_state:
            st.session_state.recovery_engine_cache = {}
        
        return st.session_state.recovery_engine_cache.get(cache_key)

    @staticmethod
    def set_report(cache_key: str, report: RecoveryReport) -> None:
        """Saves a report to the cache."""
        if "recovery_engine_cache" not in st.session_state:
            st.session_state.recovery_engine_cache = {}
        
        st.session_state.recovery_engine_cache[cache_key] = report

    @st.cache_data(ttl=3600)
    def get_static_key(branch_name: str, week_start: str) -> str:
        """Generates a stable cache key for a specific branch and time window."""
        return f"{branch_name}_{week_start}"