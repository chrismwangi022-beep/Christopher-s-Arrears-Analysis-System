"""Compatibility Shim for Narrative AI"""

from .ai_engine import generate_ai_insights

class NarrativeGenerator:
    def generate(self, metrics):
        """Routes to the central AI engine for narrative generation."""
        # metrics is the raw_metrics dict prepared by the builder
        results = generate_ai_insights(metrics)
        return results.get("executive_summary", "Recovery intelligence summary is pending...")