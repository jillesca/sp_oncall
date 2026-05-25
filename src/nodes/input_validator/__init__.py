"""
Input Validator Node.

Orchestrates the multi-device investigation setup workflow by extracting
device information, splitting devices into primary (alert targets) and
context (neighbor health checks), and creating Investigation objects.
"""

from .core import input_validator_node
