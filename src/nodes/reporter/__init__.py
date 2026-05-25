"""
Investigation Reporter Node.

Generates the final investigation report, persists device facts and history
to the store, and resets working state for the next request.
"""

from .core import investigation_report_node
