#!/usr/bin/env python3
"""
Operation tracking decorator.

This module provides decorators for automatic logging of operation
execution with timing and context information.
"""

import functools
import time
from typing import Any, Callable, Optional, Dict

from ..utils.dynamic import get_logger


def log_operation(
    operation_name: Optional[str] = None,
    log_args: bool = True,
    log_result: bool = False,
    log_duration: bool = True,
) -> Callable[[Callable], Callable]:
    """
    Decorator for automatic operation logging with timing.

    Args:
        operation_name: Custom operation name (defaults to function name)
        log_args: Whether to log function arguments
        log_result: Whether to log function result
        log_duration: Whether to log execution duration

    Returns:
        Decorated function with automatic operation logging

    Example:
        @log_operation("device_health_check")
        def check_device_health(device_name: str) -> Dict[str, Any]:
            # Implementation...
            return health_data
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_logger(func.__module__)
            op_name = operation_name or getattr(
                func, "__name__", "unknown_operation"
            )

            # Prepare extra logging context
            extra: Dict[str, Any] = {"operation": op_name}

            # Add arguments if requested
            if log_args and (args or kwargs):
                if args:
                    extra["function_args"] = str(args)
                if kwargs:
                    extra["function_kwargs"] = str(
                        kwargs
                    )  # Log operation start
            logger.debug(f"Starting {op_name}", extra=extra)

            start_time = time.time()
            try:
                result = func(*args, **kwargs)

                # Calculate duration
                if log_duration:
                    duration_ms = (time.time() - start_time) * 1000
                    extra["duration_ms"] = round(duration_ms, 2)

                # Add result if requested
                if log_result:
                    extra["result"] = str(result)

                # Log successful completion
                logger.debug(f"Completed {op_name}", extra=extra)

                return result

            except Exception as e:
                # Calculate duration for error case
                if log_duration:
                    duration_ms = (time.time() - start_time) * 1000
                    extra["duration_ms"] = round(duration_ms, 2)

                extra["error"] = str(e)
                extra["error_type"] = type(e).__name__

                # Log operation failure
                logger.error(f"Failed {op_name}: {e}", extra=extra)

                # Re-raise the exception
                raise

        return wrapper

    return decorator


def log_async_operation(
    operation_name: Optional[str] = None,
    log_args: bool = True,
    log_result: bool = False,
    log_duration: bool = True,
) -> Callable[[Callable], Callable]:
    """
    Decorator for automatic async operation logging with timing.

    Similar to log_operation but for async functions.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_logger(func.__module__)
            op_name = operation_name or getattr(
                func, "__name__", "unknown_async_operation"
            )

            # Prepare extra logging context
            extra: Dict[str, Any] = {"operation": op_name, "async": True}

            # Add arguments if requested
            if log_args and (args or kwargs):
                if args:
                    extra["function_args"] = str(args)
                if kwargs:
                    extra["function_kwargs"] = str(
                        kwargs
                    )  # Log operation start
            logger.debug(f"Starting async {op_name}", extra=extra)

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)

                # Calculate duration
                if log_duration:
                    duration_ms = (time.time() - start_time) * 1000
                    extra["duration_ms"] = round(duration_ms, 2)

                # Add result if requested
                if log_result:
                    extra["result"] = str(result)

                # Log successful completion
                logger.debug(f"Completed async {op_name}", extra=extra)

                return result

            except Exception as e:
                # Calculate duration for error case
                if log_duration:
                    duration_ms = (time.time() - start_time) * 1000
                    extra["duration_ms"] = round(duration_ms, 2)

                extra["error"] = str(e)
                extra["error_type"] = type(e).__name__

                # Log operation failure
                logger.error(f"Failed async {op_name}: {e}", extra=extra)

                # Re-raise the exception
                raise

        return wrapper

    return decorator
