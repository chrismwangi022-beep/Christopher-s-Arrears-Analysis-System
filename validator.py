"""
Recovery Engine Validator

Ensures data integrity before processing and before returning reports.
Includes deterministic validation for numeric consistency and structural repair.
"""

import pandas as pd
import logging
from typing import Tuple, List, Optional, Dict, Any
from .schema import RecoveryReport

# Setup specialized logger for the Recovery Engine
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RecoveryEngine.Validator")

class DataValidator:
    """
    Production-grade validation engine for Weekly Recovery Reports.
    Ensures that deterministic data and AI-generated summaries meet quality thresholds.
    """

    @staticmethod
    def validate_input_df(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Checks if the input dataframe has the required columns for recovery processing."""
        required_columns = ["Branch", "Arrears", "Report_Date"]
        missing = [col for col in required_columns if col not in df.columns]
        
        if missing:
            logger.error(f"Input DataFrame validation failed. Missing: {missing}")
        return (len(missing) == 0, missing)

    @staticmethod
    def validate_report_integrity(report: RecoveryReport) -> bool:
        """
        Lightweight consistency check for RecoveryReport objects.
        Matches the schema defined in schema.py.
        """
        # Ensure total arrears isn't negative and a summary exists
        if report.portfolio_summary.total_arrears < 0:
            return False
        if not report.whatsapp_summary or "No summary" in report.whatsapp_summary:
            return False
        return True

    @staticmethod
    def validate_report(report: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Comprehensive validation of a report dictionary.
        Checks for missing keys, empty sections, and invalid numeric data.
        """
        errors = []
        logger.info(f"Validating recovery report for branch: {report.get('branch_name', 'Unknown')}")

        try:
            # 1. Type Check
            if not isinstance(report, dict):
                return False, ["Report must be a dictionary object"]

            # 2. Key Existence & Null Check
            required_keys = ["branch_name", "portfolio_summary", "trend_analysis", "officer_risks"]
            for key in required_keys:
                if key not in report or report[key] is None:
                    errors.append(f"Critical section missing or null: {key}")
            
            # 3. Critical Section Non-Empty Check
            if "officer_risks" in report and not report["officer_risks"]:
                errors.append("Officer risk data is empty; requires at least one record.")

            # 4. Nested Validations
            if "portfolio_summary" in report:
                errors.extend(DataValidator.validate_metrics(report["portfolio_summary"]))
            
            if "trend_analysis" in report:
                errors.extend(DataValidator.validate_trend_data(report["trend_analysis"]))
                
            if "officer_risks" in report:
                errors.extend(DataValidator.validate_officer_data(report["officer_risks"]))

            # 5. Operational Intelligence Check
            actions = report.get("recovery_actions", [])
            if not isinstance(actions, list) or len(actions) == 0:
                errors.append("Report contains zero operational recovery actions.")

        except Exception as e:
            # Defensive programming: catch-all to prevent app crashes during validation
            msg = f"Unexpected error in validator: {str(e)}"
            logger.error(msg, exc_info=True)
            errors.append(msg)

        is_valid = len(errors) == 0
        return is_valid, errors

    @staticmethod
    def validate_metrics(metrics: Dict[str, Any]) -> List[str]:
        """Validates that summary metrics are present and numeric."""
        errs = []
        if not isinstance(metrics, dict):
            return ["Portfolio summary section is not a dictionary."]

        fields = ["total_arrears", "par_percentage", "account_count", "avg_days_past_due"]
        for field in fields:
            val = metrics.get(field)
            if val is None:
                errs.append(f"Metric '{field}' is missing.")
            elif not isinstance(val, (int, float)):
                errs.append(f"Metric '{field}' must be numeric (found {type(val).__name__}).")
            elif val < 0:
                errs.append(f"Metric '{field}' cannot be negative.")
        return errs

    @staticmethod
    def validate_officer_data(officers: List[Dict[str, Any]]) -> List[str]:
        """Ensures officer data records are properly structured."""
        errs = []
        if not isinstance(officers, list):
            return ["Officer risks must be a list."]
            
        for idx, officer in enumerate(officers):
            if not isinstance(officer, dict):
                errs.append(f"Officer record at index {idx} is not a dictionary.")
                continue
            if "name" not in officer or not officer["name"]:
                errs.append(f"Officer record at index {idx} is missing a name.")
            if not isinstance(officer.get("arrears", 0), (int, float)):
                errs.append(f"Arrears for officer '{officer.get('name', idx)}' must be numeric.")
        return errs

    @staticmethod
    def validate_trend_data(trend: Dict[str, Any]) -> List[str]:
        """Validates the presence of trend movement and direction."""
        errs = []
        if not isinstance(trend, dict):
            return ["Trend analysis section is malformed."]
            
        if "direction" not in trend:
            errs.append("Trend direction field is missing.")
        if not isinstance(trend.get("movement_amount"), (int, float)):
            errs.append("Trend movement amount must be numeric.")
        return errs

    @staticmethod
    def repair_missing_sections(report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatic repair helper.
        Injects safe fallback placeholders for missing or malformed report sections.
        Prevents downstream UI components from crashing on key errors.
        """
        logger.warning(f"Repairing missing sections for: {report.get('branch_name', 'Unknown')}")
        
        if "branch_name" not in report: report["branch_name"] = "Unknown Branch"
        
        # Repair Portfolio Summary
        if "portfolio_summary" not in report or not isinstance(report["portfolio_summary"], dict):
            report["portfolio_summary"] = {
                "total_arrears": 0.0, "par_percentage": 0.0, 
                "account_count": 0, "avg_days_past_due": 0.0
            }
            
        # Repair Trend Analysis
        if "trend_analysis" not in report or not isinstance(report["trend_analysis"], dict):
            report["trend_analysis"] = {
                "direction": "Stable", "movement_amount": 0.0, 
                "percentage_change": 0.0, "status_label": "No Data"
            }
            
        # Repair required lists
        for key in ["officer_risks", "critical_accounts", "recovery_actions"]:
            if key not in report or not isinstance(report[key], list):
                report[key] = []
        
        # Ensure minimum operational intelligence if empty
        if not report["recovery_actions"]:
            report["recovery_actions"] = ["Monitor portfolio for new arrears movement."]
            
        return report