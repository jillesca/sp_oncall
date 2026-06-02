#!/usr/bin/env python3
"""
Decorators for detailed logging of LangGraph node execution with state
tracking and transition monitoring.
"""

import asyncio
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

    Works with both sync and async node functions. Detects the function type
    at decoration time and wraps it with the appropriate sync or async wrapper.

    Args:
        node_name: Human-readable name of the node
        include_state_details: Whether to log detailed state information
        include_performance_metrics: Whether to include timing and performance data

    Returns:
        Decorated function with enhanced logging
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(state: Any, *args: Any, **kwargs: Any) -> Any:
                logger = get_logger(func.__module__)
                start_time = time.time()

                _log_node_start(logger, node_name, state, include_state_details)

                try:
                    result_state = await func(state, *args, **kwargs)
                    execution_time = time.time() - start_time
                    _log_node_success(
                        logger,
                        node_name,
                        result_state,
                        execution_time,
                        include_state_details,
                        include_performance_metrics,
                    )
                    if include_state_details:
                        _log_state_changes(logger, node_name, state, result_state)
                    return result_state

                except Exception as e:
                    execution_time = time.time() - start_time
                    _log_node_error(logger, node_name, e, execution_time)
                    raise

            return async_wrapper

        @wraps(func)
        def sync_wrapper(state: Any, *args: Any, **kwargs: Any) -> Any:
            logger = get_logger(func.__module__)
            start_time = time.time()

            _log_node_start(logger, node_name, state, include_state_details)

            try:
                result_state = func(state, *args, **kwargs)
                execution_time = time.time() - start_time
                _log_node_success(
                    logger,
                    node_name,
                    result_state,
                    execution_time,
                    include_state_details,
                    include_performance_metrics,
                )
                if include_state_details:
                    _log_state_changes(logger, node_name, state, result_state)
                return result_state

            except Exception as e:
                execution_time = time.time() - start_time
                _log_node_error(logger, node_name, e, execution_time)
                raise

        return sync_wrapper

    return decorator


def _log_node_start(
    logger,
    node_name: str,
    state: Any,
    include_details: bool,
) -> None:
    """Log node start with clear visual boundary."""
    border = "═" * 80

    logger.info("╔%s╗", border)
    logger.info(
        "║ 🚀 NODE START: %-63s ║",
        node_name,
        extra={"node_name": node_name, "event": "node_start"},
    )
    logger.info("╚%s╝", border)

    if include_details:
        primary_count = len(getattr(state, "primary_investigations", []) or [])
        context_count = len(getattr(state, "context_investigations", []) or [])
        event_type = getattr(state, "event_type", None)

        logger.info(
            "📋 %s Context: primary_investigations=%s, context_investigations=%s, event_type=%s",
            node_name,
            primary_count,
            context_count,
            event_type,
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

    logger.info("╔%s╗", border)
    if include_metrics:
        logger.info(
            "║ ✅ NODE COMPLETE: %-50s [%.3fs] ║",
            node_name,
            execution_time,
            extra={
                "node_name": node_name,
                "event": "node_complete",
                "execution_time_ms": round(execution_time * 1000, 2),
                "execution_time_s": round(execution_time, 3),
            },
        )
    else:
        logger.info(
            "║ ✅ NODE COMPLETE: %-58s ║",
            node_name,
            extra={"node_name": node_name, "event": "node_complete"},
        )
    logger.info("╚%s╝", border)

    if include_details:
        primary_count = len(
            getattr(result_state, "completed_primary_investigations", []) or []
        )
        context_device_count = len(
            getattr(result_state, "context_device_names", []) or []
        )
        root_cause_set = bool(getattr(result_state, "root_cause", None))

        logger.info(
            "📤 %s Result: completed_primary=%s, context_devices=%s, root_cause_set=%s",
            node_name,
            primary_count,
            context_device_count,
            root_cause_set,
            extra={
                "node_name": node_name,
                "completed_primary_count": primary_count,
                "context_device_count": context_device_count,
                "root_cause_set": root_cause_set,
            },
        )


def _log_node_error(
    logger,
    node_name: str,
    error: Exception,
    execution_time: float,
) -> None:
    """Log node execution error with clear boundary."""
    border = "═" * 80

    logger.error("╔%s╗", border)
    logger.error(
        "║ ❌ NODE ERROR: %-55s [%.3fs] ║",
        node_name,
        execution_time,
        extra={
            "node_name": node_name,
            "event": "node_error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "execution_time_ms": round(execution_time * 1000, 2),
        },
    )
    logger.error("║ Error: %s: %-55s ║", type(error).__name__, str(error)[:55])
    logger.error("╚%s╝", border)


def _log_state_changes(
    logger, node_name: str, input_state: Any, output_state: Any
) -> None:
    """Log significant GraphState changes during node execution."""
    changes = []

    _check_list_change(
        changes,
        "primary_investigations",
        getattr(input_state, "primary_investigations", []),
        getattr(output_state, "primary_investigations", []),
    )

    _check_list_change(
        changes,
        "context_investigations",
        getattr(input_state, "context_investigations", []),
        getattr(output_state, "context_investigations", []),
    )

    _check_list_change(
        changes,
        "completed_primary_investigations",
        getattr(input_state, "completed_primary_investigations", []),
        getattr(output_state, "completed_primary_investigations", []),
    )

    _check_list_change(
        changes,
        "context_device_names",
        getattr(input_state, "context_device_names", []),
        getattr(output_state, "context_device_names", []),
    )

    input_root_cause = getattr(input_state, "root_cause", None)
    output_root_cause = getattr(output_state, "root_cause", None)
    if bool(input_root_cause) != bool(output_root_cause):
        changes.append("root_cause: %s → %s" % (bool(input_root_cause), bool(output_root_cause)))

    if changes:
        logger.info("📊 %s State Changes:", node_name)
        for change in changes:
            logger.info("   %s", change)


def _check_list_change(changes: list, field: str, before: Any, after: Any) -> None:
    """Append a change entry when the length of a list field differs."""
    before_len = len(before or [])
    after_len = len(after or [])
    if before_len != after_len:
        changes.append("%s: %s → %s" % (field, before_len, after_len))
