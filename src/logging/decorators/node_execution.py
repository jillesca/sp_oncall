#!/usr/bin/env python3
"""
This module provides decorators for detailed logging of LangGraph node
execution with comprehensive state tracking and transition monitoring.
"""

import time
from functools import wraps
from typing import Callable, Any

from ..utils.dynamic import get_logger


def log_node_execution(
    node_name: str,
    *,
    include_state_details: bool = True,
    include_performance_metrics: bool = True,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Enhanced decorator for LangGraph node execution logging.

    Creates clear visual boundaries and structured logging following
    OpenTelemetry and Kubernetes best practices for easier debugging.

    Args:
        node_name: Human-readable name of the node
        include_state_details: Whether to log detailed state information
        include_performance_metrics: Whether to include timing and performance data

    Returns:
        Decorated function with enhanced logging
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(state: Any, *args: Any, **kwargs: Any) -> Any:
            logger = get_logger(func.__module__)

            start_time = time.time()

            # Log node entry with clear visual boundary
            _log_node_start(logger, node_name, state, include_state_details)

            try:
                # Execute the actual node function
                result_state = func(state, *args, **kwargs)

                # Calculate execution metrics
                execution_time = time.time() - start_time

                # Log successful completion
                _log_node_success(
                    logger,
                    node_name,
                    result_state,
                    execution_time,
                    include_state_details,
                    include_performance_metrics,
                )

                # Log state changes if any
                if include_state_details:
                    _log_state_changes(logger, node_name, state, result_state)

                return result_state

            except Exception as e:
                execution_time = time.time() - start_time
                _log_node_error(logger, node_name, e, execution_time)
                raise

        return wrapper

    return decorator


def _log_node_start(
    logger,
    node_name: str,
    state: Any,
    include_details: bool,
) -> None:
    """Log node start with clear visual boundary."""
    border = "═" * 80

    # Main entry log with visual boundary
    logger.info(f"╔{border}╗")
    logger.info(
        f"║ 🚀 NODE START: {node_name:<63} ║",
        extra={
            "node_name": node_name,
            "event": "node_start",
        },
    )
    logger.info(f"╚{border}╝")

    if include_details:
        # Context information
        device_name = getattr(state, "device_name", "N/A")
        objective = getattr(state, "objective", "N/A")
        current_retries = getattr(state, "current_retries", 0)

        logger.info(
            f"📋 {node_name} Context:",
            extra={
                "device_name": device_name,
                "objective": (
                    objective[:100] + "..."
                    if len(str(objective)) > 100
                    else objective
                ),
                "retries": current_retries,
            },
        )

        # State summary
        working_plan_steps = getattr(state, "working_plan_steps", [])
        execution_results = getattr(state, "execution_results", [])

        logger.debug(f"   Device: {device_name}")
        logger.debug(f"   Objective: {objective}")
        logger.debug(f"   Retries: {current_retries}")
        logger.debug(
            f"   Working plan steps: {len(working_plan_steps) if working_plan_steps else 0}"
        )
        logger.debug(
            f"   Execution results: {len(execution_results) if execution_results else 0}"
        )


def _log_node_success(
    logger,
    node_name: str,
    result_state: Any,
    execution_time: float,
    include_details: bool,
    include_metrics: bool,
) -> None:
    """Log successful node completion with metrics."""
    border = "═" * 80

    # Performance metrics
    metrics = {}
    if include_metrics:
        metrics = {
            "execution_time_ms": round(execution_time * 1000, 2),
            "execution_time_s": round(execution_time, 3),
        }

    # Main success log with visual boundary
    logger.info(f"╔{border}╗")
    if include_metrics:
        logger.info(
            f"║ ✅ NODE COMPLETE: {node_name:<50} [{execution_time:.3f}s] ║",
            extra={
                "node_name": node_name,
                "event": "node_complete",
                **metrics,
            },
        )
    else:
        logger.info(
            f"║ ✅ NODE COMPLETE: {node_name:<58} ║",
            extra={
                "node_name": node_name,
                "event": "node_complete",
            },
        )
    logger.info(f"╚{border}╝")

    if include_details:
        # Result state summary
        device_name = getattr(result_state, "device_name", "N/A")
        current_retries = getattr(result_state, "current_retries", 0)
        working_plan_steps = getattr(result_state, "working_plan_steps", [])
        execution_results = getattr(result_state, "execution_results", [])
        objective_achieved = getattr(
            result_state, "objective_achieved_assessment", None
        )

        logger.info(
            f"📤 {node_name} Result:",
            extra={
                "device_name": device_name,
                "retries": current_retries,
                "plan_steps_count": (
                    len(working_plan_steps) if working_plan_steps else 0
                ),
                "execution_results_count": (
                    len(execution_results) if execution_results else 0
                ),
                "objective_achieved": objective_achieved,
            },
        )

        logger.debug(f"   Device: {device_name}")
        logger.debug(f"   Retries: {current_retries}")
        logger.debug(
            f"   Working plan steps: {len(working_plan_steps) if working_plan_steps else 0}"
        )
        logger.debug(
            f"   Execution results: {len(execution_results) if execution_results else 0}"
        )
        logger.debug(f"   Objective achieved: {objective_achieved}")


def _log_node_error(
    logger,
    node_name: str,
    error: Exception,
    execution_time: float,
) -> None:
    """Log node execution error with clear boundary."""
    border = "═" * 80

    logger.error(f"╔{border}╗")
    logger.error(
        f"║ ❌ NODE ERROR: {node_name:<55} [{execution_time:.3f}s] ║",
        extra={
            "node_name": node_name,
            "event": "node_error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "execution_time_ms": round(execution_time * 1000, 2),
        },
    )
    logger.error(f"║ Error: {type(error).__name__}: {str(error)[:55]:<55} ║")
    logger.error(f"╚{border}╝")


def _log_state_changes(
    logger, node_name: str, input_state: Any, output_state: Any
) -> None:
    """Log significant state changes during node execution."""
    changes = []

    # Check working plan steps changes
    input_steps = getattr(input_state, "working_plan_steps", [])
    output_steps = getattr(output_state, "working_plan_steps", [])
    if len(input_steps or []) != len(output_steps or []):
        changes.append(
            f"Working plan steps: {len(input_steps or [])} → {len(output_steps or [])}"
        )

    # Check execution results changes
    input_results = getattr(input_state, "execution_results", [])
    output_results = getattr(output_state, "execution_results", [])
    if len(input_results or []) != len(output_results or []):
        changes.append(
            f"Execution results: {len(input_results or [])} → {len(output_results or [])}"
        )

    # Check objective achieved changes
    input_achieved = getattr(
        input_state, "objective_achieved_assessment", None
    )
    output_achieved = getattr(
        output_state, "objective_achieved_assessment", None
    )
    if input_achieved != output_achieved:
        changes.append(
            f"Objective achieved: {input_achieved} → {output_achieved}"
        )

    # Check retries changes
    input_retries = getattr(input_state, "current_retries", 0)
    output_retries = getattr(output_state, "current_retries", 0)
    if input_retries != output_retries:
        changes.append(f"Retries: {input_retries} → {output_retries}")

    # Log changes if any
    if changes:
        logger.info(f"📊 {node_name} State Changes:")
        for change in changes:
            logger.info(f"   {change}")
