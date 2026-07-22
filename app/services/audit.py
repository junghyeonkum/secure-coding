from app.extensions import db
from app.models import AuditLog


def record_audit(actor_id, action, target_type, target_id, report_id=None, reason=""):
    db.session.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            report_id=report_id,
            reason=reason or "",
        )
    )
