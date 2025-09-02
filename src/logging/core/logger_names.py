#!/usr/bin/env python3
"""
Standard logger names for sp_oncall application.

This module defines the hierarchical logger naming convention following
OpenTelemetry best practices. All logger names are centralized here to
ensure consistency and prevent typos.

The naming follows the pattern: sp_oncall.<component>.<subcomponent>
This allows for easy filtering and hierarchical log level control.
"""


class LoggerNames:
    """
    Standard logger names for the application following OTel conventions.

    Provides a centralized registry of all logger names used throughout
    the application, ensuring consistency and enabling hierarchical
    log level control.
    """

    # Root application logger
    APP_ROOT = "sp_oncall"

    # Core application components
    GRAPH = f"{APP_ROOT}.graph"
    CONFIGURATION = f"{APP_ROOT}.configuration"
    MCP_CLIENT = f"{APP_ROOT}.mcp_client"

    # Node components
    NODES = f"{APP_ROOT}.nodes"
    INPUT_VALIDATOR = f"{NODES}.input_validator"
    PLANNER = f"{NODES}.planner"
    EXECUTOR = f"{NODES}.executor"
    ASSESSOR = f"{NODES}.assessor"
    REPORTER = f"{NODES}.reporter"

    # Utilities
    UTILS = f"{APP_ROOT}.utils"
    LLM = f"{UTILS}.llm"
    FILE_LOADER = f"{UTILS}.file_loader"
    PLANS = f"{UTILS}.plans"

    # Prompts
    PROMPTS = f"{APP_ROOT}.prompts"
    INVESTIGATION_PLANNING = f"{PROMPTS}.investigation_planning"
    NETWORK_EXECUTOR = f"{PROMPTS}.network_executor"
    OBJECTIVE_ASSESSOR = f"{PROMPTS}.objective_assessor"
    PLANNER_PROMPT = f"{PROMPTS}.planner"
    REPORT_GENERATOR = f"{PROMPTS}.report_generator"

    # Schemas
    SCHEMAS = f"{APP_ROOT}.schemas"
    STATE = f"{SCHEMAS}.state"
    ASSESSMENT = f"{SCHEMAS}.assessment_schema"
    INVESTIGATION_PLANNING_SCHEMA = f"{SCHEMAS}.investigation_planning_schema"
    PLANNER_SCHEMA = f"{SCHEMAS}.planner_schema"

    @classmethod
    def get_all_loggers(cls) -> list[str]:
        """Get all defined logger names."""
        return [
            value
            for key, value in cls.__dict__.items()
            if isinstance(value, str) and not key.startswith("_")
        ]

    @classmethod
    def is_valid_logger_name(cls, name: str) -> bool:
        """Check if a logger name is valid (starts with app root)."""
        return name.startswith(cls.APP_ROOT)
