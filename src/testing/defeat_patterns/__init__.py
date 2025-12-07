"""
Defeat pattern detectors for specific agent anti-patterns.
"""

from src.testing.defeat_patterns.breaking_code import detect_breaking_working_code
from src.testing.defeat_patterns.context_drift import detect_context_drift
from src.testing.defeat_patterns.over_engineering import detect_over_engineering
from src.testing.defeat_patterns.retry_loop import detect_retry_loop

__all__ = [
    "detect_retry_loop",
    "detect_context_drift",
    "detect_breaking_working_code",
    "detect_over_engineering",
]
