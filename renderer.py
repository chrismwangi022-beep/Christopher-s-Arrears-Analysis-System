"""
Recovery Report Renderer

Formatting logic for different output channels (Streamlit UI, WhatsApp, PDF).
"""

from typing import Dict, Any, List
from .schema import RecoveryReport

class ReportRenderer:
    """Converts RecoveryReport objects into user-facing formats."""

    @staticmethod
    def to_markdown(report: RecoveryReport) -> str:
        """Renders report as Markdown for Streamlit display."""
        return f"# Recovery Report: {report.metrics.branch_name}\n\n{report.narrative_text}"

    @staticmethod
    def to_whatsapp(report: RecoveryReport) -> str:
        """Renders report as a compact text block for mobile messaging."""
        return report.narrative_text

    @staticmethod
    def render_weekly_report(report: Dict[str, Any]) -> str:
        """
        Main entry point for rendering the structured report into Markdown.
        Guarantees all sections are present via defensive fallbacks.
        """
        if not isinstance(report, dict):
            return "### ❌ Error: Invalid report data format."

        # Initialize markdown list
        md = []

        # 1. Executive Summary
        branch = report.get("branch_name", "Unknown Branch")
        timestamp = report.get("generated_at", "N/A")
        md.append(f"# 📋 Weekly Recovery Intelligence: {branch}")
        md.append(f"**Report Generated:** `{timestamp}`")
        md.append("---")

        # 2. Portfolio Metrics
        md.append("## 📊 Portfolio Metrics")
        metrics = report.get("portfolio_summary", {})
        if isinstance(metrics, dict):
            md.append(f"- **Total Arrears:** KSh {metrics.get('total_arrears', 0):,.2f}")
            md.append(f"- **PAR %:** {metrics.get('par_percentage', 0):.2f}%")
            md.append(f"- **Account Count:** {metrics.get('account_count', 0)}")
            md.append(f"- **Avg DPD:** {metrics.get('avg_days_past_due', 0):.1f} days")
        else:
            md.append("_Metrics data unavailable._")
        md.append("")

        # 3. Trend Analysis
        md.append("## 📈 Trend Analysis")
        trend = report.get("trend_analysis", {})
        if isinstance(trend, dict):
            direction = trend.get("direction", "Stable")
            amount = trend.get("movement_amount", 0.0)
            pct = trend.get("percentage_change", 0.0)
            status = trend.get("status_label", "N/A")
            
            # Emoji-based visual indicator
            arrow = "🔺" if amount > 0 else ("🔻" if amount < 0 else "↔️")
            md.append(f"**Status:** {status} ({direction} {arrow})")
            md.append(f"- **Movement:** KSh {amount:,.2f} ({pct:+.2f}%)")
        else:
            md.append("_Trend analysis data unavailable._")
        md.append("")

        # 4. Officer Intelligence
        md.append("## 👤 Officer Intelligence")
        officers = report.get("officer_risks", [])
        if isinstance(officers, list) and officers:
            md.append("| Officer | Arrears | Rec. Rate | Avg DPD | Status |")
            md.append("| :--- | :--- | :--- | :--- | :--- |")
            for off in officers:
                name = off.get("name", "Unknown")
                arr = off.get("arrears", 0.0)
                rate = off.get("recovery_rate", 0.0)
                dpd = off.get("dpd_avg", 0.0)
                stat = off.get("status", "N/A")
                md.append(f"| {name} | {arr:,.0f} | {rate:.1f}% | {dpd:.1f} | {stat} |")
        else:
            md.append("_No officer data identified._")
        md.append("")

        # 5. Critical Accounts
        md.append("## 🚨 Critical Accounts")
        accounts = report.get("critical_accounts", [])
        if isinstance(accounts, list) and accounts:
            md.append("| ID | Client | Arrears | DPD | Priority |")
            md.append("| :--- | :--- | :--- | :--- | :--- |")
            for acc in accounts:
                aid = acc.get("account_id", "N/A")
                client = acc.get("client_name", "N/A")
                arr = acc.get("arrears", 0.0)
                dpd = acc.get("days_past_due", 0)
                pri = acc.get("action_priority", "Normal")
                md.append(f"| {aid} | {client} | {arr:,.0f} | {dpd} | {pri} |")
        else:
            md.append("_No critical accounts requiring escalation._")
        md.append("")

        # 6. Operational Alerts
        md.append("## 🔔 Operational Alerts")
        alerts = report.get("operational_alerts", [])
        if isinstance(alerts, list) and alerts:
            for alert in alerts:
                md.append(f"- ⚠️ {alert}")
        else:
            md.append("_No high-priority alerts identified._")
        md.append("")

        # 7. Recovery Priorities
        md.append("## 🛠️ Recovery Priorities")
        actions = report.get("recovery_actions", [])
        if isinstance(actions, list) and actions:
            for idx, action in enumerate(actions, 1):
                md.append(f"{idx}. **{action}**")
        else:
            md.append("_No specific recovery actions defined._")
        md.append("")

        # 8. WhatsApp Communication
        md.append("## 📲 WhatsApp Communication")
        summary = report.get("whatsapp_summary", "No summary text generated.")
        md.append("```text")
        md.append(summary)
        md.append("```")

        return "\n".join(md)

    def render_radar_ui(self, report: RecoveryReport) -> None:
        """Renders the visual Radar UI components using Streamlit primitives."""
        pass