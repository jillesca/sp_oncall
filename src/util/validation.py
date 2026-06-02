"""Structured output validation with retry-on-violation for LLM parsing.

Provides a generic validation gate that parses LLM output into a schema,
runs validators, and retries with feedback when violations are found.
Never raises — always returns a best-effort result.
"""

from typing import Any, Callable, List, Optional, Tuple

from langchain_core.language_models import BaseChatModel

from src.logging import get_logger

logger = get_logger(__name__)


def validate_structured_output(
    raw_text: Any,
    schema: type,
    model: BaseChatModel,
    validators: List[Callable[[Any], List[str]]],
    max_attempts: int = 2,
) -> Tuple[Optional[Any], List[str]]:
    """Parse raw_text into schema, run validators, retry with feedback on violations.

    Args:
        raw_text: The LLM output to parse (passed directly to model.invoke).
        schema: The dataclass or Pydantic schema to parse into.
        model: The LLM model to use for parsing.
        validators: Callables that take the parsed result and return a list
                    of violation strings (empty list means valid).
        max_attempts: Number of retry attempts after the initial parse.
                      Total attempts = max_attempts + 1.

    Returns:
        Tuple of (parsed_result, violations).
        If parsing succeeds with no violations, violations is empty.
        If all attempts are exhausted, returns (last_result, remaining_violations).
        parsed_result is None only if every attempt raised an exception.
    """
    structured_model = model.with_structured_output(schema=schema)

    current_input = raw_text
    last_result = None
    last_violations: List[str] = []

    for attempt in range(max_attempts + 1):
        try:
            result = structured_model.invoke(input=current_input)
            violations = _run_validators(result, validators)

            if not violations:
                logger.debug("✅ Structured output valid on attempt %d", attempt + 1)
                return result, []

            last_result = result
            last_violations = violations

            if attempt < max_attempts:
                logger.debug(
                    "⚠️ Validation violations on attempt %d, retrying: %s",
                    attempt + 1,
                    violations,
                )
                current_input = _build_retry_prompt(raw_text, violations)
            else:
                logger.warning(
                    "⚠️ Returning best-effort result after %d attempt(s) with violations: %s",
                    max_attempts + 1,
                    last_violations,
                )

        except Exception as e:
            logger.error(
                "❌ Structured output parsing failed on attempt %d: %s",
                attempt + 1,
                e,
            )
            if attempt >= max_attempts:
                return last_result, last_violations

    return last_result, last_violations


def validate_planning_response(result: Any) -> List[str]:
    """Validate a DevicePlan: must have device_name and working_plan_steps."""
    violations = []
    device_name = _get_field(result, "device_name", "")
    steps = _get_field(result, "working_plan_steps", "")

    if not device_name:
        violations.append("device_name is empty")
    if not steps:
        violations.append("working_plan_steps is empty")

    return violations


def validate_investigation_planning(result: Any) -> List[str]:
    """Validate an InvestigationPlanningResponse: devices list is non-empty, all device_names non-empty."""
    violations = []
    devices = _get_field(result, "devices", [])

    if not devices:
        violations.append("devices list is empty")
        return violations

    for device in devices:
        name = _get_field(device, "device_name", "")
        if not name:
            violations.append("device_name is empty for one or more devices")

    return violations


def _run_validators(
    result: Any, validators: List[Callable[[Any], List[str]]]
) -> List[str]:
    """Run all validators and collect violations."""
    violations = []
    for validator in validators:
        violations.extend(validator(result))
    return violations


def _build_retry_prompt(original_input: Any, violations: List[str]) -> str:
    """Build a retry prompt with the original input plus violation feedback."""
    original_text = (
        original_input
        if isinstance(original_input, str)
        else str(original_input)
    )
    violation_list = "\n".join(f"- {v}" for v in violations)
    return (
        f"{original_text}\n\n"
        f"---\n"
        f"The previous response had validation issues:\n"
        f"{violation_list}\n"
        f"Please provide a corrected response that fixes these issues."
    )


def _get_field(obj: Any, field: str, default: Any) -> Any:
    """Get a field from either a dataclass/object or a dictionary."""
    if isinstance(obj, dict):
        return obj.get(field, default)
    return getattr(obj, field, default)
