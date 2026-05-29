"""
Recovery Narrative AI

Uses Large Language Models to transform deterministic metrics into 
professional narrative insights.
"""

from typing import Dict, Any
from .schema import RecoveryMetrics

class NarrativeGenerator:
    """Interface for AI model interaction for report narrativization."""

    def __init__(self, provider: str = "gemini"):
        self.provider = provider

    def generate(self, metrics: RecoveryMetrics) -> str:
        """
        Generates a professional narrative based on the provided metrics.
        Does not perform calculations; only interpretation.
        """
        return ""