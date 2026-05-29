"""
Recovery Engine Schemas

Strict structured data models for recovery intelligence reporting.
Uses dataclasses for type safety and serialization.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class RecoveryOfficerRisk:
    """Individual performance metrics and risk status for a loan officer."""
    name: str = "Unknown"
    arrears: float = 0.0
    recovery_rate: float = 0.0
    dpd_avg: float = 0.0
    status: str = "Stable"

@dataclass
class RecoveryAccount:
    """Individual high-risk account details requiring urgent attention."""
    account_id: str = "N/A"
    client_name: str = "Unknown"
    arrears: float = 0.0
    days_past_due: int = 0
    action_priority: str = "Normal"

@dataclass
class RecoveryTrend:
    """Deterministic movement analysis compared to previous snapshots."""
    direction: str = "Stable"
    movement_amount: float = 0.0
    percentage_change: float = 0.0
    status_label: str = "No Change"

@dataclass
class RecoverySummary:
    """Aggregated high-level portfolio metrics for a branch."""
    total_arrears: float = 0.0
    par_percentage: float = 0.0
    account_count: int = 0
    avg_days_past_due: float = 0.0

@dataclass
class RecoveryReport:
    """
    Main container for the Weekly Recovery Intelligence Report.
    Designed for full JSON serializability and UI crash protection.
    """
    branch_name: str = "Unknown Branch"
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    reporting_week: str = "N/A"
    portfolio_summary: RecoverySummary = field(default_factory=RecoverySummary)
    officer_risks: List[RecoveryOfficerRisk] = field(default_factory=list)
    critical_accounts: List[RecoveryAccount] = field(default_factory=list)
    trend_analysis: RecoveryTrend = field(default_factory=RecoveryTrend)
    operational_alerts: List[str] = field(default_factory=list)
    recovery_actions: List[str] = field(default_factory=list)
    whatsapp_summary: str = "No summary generated."
    metadata: Dict[str, Any] = field(default_factory=dict)
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Converts the report and all nested dataclasses to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecoveryReport":
        """
        Safely reconstructs a RecoveryReport from a dictionary.
        Implements defensive mapping to prevent UI crashes on missing keys.
        """
        if not isinstance(data, dict):
            return cls()

        def _safe_init(datacls, d):
            if not isinstance(d, dict): return {}
            valid_keys = datacls.__dataclass_fields__.keys()
            return {k: v for k, v in d.items() if k in valid_keys}

        summary_raw = data.get("portfolio_summary", {})
        summary = RecoverySummary(**_safe_init(RecoverySummary, summary_raw))

        trend_raw = data.get("trend_analysis", {})
        trend = RecoveryTrend(**_safe_init(RecoveryTrend, trend_raw))

        return cls(
            branch_name=data.get("branch_name", "Unknown Branch"),
            generated_at=data.get("generated_at", datetime.now().isoformat()),
            reporting_week=data.get("reporting_week", "N/A"),
            portfolio_summary=summary,
            officer_risks=[
                RecoveryOfficerRisk(**_safe_init(RecoveryOfficerRisk, off)) 
                for off in data.get("officer_risks", []) if isinstance(off, dict)
            ],
            critical_accounts=[
                RecoveryAccount(**_safe_init(RecoveryAccount, acc)) 
                for acc in data.get("critical_accounts", []) if isinstance(acc, dict)
            ],
            trend_analysis=trend,
            operational_alerts=data.get("operational_alerts", []) 
                if isinstance(data.get("operational_alerts"), list) else [],
            recovery_actions=data.get("recovery_actions", []) 
                if isinstance(data.get("recovery_actions"), list) else [],
            whatsapp_summary=data.get("whatsapp_summary", "No summary generated."),
            metadata=data.get("metadata", {}) 
                if isinstance(data.get("metadata"), dict) else {},
            schema_version=data.get("schema_version", "1.0")
        )