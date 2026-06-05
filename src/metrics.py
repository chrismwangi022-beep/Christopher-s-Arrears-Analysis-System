"""
Recovery Engine Compatibility Layer
Redirects internal metrics calls to the central calculations engine.
"""

from .calculations import get_standard_metrics_package

def build_recovery_metrics(df_display, df_full, branch_name=None):
    """
    Compatibility wrapper for Recovery Engine v2.
    Maps the modular builder to the strict financial calculation engine.
    """
    return get_standard_metrics_package(df_display, df_full)