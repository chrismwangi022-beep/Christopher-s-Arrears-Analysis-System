"""
Recovery Engine Orchestrator (Builder)

The main entry point that coordinates metrics calculation, 
validation, and narrative generation.
"""

import pandas as pd
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from .schema import RecoveryReport, RecoverySummary
from .metrics import build_recovery_metrics
from .validator import DataValidator
from .narrative_ai import NarrativeGenerator
from .cache import RecoveryCache
from .renderer import ReportRenderer

logger = logging.getLogger("RecoveryEngine.Builder")

class RecoveryEngineBuilder:
    """
    Orchestrates the lifecycle of a recovery intelligence report.
    Handles the transformation from raw data to validated, AI-enhanced insights.
    """

    def __init__(self):
        """Initializes the engine components."""
        self.validator = DataValidator()
        self.ai_engine = NarrativeGenerator()
        self.cache = RecoveryCache()
        self.renderer = ReportRenderer()

    def build_weekly_recovery_report(
        self, 
        branch_name: str, 
        df_branch: pd.DataFrame, 
        full_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Executes the master pipeline for generating a Weekly Recovery Intelligence Report.
        
        Pipeline Steps:
        1. STEP 1 → Deterministic metrics generation (AI-free)
        2. STEP 2 → Structural and numeric validation
        3. STEP 3 → AI narrative enhancement (with deterministic fallback)
        4. STEP 4 → Schema-compliant report assembly
        5. STEP 5 → Markdown rendering

        Args:
            branch_name: Name of the branch to analyze.
            df_branch: Filtered dataframe for the specific branch.
            full_df: The complete dataset for historical context.

        Returns:
            A dictionary containing the structured report, rendered output, 
            validation logs, and processing metadata.
        """
        start_perf = time.perf_counter()
        ai_status = "Skipped"
        validation_passed = False
        errors = []

        try:
            # --- STEP 1: Deterministic Metrics ---
            # Generate core data points without AI intervention
            raw_metrics = build_recovery_metrics(df_branch, full_df, branch_name)

            # --- STEP 2: Validation & Repair ---
            # Ensure no critical sections are missing or mathematically invalid
            validation_passed, errors = self.validator.validate_report(raw_metrics)
            if not validation_passed:
                logger.warning(f"Validation failed for {branch_name}. Attempting repair.")
                raw_metrics = self.validator.repair_missing_sections(raw_metrics)

            # --- STEP 3: AI Narrative Enhancement ---
            # Attempt to generate a professional summary using the AI engine
            try:
                # AI is only used for interpretation, not for calculating values
                narrative = self.ai_engine.generate(raw_metrics)
                if not narrative or len(narrative.strip()) < 10:
                    raise ValueError("AI generated an insufficient narrative.")
                
                raw_metrics["whatsapp_summary"] = narrative
                ai_status = "Success"
            except Exception as ai_err:
                logger.error(f"AI Narrative failed: {ai_err}. Using deterministic fallback.")
                # Fallback: Construct a basic narrative from deterministic flags
                trend_status = raw_metrics.get("trend_analysis", {}).get("status_label", "Stable")
                raw_metrics["whatsapp_summary"] = (
                    f"Weekly Recovery Update for {branch_name}: "
                    f"Portfolio is currently {trend_status}. "
                    f"Immediate review of critical accounts is recommended."
                )
                ai_status = "Fallback"

            # --- STEP 4: Report Assembly ---
            # Map the dictionary to a strict schema-validated object
            report_obj = RecoveryReport.from_dict(raw_metrics)
            structured_report = report_obj.to_dict()

            # --- STEP 5: Rendering ---
            # Convert structured data into Streamlit-friendly Markdown
            rendered_markdown = self.renderer.render_weekly_report(structured_report)

        except Exception as catastrophic_err:
            logger.error(f"Catastrophic report failure: {catastrophic_err}", exc_info=True)
            # Return a safety-first empty report structure to prevent UI crashes
            structured_report = RecoveryReport(branch_name=branch_name).to_dict()
            rendered_markdown = "### ❌ Critical Error\nSystem failed to generate report logic."
            errors.append(str(catastrophic_err))
            ai_status = "Failed"

        duration = time.perf_counter() - start_perf

        return {
            "structured_report": structured_report,
            "rendered_report": rendered_markdown,
            "validation_errors": errors,
            "metadata": {
                "generation_time": datetime.now().isoformat(),
                "processing_duration_seconds": round(duration, 4),
                "ai_status": ai_status,
                "validation_status": validation_passed,
                "engine_version": "2.0.0-PROD"
            }
        }

    def build_report(self, branch_name: str, force_refresh: bool = False) -> Optional[RecoveryReport]:
        """Scaffold method for external calls (Legacy compatibility)."""
        # This can be mapped to build_weekly_recovery_report or kept as a stub
        # for the UI to call build_weekly_recovery_report directly.
        return None