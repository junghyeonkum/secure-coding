from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.forms import ReportForm
from app.models import Product, Report, User
from app.utils.security import active_account_required, check_rate_limit

bp = Blueprint("reports", __name__, url_prefix="/reports")


def _target_from_request():
    reported_user_id = request.values.get("reported_user_id", type=int)
    reported_product_id = request.values.get("reported_product_id", type=int)

    if bool(reported_user_id) == bool(reported_product_id):
        abort(400)

    if reported_product_id:
        product = db.session.get(Product, reported_product_id)
        if not product:
            abort(404)
        seller_id = request.values.get("seller_id", type=int)
        if seller_id is None or seller_id != product.seller_id:
            abort(400)
        return {
            "kind": "product",
            "product": product,
            "seller": product.seller,
            "cancel_url": url_for("products.detail", product_id=product.product_id),
            "reported_user_id": None,
            "reported_product_id": product.product_id,
        }

    user = db.session.get(User, reported_user_id)
    if not user:
        abort(404)
    return {
        "kind": "user",
        "user": user,
        "cancel_url": url_for("users.profile", user_id=user.user_id),
        "reported_user_id": user.user_id,
        "reported_product_id": None,
    }


@bp.route("/new", methods=["GET", "POST"])
@login_required
@active_account_required
def new():
    target = _target_from_request()
    form = ReportForm()
    form.reported_user_id.data = target["reported_user_id"]
    form.reported_product_id.data = target["reported_product_id"]

    if form.validate_on_submit():
        check_rate_limit("reports", 10)
        report = Report(
            reporter_id=current_user.user_id,
            reported_user_id=target["reported_user_id"],
            reported_product_id=target["reported_product_id"],
            report_type=form.report_type.data,
            reason=form.reason.data,
        )
        try:
            db.session.add(report)
            if target["kind"] == "user":
                target["user"].report_count += 1
            else:
                target["product"].report_count += 1
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("이미 신고한 대상입니다.")
            return render_template("reports/form.html", form=form, target=target), 400
        flash("신고가 접수되었습니다.")
        return redirect(url_for("main.index"))

    return render_template("reports/form.html", form=form, target=target)
