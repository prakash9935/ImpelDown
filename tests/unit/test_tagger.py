"""
Unit tests for metadata tagging module (US-102, US-105).

Tests trust score calculation:
  - base_tier contribution (0-3)
  - recency_factor contribution (0-0.5)
  - authority_weight contribution (0-0.5)
  - Sum capped at 4.0
  - Quarantine flagging (trust_score < 1.5)
"""

import pytest
from datetime import datetime, timedelta
from src.secrag.ingestion import tagger


class TestTrustScoreCalculation:
    """Test trust score formula: trust_score = base_tier + recency_factor + authority_weight."""

    def test_official_recent_doc_with_executive_author(self):
        """Test high trust score for official, recent doc with C-level author."""
        # base_tier=3, recent=0.5, c-suite=0.5 → score=4.0
        score, recency, authority = tagger.calculate_trust_score(
            base_tier=3,
            published_date=datetime.utcnow(),  # Today
            author_role="CEO",
        )
        assert score == 4.0
        assert recency == 0.5
        assert authority == 0.5

    def test_team_doc_30_days_old(self):
        """Test medium trust score for 30-day-old team doc."""
        # base_tier=2, 30 days old=0.3, dept-head=0.3 → score=2.6
        old_date = datetime.utcnow() - timedelta(days=30)
        score, recency, authority = tagger.calculate_trust_score(
            base_tier=2,
            published_date=old_date,
            author_role="Director",
        )
        assert score == pytest.approx(2.6)
        assert recency == pytest.approx(0.3)
        assert authority == pytest.approx(0.3)

    def test_user_upload_old_unknown_author(self):
        """Test low trust score for old user upload with no author."""
        # base_tier=1, >1 year old=0.0, unknown=0.0 → score=1.0
        old_date = datetime.utcnow() - timedelta(days=400)
        score, recency, authority = tagger.calculate_trust_score(
            base_tier=1,
            published_date=old_date,
            author_role=None,
        )
        assert score == 1.0
        assert recency == 0.0
        assert authority == 0.0

    def test_score_capped_at_4_0(self):
        """Test that score is capped at 4.0 even if formula exceeds it."""
        # If we try to add more than 4.0, it should be capped
        score, _, _ = tagger.calculate_trust_score(
            base_tier=3,
            published_date=datetime.utcnow(),
            author_role="CEO",
        )
        assert score <= 4.0


class TestChunkTagging:
    """Test chunk tagging with RBAC metadata."""

    def test_tag_chunk_valid_dept_and_visibility(self):
        """Test tagging with valid dept and visibility."""
        tagged = tagger.tag_chunk(
            text="Q2 revenue was $5M",
            source_file="financials.pdf",
            dept="finance",
            visibility="internal",
            base_tier=3,
        )
        assert tagged.dept == "finance"
        assert tagged.visibility == "internal"
        assert tagged.base_tier == 3
        assert tagged.trust_score >= 0

    def test_tag_chunk_invalid_dept_raises_error(self):
        """Test tagging with invalid dept raises ValueError."""
        with pytest.raises(ValueError, match="Invalid dept"):
            tagger.tag_chunk(
                text="Test",
                source_file="test.pdf",
                dept="invalid_dept",
                visibility="internal",
            )

    def test_tag_chunk_invalid_visibility_raises_error(self):
        """Test tagging with invalid visibility raises ValueError."""
        with pytest.raises(ValueError, match="Invalid visibility"):
            tagger.tag_chunk(
                text="Test",
                source_file="test.pdf",
                dept="finance",
                visibility="secret",  # Invalid
            )

    def test_quarantine_flagging_low_trust_score(self):
        """Test quarantine=true when trust_score < 1.5."""
        # Score < 1.5: base_tier=1, old=0.0, unknown=0.0 → score=1.0
        old_date = datetime.utcnow() - timedelta(days=400)
        tagged = tagger.tag_chunk(
            text="Old anonymous doc",
            source_file="old.pdf",
            dept="public",
            visibility="public",
            base_tier=1,
            published_date=old_date,
            author_role=None,
        )
        assert tagged.quarantine is True
        assert tagged.trust_score < 1.5

    def test_no_quarantine_above_threshold(self):
        """Test quarantine=false when trust_score >= 1.5."""
        # Score >= 1.5: base_tier=2, recent=0.5, staff=0.1 → score=2.6
        tagged = tagger.tag_chunk(
            text="Team doc",
            source_file="team.pdf",
            dept="finance",
            visibility="internal",
            base_tier=2,
            published_date=datetime.utcnow(),
            author_role="Engineer",
        )
        assert tagged.quarantine is False
        assert tagged.trust_score >= 1.5

    def test_chunk_id_uniqueness(self):
        """Test that each chunk gets a unique ID."""
        tagged1 = tagger.tag_chunk(
            text="Text 1",
            source_file="doc.pdf",
            dept="finance",
            visibility="internal",
        )
        tagged2 = tagger.tag_chunk(
            text="Text 2",
            source_file="doc.pdf",
            dept="finance",
            visibility="internal",
        )
        assert tagged1.chunk_id != tagged2.chunk_id

    def test_all_valid_depts(self):
        """Test tagging works for all valid departments."""
        for dept in ["finance", "hr", "corp", "public"]:
            tagged = tagger.tag_chunk(
                text="Test",
                source_file="test.pdf",
                dept=dept,
                visibility="public",
            )
            assert tagged.dept == dept

    def test_all_valid_visibilities(self):
        """Test tagging works for all valid visibilities."""
        for visibility in ["public", "internal", "restricted"]:
            tagged = tagger.tag_chunk(
                text="Test",
                source_file="test.pdf",
                dept="finance",
                visibility=visibility,
            )
            assert tagged.visibility == visibility
