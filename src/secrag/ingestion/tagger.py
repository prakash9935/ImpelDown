"""
Metadata Tagging and Trust Score Calculation (US-102, US-105)

Assigns RBAC metadata (dept, visibility, trust_score) to each chunk at ingestion.

Trust Score Formula (SYSTEM_DESIGN.md Section 5.1):
  trust_score = base_tier + recency_factor + authority_weight (capped at 4.0)

  base_tier (0–3):
    - 3: Official company policy or legal document
    - 2: Team/department documentation
    - 1: User-uploaded or external material
    - 0: Anonymous/untrusted source

  recency_factor (0–0.5):
    - 0.5: Published within last 30 days
    - 0.3: Published within last 90 days
    - 0.1: Published within last 1 year
    - 0.0: Older than 1 year

  authority_weight (0–0.5):
    - 0.5: Author is C-level executive or legal counsel
    - 0.3: Author is department head or security officer
    - 0.1: Author is individual contributor
    - 0.0: Author unknown
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Valid department and visibility values
VALID_DEPTS = {"finance", "hr", "corp", "public"}
VALID_VISIBILITIES = {"public", "internal", "restricted"}
TRUST_SCORE_MIN_THRESHOLD = 1.5


@dataclass
class TaggedChunk:
    """Chunk with RBAC metadata and trust score."""

    chunk_id: str
    text: str
    source_file: str
    dept: str  # finance, hr, corp, public
    visibility: str  # public, internal, restricted
    trust_score: float
    base_tier: int
    recency_factor: float
    authority_weight: float
    quarantine: bool
    ingestion_timestamp: datetime = field(default_factory=datetime.utcnow)


def calculate_trust_score(
    base_tier: int,
    published_date: Optional[datetime] = None,
    author_role: Optional[str] = None,
) -> tuple[float, float, float]:
    """
    Calculate chunk trust score per SYSTEM_DESIGN.md Section 5.1 (US-102).

    Returns the full score plus component breakdown.

    Args:
        base_tier: 0-3 based on document type
        published_date: Document publication date (default: today)
        author_role: Author's role (c-suite, dept-head, staff, unknown)

    Returns:
        (trust_score: float, recency_factor: float, authority_weight: float)
    """
    # Validate base_tier
    if not 0 <= base_tier <= 3:
        logger.warning(f"Invalid base_tier {base_tier}, clamping to [0, 3]")
        base_tier = max(0, min(3, base_tier))

    # Calculate recency factor (0-0.5)
    if published_date is None:
        published_date = datetime.utcnow()

    days_old = (datetime.utcnow() - published_date).days

    if days_old < 30:
        recency_factor = 0.5
    elif days_old < 90:
        recency_factor = 0.3
    elif days_old < 365:
        recency_factor = 0.1
    else:
        recency_factor = 0.0

    # Calculate authority weight (0-0.5)
    authority_weight = 0.0
    if author_role:
        role_lower = author_role.lower()
        # Check for keywords - use word boundaries to avoid "cto" matching in "director"
        c_suite_keywords = [
            "c-suite",
            "ceo",
            "cfo",
            "chief executive",
            "chief financial",
            "chief technology",
            "legal",
            "counsel",
            "general counsel",
        ]
        dept_head_keywords = ["dept-head", "head", "director", "security", "manager", "team lead"]
        staff_keywords = ["staff", "contributor", "engineer", "developer", "analyst"]

        # Check if any keyword is in the role (for hyphenated/multi-word keywords)
        # OR if any keyword appears as a complete word
        role_words = set(role_lower.replace("-", " ").split())

        if any(x in role_lower for x in c_suite_keywords if "-" in x or " " in x) or any(
            x in role_words for x in ["ceo", "cfo", "legal", "counsel"]
        ):
            authority_weight = 0.5
        elif any(x in role_lower for x in dept_head_keywords if "-" in x or " " in x) or any(
            x in role_words for x in ["director", "security", "manager", "head"]
        ):
            authority_weight = 0.3
        elif any(x in role_words for x in staff_keywords):
            authority_weight = 0.1

    # Calculate total trust score (capped at 4.0)
    trust_score = min(4.0, base_tier + recency_factor + authority_weight)

    return trust_score, recency_factor, authority_weight


def tag_chunk(
    text: str,
    source_file: str,
    dept: str,
    visibility: str,
    base_tier: int = 1,
    published_date: Optional[datetime] = None,
    author_role: Optional[str] = None,
) -> TaggedChunk:
    """
    Tag a chunk with RBAC metadata and compute trust score (US-102, US-105).

    Args:
        text: Chunk text content
        source_file: Source PDF filename
        dept: Department code (finance, hr, corp, public)
        visibility: Visibility level (public, internal, restricted)
        base_tier: Document trustworthiness tier (0-3, default 1)
        published_date: When document was published
        author_role: Who wrote the document

    Returns:
        TaggedChunk with all metadata and trust_score

    Raises:
        ValueError: If dept or visibility are invalid
    """
    # Validate dept and visibility
    if dept not in VALID_DEPTS:
        raise ValueError(f"Invalid dept '{dept}'. Must be one of: {', '.join(VALID_DEPTS)}")

    if visibility not in VALID_VISIBILITIES:
        raise ValueError(
            f"Invalid visibility '{visibility}'. Must be one of: {', '.join(VALID_VISIBILITIES)}"
        )

    # Generate unique chunk ID
    chunk_id = f"{source_file}_{uuid.uuid4().hex[:8]}"

    # Calculate trust score and components
    trust_score, recency_factor, authority_weight = calculate_trust_score(
        base_tier, published_date, author_role
    )

    # Determine quarantine status
    quarantine = trust_score < TRUST_SCORE_MIN_THRESHOLD

    logger.info(
        f"Tagged chunk {chunk_id}: dept={dept}, visibility={visibility}, "
        f"trust_score={trust_score:.2f}, quarantine={quarantine}"
    )

    return TaggedChunk(
        chunk_id=chunk_id,
        text=text,
        source_file=source_file,
        dept=dept,
        visibility=visibility,
        trust_score=trust_score,
        base_tier=base_tier,
        recency_factor=recency_factor,
        authority_weight=authority_weight,
        quarantine=quarantine,
    )
