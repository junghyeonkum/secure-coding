from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Product, Report, User
from app.services.audit import record_audit
from app.utils.security import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@login_required
@admin_required
def dashboard():
    return render_template(
        "admin/dashboard.html",
        pending_reports=Report.query.filter_by(report_status="pending").count(),
        restricted_users=User.query.filter_by(account_status="restricted").count(),
        blocked_users=User.query.filter_by(account_status="blocked").count(),
        blocked_products=Product.query.filter_by(product_status="blocked").count(),
    )


@bp.route("/reports")
@login_required
@admin_required
def reports():
    report_list = Report.query.order_by(Report.created_at.desc()).all()
    return render_template("admin/reports.html", reports=report_list)


@bp.route("/reports/<int:report_id>")
@login_required
@admin_required
def report_detail(report_id):
    report = db.session.get(Report, report_id) or abort(404)
    return render_template("admin/report_detail.html", report=report)


@bp.post("/reports/<int:report_id>/action")
@login_required
@admin_required
def report_action(report_id):
    report = db.session.get(Report, report_id) or abort(404)
    action = request.form.get("action", "")
    reason = request.form.get("reason", "").strip()

    if action == "review":
        report.report_status = "reviewing"
        audit(report, "report:review", "report", report.report_id, reason)
    elif action == "approve":
        report.report_status = "resolved"
        audit(report, "report:approve", "report", report.report_id, reason)
    elif action == "reject":
        report.report_status = "rejected"
        audit(report, "report:reject", "report", report.report_id, reason)
    elif action in {"restrict_user", "block_user", "activate_user"}:
        user = report.reported_user or abort(400)
        apply_user_action(report, user, action, reason)
    elif action in {"block_product", "unblock_product"}:
        product = report.reported_product or abort(400)
        apply_product_action(report, product, action, reason)
    else:
        abort(400)

    db.session.commit()
    flash("관리자 조치가 저장되었습니다.")
    return redirect(url_for("admin.report_detail", report_id=report.report_id))


def apply_user_action(report, user, action, reason):
    if user.user_id == current_user.user_id and action in {"restrict_user", "block_user"}:
        abort(400)
    last_active_admin = (
        user.is_admin
        and action == "block_user"
        and User.query.filter_by(is_admin=True, account_status="active").count() <= 1
    )
    if last_active_admin:
        abort(400)

    if action == "restrict_user":
        user.account_status = "restricted"
        audit(report, "user:restrict", "user", user.user_id, reason)
    elif action == "block_user":
        user.account_status = "blocked"
        audit(report, "user:block", "user", user.user_id, reason)
    elif action == "activate_user":
        user.account_status = "active"
        audit(report, "user:activate", "user", user.user_id, reason)


def apply_product_action(report, product, action, reason):
    if action == "block_product":
        product.product_status = "blocked"
        audit(report, "product:block", "product", product.product_id, reason)
    elif action == "unblock_product":
        product.product_status = "selling"
        audit(report, "product:unblock", "product", product.product_id, reason)


def audit(report, action, target_type, target_id, reason):
    record_audit(
        current_user.user_id,
        action,
        target_type,
        target_id,
        report_id=report.report_id,
        reason=reason,
    )
