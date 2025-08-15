#!/usr/bin/env python3
"""
Node execution tracking decorator.

This module provides decorators for detailed logging of LangGraph node
execution with comprehensive state tracking and transition monitoring.
"""

from functools import wraps
from typing import Callable, Any

from ..utils.dynamic import get_logger


def log_node_execution(
    node_name: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to add detailed entry/exit logging for graph nodes.

    This decorator provides comprehensive logging for LangGraph node execution,
    including state transitions, execution results, and detailed debugging
    information for node state changes.

    Args:
        node_name: Human-readable name of the node for logging

    Returns:
        Decorated function with detailed node execution logging

    Example:
        @log_node_execution("Input Validator")
        def enhanced_input_validator_node(state: GraphState) -> GraphState:
            return input_validator_node(state)
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(state: Any, *args: Any, **kwargs: Any) -> Any:
            logger = get_logger(func.__module__)

            # Log node entry with current state
            logger.info("🔵 Entering node: %s", node_name)
            logger.debug("📥 %s - Input state summary:", node_name)
            logger.debug("  Device: %s", getattr(state, "device_name", "N/A"))
            logger.debug("  Objective: %s", getattr(state, "objective", "N/A"))
            logger.debug(
                "  Retries: %s", getattr(state, "current_retries", "N/A")
            )

            working_plan_steps = getattr(state, "working_plan_steps", None)
            logger.debug(
                f"  Working plan steps: {len(working_plan_steps) if working_plan_steps else 0}"
            )

            execution_results = getattr(state, "execution_results", [])
            logger.debug("  Execution results: %s", len(execution_results))

            objective_achieved = getattr(
                state, "objective_achieved_assessment", None
            )
            logger.debug("  Objective achieved: %s", objective_achieved)

            # Log detailed input state data
            logger.debug("📋 %s - Detailed input state:", node_name)
            if working_plan_steps:
                logger.debug("  Working plan steps content:")
                for i, step in enumerate(working_plan_steps, 1):
                    logger.debug("    Step %s: %s", i, step)
            else:
                logger.debug("  Working plan steps: None")

            if execution_results:
                logger.debug("  Execution results content:")
                for i, result in enumerate(execution_results, 1):
                    investigation_report = getattr(
                        result, "investigation_report", ""
                    )
                    executed_calls = getattr(result, "executed_calls", [])
                    logger.debug(
                        "    Result %s: investigation_report=%s chars, executed_calls=%s calls",
                        i,
                        len(investigation_report),
                        len(executed_calls),
                    )
                    if executed_calls:
                        for j, call in enumerate(executed_calls, 1):
                            logger.debug("      Call %s: %s", j, call)
            else:
                logger.debug("  Execution results: None")

            assessor_feedback = getattr(
                state, "assessor_feedback_for_retry", None
            )
            if assessor_feedback:
                logger.debug("  Assessor feedback: %s", assessor_feedback)

            try:
                # Execute the actual node function
                result_state = func(state, *args, **kwargs)

                # Log node exit with result state
                logger.info("🟢 Exiting node: %s - Success", node_name)
                logger.debug("📤 %s - Output state summary:", node_name)
                logger.debug(
                    "  Device: %s", getattr(result_state, "device_name", "N/A")
                )
                logger.debug(
                    "  Objective: %s",
                    getattr(result_state, "objective", "N/A"),
                )
                logger.debug(
                    "  Retries: %s",
                    getattr(result_state, "current_retries", "N/A"),
                )

                result_working_plan_steps = getattr(
                    result_state, "working_plan_steps", None
                )
                logger.debug(
                    f"  Working plan steps: {len(result_working_plan_steps) if result_working_plan_steps else 0}"
                )

                result_execution_results = getattr(
                    result_state, "execution_results", []
                )
                logger.debug(
                    f"  Execution results: {len(result_execution_results)}"
                )

                result_objective_achieved = getattr(
                    result_state, "objective_achieved_assessment", None
                )
                logger.debug(
                    f"  Objective achieved: {result_objective_achieved}"
                )

                # Log detailed output state data
                logger.debug("📋 %s - Detailed output state:", node_name)
                if result_working_plan_steps:
                    logger.debug("  Working plan steps content:")
                    for i, step in enumerate(result_working_plan_steps, 1):
                        logger.debug("    Step %s: %s", i, step)
                else:
                    logger.debug("  Working plan steps: None")

                if result_execution_results:
                    logger.debug("  Execution results content:")
                    for i, result in enumerate(result_execution_results, 1):
                        investigation_report = getattr(
                            result, "investigation_report", ""
                        )
                        executed_calls = getattr(result, "executed_calls", [])
                        logger.debug(
                            "    Result %s: investigation_report=%s chars, executed_calls=%s calls",
                            i,
                            len(investigation_report),
                            len(executed_calls),
                        )
                        if executed_calls:
                            for j, call in enumerate(executed_calls, 1):
                                logger.debug("      Call %s: %s", j, call)

                        tools_limitations = getattr(
                            result, "tools_limitations", None
                        )
                        if tools_limitations:
                            logger.debug(
                                "      Limitations: %s", tools_limitations
                            )
                else:
                    logger.debug("  Execution results: None")

                result_assessor_feedback = getattr(
                    result_state, "assessor_feedback_for_retry", None
                )
                if result_assessor_feedback:
                    logger.debug(
                        f"  Assessor feedback: {result_assessor_feedback}"
                    )

                # Log state changes with detailed comparison
                if len(result_execution_results) != len(execution_results):
                    logger.info(
                        f"📊 {node_name} - EXECUTION RESULTS CHANGED: {len(execution_results)} → {len(result_execution_results)}"
                    )

                    # Log new execution results in detail
                    if len(result_execution_results) > len(execution_results):
                        new_results = result_execution_results[
                            len(execution_results) :
                        ]
                        for i, new_result in enumerate(
                            new_results, len(execution_results) + 1
                        ):
                            investigation_report = getattr(
                                new_result, "investigation_report", ""
                            )
                            executed_calls = getattr(
                                new_result, "executed_calls", []
                            )
                            logger.debug("📊 New execution result %s:", i)
                            logger.debug(
                                "    Investigation report (%s chars): %s...",
                                len(investigation_report),
                                investigation_report[:200],
                            )
                            logger.debug(
                                "    Executed calls (%s): %s",
                                len(executed_calls),
                                executed_calls,
                            )

                            tools_limitations = getattr(
                                new_result, "tools_limitations", None
                            )
                            if tools_limitations:
                                logger.debug(
                                    "    Tools limitations: %s",
                                    tools_limitations,
                                )

                if result_working_plan_steps != working_plan_steps:
                    logger.info("📊 %s - WORKING PLAN CHANGED", node_name)
                    logger.debug("    Before: %s", working_plan_steps)
                    logger.debug("    After: %s", result_working_plan_steps)

                if result_objective_achieved != objective_achieved:
                    logger.info(
                        f"📊 {node_name} - OBJECTIVE ACHIEVED CHANGED: {objective_achieved} → {result_objective_achieved}"
                    )

                result_current_retries = getattr(
                    result_state, "current_retries", None
                )
                current_retries = getattr(state, "current_retries", None)
                if result_current_retries != current_retries:
                    logger.info(
                        "📊 %s - RETRIES CHANGED: %s → %s",
                        node_name,
                        current_retries,
                        result_current_retries,
                    )

                return result_state

            except Exception as e:
                logger.error("🔴 Exiting node: %s - Error: %s", node_name, e)
                logger.error(
                    f"❌ {node_name} - Exception type: {type(e).__name__}"
                )
                raise

        return wrapper

    return decorator
