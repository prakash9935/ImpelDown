"""
RBAC Filter Mapper (US-204, US-205, Sprint 3)

Maps user role → Qdrant multi-dimensional filter.
Loads filter definitions from config/rbac_filters.yaml.

Multi-dimensional filters (Sprint 3 upgrade):
  - Admin: {} (no filter, see all including quarantined)
  - Finance: must=[dept ANY (finance|corp|public), quarantine=false, trust_score>=1.0]
  - HR: must=[dept ANY (hr|public), quarantine=false, trust_score>=1.0]
  - Standard: must=[visibility=public, quarantine=false, trust_score>=1.5]

Critical: Filters are injected BEFORE vector search (pre-retrieval),
not after, to prevent unauthorized data leakage (US-204).
"""

import logging
from typing import Any, Dict, Optional

import yaml
from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue, Range

logger = logging.getLogger(__name__)

# Module-level cache for RBAC filters (loaded once at startup)
_RBAC_FILTERS_CACHE: Optional[Dict[str, Filter]] = None


def _build_filter_from_dict(filter_dict: Dict[str, Any]) -> Optional[Filter]:
    """
    Build Qdrant Filter object from YAML dict.

    Supports two formats:
      1. Empty dict {} → None (no filter, see all)
      2. Multi-dimensional must list → Filter(must=[...])

    Args:
        filter_dict: Filter definition from YAML

    Returns:
        Qdrant Filter object or None (for no filtering)

    Raises:
        ValueError: If filter format is invalid
    """
    if not filter_dict:  # Empty dict {} for admin
        return None

    if "must" not in filter_dict:
        raise ValueError(f"Filter must have 'must' key (got: {filter_dict})")

    must_conditions = filter_dict["must"]
    field_conditions = []

    for condition in must_conditions:
        for field_name, condition_value in condition.items():
            # Parse the condition value (any, eq, gte, etc.)
            if "any" in condition_value:
                # Multi-value condition: {"any": [{"eq": "value1"}, {"eq": "value2"}]}
                # Convert to: FieldCondition(key=field_name, match=MatchAny(any=[value1, value2]))
                values = []
                for match_dict in condition_value["any"]:
                    if "eq" in match_dict:
                        values.append(match_dict["eq"])
                field_conditions.append(FieldCondition(key=field_name, match=MatchAny(any=values)))
            elif "eq" in condition_value:
                # Single value: {"eq": value}
                field_conditions.append(
                    FieldCondition(key=field_name, match=MatchValue(value=condition_value["eq"]))
                )
            elif "gte" in condition_value:
                # Range condition: {"gte": value}
                field_conditions.append(
                    FieldCondition(key=field_name, range=Range(gte=condition_value["gte"]))
                )
            else:
                raise ValueError(f"Unknown condition type in {field_name}: {condition_value}")

    return Filter(must=field_conditions) if field_conditions else None


def load_rbac_filters(config_path: str = "config/rbac_filters.yaml") -> Dict[str, Optional[Filter]]:
    """
    Load RBAC role -> Qdrant filter mapping from config file.

    Caches result in module-level variable to avoid repeated file I/O.
    Converts YAML dict format to Qdrant Filter objects.

    Args:
        config_path: Path to rbac_filters.yaml (relative to project root)

    Returns:
        Dict mapping role (str) to Qdrant Filter (or None for no filtering)

    Raises:
        FileNotFoundError: If config file not found
        yaml.YAMLError: If config file is malformed
        ValueError: If filter format is invalid
    """
    global _RBAC_FILTERS_CACHE

    if _RBAC_FILTERS_CACHE is not None:
        logger.debug("Using cached RBAC filters")
        return _RBAC_FILTERS_CACHE

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Extract and build filters: config = {admin: {filter: {}}, finance: {filter: {...}}, ...}
        filters = {}
        for role, role_config in config.items():
            if isinstance(role_config, dict) and "filter" in role_config:
                filter_dict = role_config["filter"]
                try:
                    qdrant_filter = _build_filter_from_dict(filter_dict)
                    filters[role] = qdrant_filter
                    logger.info(f"Loaded filter for role '{role}': {qdrant_filter}")
                except ValueError as e:
                    logger.error(f"Invalid filter for role '{role}': {e}")
                    raise
            else:
                logger.warning(f"Invalid RBAC config for role {role}: missing 'filter' key")

        _RBAC_FILTERS_CACHE = filters
        logger.info(f"Loaded RBAC filters for roles: {list(filters.keys())}")
        return filters

    except FileNotFoundError:
        logger.error(f"RBAC filters config not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse RBAC filters config: {e}")
        raise


def get_filter_for_role(role: str) -> Optional[Filter]:
    """
    Get Qdrant Filter object for a user role.

    **Critical:** This filter is injected BEFORE the vector search query (pre-retrieval),
    not after, to prevent unauthorized data leakage. This is a security-critical function.

    Multi-dimensional filtering enforces three independent checks:
      1. Department/visibility authorization
      2. Quarantine enforcement (filters out untrusted chunks)
      3. Trust score thresholds per role

    Args:
        role: User role (admin, finance, hr, standard)

    Returns:
        Qdrant Filter object (or None for admin = no restrictions)

    Raises:
        ValueError: If role is not recognized
    """
    filters = load_rbac_filters()

    if role not in filters:
        raise ValueError(f"Unknown role: {role}. Valid roles: {list(filters.keys())}")

    qdrant_filter = filters[role]
    logger.debug(f"Returning filter for role '{role}': {qdrant_filter}")
    return qdrant_filter
