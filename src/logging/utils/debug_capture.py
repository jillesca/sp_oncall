#!/usr/bin/env python3
"""
Debug object capture utilities.

This module provides utilities for capturing complex objects to dedicated
log files for offline analysis and testing. Useful when debuggers truncate
or modify object representations.
"""

import json
import logging
import pprint
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..core.logger_names import LoggerNames


class DebugCapture:
    """
    Utility class for capturing debug objects to dedicated log files.

    This class provides methods to capture objects in various formats
    (JSON, pretty-print, repr) to dedicated debug log files that can
    be easily copied and used for offline testing.
    """

    def __init__(self, debug_dir: Optional[Union[str, Path]] = None):
        """
        Initialize debug capture utility.

        Args:
            debug_dir: Directory for debug files. Defaults to logs/debug/
        """
        if debug_dir is None:
            debug_dir = Path.cwd() / "logs" / "debug"

        self.debug_dir = Path(debug_dir)
        self.debug_dir.mkdir(parents=True, exist_ok=True)

        # Set up dedicated debug logger
        self.logger = logging.getLogger(
            f"{LoggerNames.APP_ROOT}.debug_capture"
        )
        self._setup_debug_logger()

    def _setup_debug_logger(self) -> None:
        """Set up dedicated debug logger with file handler."""
        # Prevent duplicate handlers
        if self.logger.handlers:
            return

        self.logger.setLevel(logging.DEBUG)

        # Create debug log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = self.debug_dir / f"debug_capture_{timestamp}.log"

        # File handler for debug capture
        file_handler = logging.FileHandler(
            debug_file, mode="w", encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)

        # Simple formatter for debug capture
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.propagate = False  # Don't propagate to other loggers

        self.logger.info(
            f"Debug capture session started - log file: {debug_file}"
        )

    def capture_object(
        self,
        obj: Any,
        label: str = "debug_object",
        formats: Optional[list] = None,
    ) -> str:
        """
        Capture an object in multiple formats for offline analysis.

        Args:
            obj: The object to capture
            label: Label for the capture (used in logs and filenames)
            formats: List of formats to capture in ['json', 'pprint', 'repr', 'str']
                    Defaults to ['json', 'pprint', 'repr']

        Returns:
            Path to the main capture file
        """
        if formats is None:
            formats = ["json", "pprint", "repr"]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[
            :-3
        ]  # Include milliseconds
        capture_id = f"{label}_{timestamp}"

        self.logger.info(f"=== CAPTURE START: {capture_id} ===")
        self.logger.info(f"Object type: {type(obj).__name__}")
        self.logger.info(f"Object class: {obj.__class__}")

        capture_file = self.debug_dir / f"{capture_id}.txt"

        with open(capture_file, "w", encoding="utf-8") as f:
            f.write(f"# Debug Capture: {capture_id}\n")
            f.write(f"# Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"# Object Type: {type(obj).__name__}\n")
            f.write(f"# Object Class: {obj.__class__}\n\n")

            for fmt in formats:
                f.write(f"\n{'='*60}\n")
                f.write(f"# FORMAT: {fmt.upper()}\n")
                f.write(f"{'='*60}\n\n")

                try:
                    if fmt == "json":
                        self._capture_json(obj, f)
                    elif fmt == "pprint":
                        self._capture_pprint(obj, f)
                    elif fmt == "repr":
                        self._capture_repr(obj, f)
                    elif fmt == "str":
                        self._capture_str(obj, f)
                    else:
                        f.write(f"Unknown format: {fmt}\n")

                except Exception as e:
                    f.write(f"ERROR capturing in {fmt} format: {e}\n")
                    self.logger.error(
                        f"Failed to capture {capture_id} in {fmt} format: {e}"
                    )

        self.logger.info(f"Object captured to: {capture_file}")
        self.logger.info(f"=== CAPTURE END: {capture_id} ===\n")

        return str(capture_file)

    def _capture_json(self, obj: Any, file_handle) -> None:
        """Capture object as JSON (if serializable)."""
        try:
            # Try to convert to JSON
            json_str = json.dumps(
                obj, indent=2, default=str, ensure_ascii=False
            )
            file_handle.write("# JSON Representation:\n")
            file_handle.write(json_str)
            file_handle.write("\n")
        except (TypeError, ValueError) as e:
            # If not JSON serializable, try to convert to dict first
            file_handle.write(f"# JSON serialization failed: {e}\n")
            try:
                if hasattr(obj, "__dict__"):
                    obj_dict = obj.__dict__
                    json_str = json.dumps(
                        obj_dict, indent=2, default=str, ensure_ascii=False
                    )
                    file_handle.write("# JSON Representation (__dict__):\n")
                    file_handle.write(json_str)
                    file_handle.write("\n")
                else:
                    file_handle.write(
                        "# Object not JSON serializable and has no __dict__\n"
                    )
            except Exception as e2:
                file_handle.write(
                    f"# __dict__ JSON serialization also failed: {e2}\n"
                )

    def _capture_pprint(self, obj: Any, file_handle) -> None:
        """Capture object using pretty print."""
        file_handle.write("# Pretty Print Representation:\n")
        pprint.pprint(obj, stream=file_handle, width=120, depth=None)
        file_handle.write("\n")

    def _capture_repr(self, obj: Any, file_handle) -> None:
        """Capture object using repr()."""
        file_handle.write("# Repr Representation:\n")
        file_handle.write(repr(obj))
        file_handle.write("\n")

    def _capture_str(self, obj: Any, file_handle) -> None:
        """Capture object using str()."""
        file_handle.write("# String Representation:\n")
        file_handle.write(str(obj))
        file_handle.write("\n")

    def capture_with_context(
        self,
        obj: Any,
        context: Dict[str, Any],
        label: str = "debug_with_context",
    ) -> str:
        """
        Capture an object along with contextual information.

        Args:
            obj: The main object to capture
            context: Dictionary of contextual information
            label: Label for the capture

        Returns:
            Path to the capture file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        capture_id = f"{label}_{timestamp}"

        self.logger.info(f"=== CONTEXT CAPTURE START: {capture_id} ===")

        capture_file = self.debug_dir / f"{capture_id}_with_context.txt"

        with open(capture_file, "w", encoding="utf-8") as f:
            f.write(f"# Debug Capture with Context: {capture_id}\n")
            f.write(f"# Timestamp: {datetime.now().isoformat()}\n\n")

            # Capture context first
            f.write("# CONTEXT INFORMATION\n")
            f.write("=" * 60 + "\n")
            for key, value in context.items():
                f.write(f"# {key}: {value}\n")
            f.write("\n")

            # Capture main object
            f.write("# MAIN OBJECT\n")
            f.write("=" * 60 + "\n")
            self._capture_pprint(obj, f)
            f.write("\n")
            self._capture_repr(obj, f)

        self.logger.info(f"Object with context captured to: {capture_file}")
        self.logger.info(f"=== CONTEXT CAPTURE END: {capture_id} ===\n")

        return str(capture_file)


# Global debug capture instance
_debug_capture = None


def get_debug_capture() -> DebugCapture:
    """Get the global debug capture instance."""
    global _debug_capture
    if _debug_capture is None:
        _debug_capture = DebugCapture()
    return _debug_capture


def debug_capture_object(
    obj: Any, label: str = "debug_object", formats: Optional[list] = None
) -> str:
    """
    Convenience function to capture an object for debugging.

    Args:
        obj: Object to capture
        label: Label for the capture
        formats: Formats to capture in

    Returns:
        Path to the capture file
    """
    return get_debug_capture().capture_object(obj, label, formats)


def debug_capture_with_context(
    obj: Any, context: Dict[str, Any], label: str = "debug_with_context"
) -> str:
    """
    Convenience function to capture an object with context.

    Args:
        obj: Main object to capture
        context: Contextual information
        label: Label for the capture

    Returns:
        Path to the capture file
    """
    return get_debug_capture().capture_with_context(obj, context, label)


# Conditional debug capture based on environment variable
def conditional_debug_capture(
    obj: Any,
    label: str = "conditional_debug",
    env_var: str = "SP_ONCALL_DEBUG_CAPTURE",
    formats: Optional[list] = None,
) -> Optional[str]:
    """
    Capture object only if environment variable is set.

    This allows you to enable debug capture only when needed without
    modifying code.

    Args:
        obj: Object to capture
        label: Label for the capture
        env_var: Environment variable to check
        formats: Formats to capture in

    Returns:
        Path to capture file if captured, None otherwise
    """
    import os

    if os.getenv(env_var, "").lower() in ("1", "true", "yes", "on"):
        return debug_capture_object(obj, label, formats)
    return None
