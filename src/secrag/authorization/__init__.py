"""Authorization module for PBAC and audit trail."""

from src.secrag.authorization.audit import get_audit_log_path, log_audit_event

__all__ = ["log_audit_event", "get_audit_log_path"]
