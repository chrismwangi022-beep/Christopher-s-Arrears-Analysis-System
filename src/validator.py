"""Compatibility Shim for Data Validation"""

class DataValidator:
    def validate_report(self, metrics):
        # Returns (passed, errors)
        return True, []
    
    def repair_missing_sections(self, metrics):
        # Return as-is
        return metrics