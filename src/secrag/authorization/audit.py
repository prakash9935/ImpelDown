"""
Audit Trail Logging (US-601, Phase 4.2)

Logs all authenticated actions to JSON audit log for compliance.
Writes to var/audit.log with rotation at 10MB.
"""

import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Create var directory if it doesn't exist
VAR_DIR = Path(__file__).parent.parent.parent.parent / "var"
VAR_DIR.mkdir(exist_ok=True)
AUDIT_LOG_PATH = VAR_DIR / "audit.log"

# Configure rotating audit logger
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# Remove any existing handlers to avoid duplicates
audit_logger.handlers = []

# Rotating file handler (10MB rotation)
handler = logging.handlers.RotatingFileHandler(
    str(AUDIT_LOG_PATH),
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,  # Keep 5 backups
)


# JSON formatter for audit events
class AuditFormatter(logging.Formatter):
    """Formatter that outputs audit events as JSON lines."""

    def format(self, record):
        """Format record as JSON."""
        audit_event = {
            "timestamp": datetime.utcnow().isoformat(),
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        return json.dumps(audit_event)


handler.setFormatter(AuditFormatter())
audit_logger.addHandler(handler)

# Also log to console at DEBUG level
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
# audit_logger.addHandler(console_handler)  # Uncomment for debugging


async def log_audit_event(
    user_id: str,
    role: str,
    action: str,
    resource: str,
    result: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log an audit event (called from middleware on every authenticated request).

    Writes to JSON audit log with fields:
      {
        "timestamp": ISO 8601,
        "user_id": str,
        "role": str,
        "action": str (GET, POST, etc.),
        "resource": str (API path),
        "result": str (success, failure, etc.),
        "metadata": dict (optional additional context),
      }

    Args:
        user_id: User identifier
        role: User's RBAC role
        action: HTTP method or action name
        resource: Resource being accessed (path)
        result: Result of action (success, forbidden, error, etc.)
        metadata: Additional context (status code, error message, etc.)
    """
    try:
        audit_entry = {
            "user_id": user_id,
            "role": role,
            "action": action,
            "resource": resource,
            "result": result,
        }

        if metadata:
            audit_entry["metadata"] = metadata

        # Format as JSON for structured logging
        audit_logger.info(json.dumps(audit_entry))

    except Exception as e:
        # Never raise from audit logging — log to regular logger instead
        logging_logger = logging.getLogger(__name__)
        logging_logger.error(f"Error in audit logging: {e}")


def get_audit_log_path() -> Path:
    """Get path to audit log file."""
    return AUDIT_LOG_PATH


def clear_audit_log() -> None:
    """Clear audit log (admin only)."""
    try:
        if AUDIT_LOG_PATH.exists():
            AUDIT_LOG_PATH.unlink()
            audit_logger.info("Audit log cleared")
    except Exception as e:
        logging_logger = logging.getLogger(__name__)
        logging_logger.error(f"Error clearing audit log: {e}")
