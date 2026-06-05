"""Compatibility Shim for Report Rendering"""

class ReportRenderer:
    def render_weekly_report(self, report_dict):
        """Basic markdown conversion for the reporting UI."""
        branch = report_dict.get('branch_name', 'Branch')
        return f"### 📡 Weekly Recovery Report: {branch}\n\nStrategic intelligence generated successfully."