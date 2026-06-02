"""Alert-to-skill routing table and lookup helpers."""

from typing import Dict, List

from src.logging import get_logger

logger = get_logger(__name__)

ALERT_SKILL_ROUTING: Dict[str, List[str]] = {
    "interface_state": ["check_interface_status", "general_device_health_check"],
    "bgp_session_state": ["check_bgp_neighbors", "review_pe_device"],
    "isis_adjacency_count": ["check_interface_status", "review_p_device"],
    "topology_degraded": ["check_interface_status", "review_p_device"],
    "interface_flapping": ["check_interface_status"],
    "interface_errors": ["check_interface_status"],
}


def get_skills_for_alert(event_type: str) -> List[str]:
    """Return skill names relevant for the given alert event_type.

    Falls back to all available skills when event_type is not in the routing table.
    """
    skills = ALERT_SKILL_ROUTING.get(event_type)

    if skills is None:
        logger.warning(
            "No routing entry for event_type '%s', falling back to all skills",
            event_type,
        )
        return get_all_skills()

    logger.debug("Routing event_type '%s' to skills: %s", event_type, skills)
    return skills


def get_all_skills() -> List[str]:
    """Return names of all available skills by scanning the skills directory."""
    from src.util.skills import SKILLS_DIR

    if not SKILLS_DIR.is_dir():
        logger.warning("Skills directory not found: %s", SKILLS_DIR)
        return []

    names = sorted(p.stem for p in SKILLS_DIR.glob("*.md"))
    logger.debug("All available skills: %s", names)
    return names
