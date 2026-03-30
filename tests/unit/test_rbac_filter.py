"""
Unit tests for RBAC filter mapping (US-204, US-205, Sprint 3).

Tests multi-dimensional filter enforcement:
  - Filter loading from config/rbac_filters.yaml
  - Qdrant Filter object construction (must conditions)
  - Multi-dimensional filtering: dept/visibility AND quarantine AND trust_score
  - Security: filters injected pre-retrieval, not post
"""

import pytest
from qdrant_client.models import Filter, FieldCondition
from src.secrag.retrieval.rbac_filter import load_rbac_filters, get_filter_for_role


class TestRBACFilterLoading:
    """Test US-205: Filter loading from YAML config."""

    def test_load_rbac_filters_from_config(self):
        """Test loading RBAC filters from YAML config (US-205)."""
        filters = load_rbac_filters("config/rbac_filters.yaml")

        # Verify all expected roles are present
        assert "admin" in filters
        assert "finance" in filters
        assert "hr" in filters
        assert "standard" in filters


class TestRBACFilterCorrectness:
    """Test US-204: Multi-dimensional filter correctness for each role."""

    def test_admin_filter_unrestricted(self):
        """Test admin role has None filter (no restriction, sees all including quarantined)."""
        admin_filter = get_filter_for_role("admin")

        # Admin should have None filter (no restrictions)
        assert admin_filter is None

    def test_finance_role_filter_multi_dimensional(self):
        """Test finance role enforces three conditions: dept, quarantine, trust_score."""
        finance_filter = get_filter_for_role("finance")

        # Filter should be a Filter object with must conditions
        assert isinstance(finance_filter, Filter)
        assert finance_filter.must is not None
        assert len(finance_filter.must) == 3  # dept, quarantine, trust_score

        # Extract field conditions by field name
        field_names = {cond.key for cond in finance_filter.must}
        assert field_names == {"dept", "quarantine", "trust_score"}

        # Verify dept condition allows finance+corp+public
        dept_cond = next((c for c in finance_filter.must if c.key == "dept"), None)
        assert dept_cond is not None
        assert dept_cond.match is not None
        allowed_depts = dept_cond.match.any
        assert set(allowed_depts) == {"finance", "corp", "public"}

        # Verify quarantine condition excludes quarantined chunks
        quarantine_cond = next((c for c in finance_filter.must if c.key == "quarantine"), None)
        assert quarantine_cond is not None
        assert quarantine_cond.match.value == False

        # Verify trust_score threshold >= 1.0
        trust_cond = next((c for c in finance_filter.must if c.key == "trust_score"), None)
        assert trust_cond is not None
        assert trust_cond.range is not None
        assert trust_cond.range.gte == 1.0

    def test_hr_role_filter_multi_dimensional(self):
        """Test HR role enforces three conditions: dept, quarantine, trust_score."""
        hr_filter = get_filter_for_role("hr")

        # Filter should be a Filter object with must conditions
        assert isinstance(hr_filter, Filter)
        assert hr_filter.must is not None
        assert len(hr_filter.must) == 3  # dept, quarantine, trust_score

        # Extract field conditions by field name
        field_names = {cond.key for cond in hr_filter.must}
        assert field_names == {"dept", "quarantine", "trust_score"}

        # Verify dept condition allows hr+public only
        dept_cond = next((c for c in hr_filter.must if c.key == "dept"), None)
        assert dept_cond is not None
        allowed_depts = dept_cond.match.any
        assert set(allowed_depts) == {"hr", "public"}

        # Verify quarantine and trust_score conditions
        quarantine_cond = next((c for c in hr_filter.must if c.key == "quarantine"), None)
        assert quarantine_cond is not None
        assert quarantine_cond.match.value == False

        trust_cond = next((c for c in hr_filter.must if c.key == "trust_score"), None)
        assert trust_cond is not None
        assert trust_cond.range.gte == 1.0

    def test_standard_user_filter_higher_trust_threshold(self):
        """Test standard user enforces stricter conditions: visibility + quarantine + trust_score>=1.5."""
        standard_filter = get_filter_for_role("standard")

        # Filter should be a Filter object with must conditions
        assert isinstance(standard_filter, Filter)
        assert standard_filter.must is not None
        assert len(standard_filter.must) == 3  # visibility, quarantine, trust_score

        # Extract field conditions by field name
        field_names = {cond.key for cond in standard_filter.must}
        assert field_names == {"visibility", "quarantine", "trust_score"}

        # Verify visibility condition restricts to public only
        vis_cond = next((c for c in standard_filter.must if c.key == "visibility"), None)
        assert vis_cond is not None
        assert vis_cond.match.value == "public"

        # Verify quarantine condition
        quarantine_cond = next((c for c in standard_filter.must if c.key == "quarantine"), None)
        assert quarantine_cond is not None
        assert quarantine_cond.match.value == False

        # Verify higher trust_score threshold >= 1.5 (stricter than finance/hr)
        trust_cond = next((c for c in standard_filter.must if c.key == "trust_score"), None)
        assert trust_cond is not None
        assert trust_cond.range.gte == 1.5

    def test_invalid_role_raises_error(self):
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Unknown role"):
            get_filter_for_role("invalid_role")
