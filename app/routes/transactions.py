from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms import DeliveryForm, ReviewForm
from app.models import Product, Transaction
from app.services.transaction import (
    add_review,
    cancel_transaction,
    complete_transfer,
    confirm_purchase,
    create_transaction,
    register_delivery,
)
from app.utils.security import active_account_required, ensure_transaction_participant

bp = Blueprint("transactions", __name__, url_prefix="/transactions")


@bp.post("/buy/<int:product_id>")
@login_required
@active_account_required
def buy(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    transaction = create_transaction(product, current_user)
    return redirect(url_for("transactions.pay", transaction_id=transaction.transaction_id))


@bp.route("/<int:transaction_id>")
@login_required
def detail(transaction_id):
    transaction = db.session.get(Transaction, transaction_id) or abort(404)
    ensure_transaction_participant(transaction)
    return render_template(
        "transactions/detail.html",
        transaction=transaction,
        delivery_form=DeliveryForm(),
    )


@bp.route("/<int:transaction_id>/pay")
@login_required
def pay(transaction_id):
    transaction = db.session.get(Transaction, transaction_id) or abort(404)
    ensure_transaction_participant(transaction)
    if current_user.user_id != transaction.buyer_id:
        abort(403)
    if (
        transaction.payment.transfer_status == "completed"
        or transaction.product.product_status == "sold"
        or transaction.transaction_status
        in {
            "preparing_shipment",
            "shipping",
            "delivered",
            "purchase_confirmed",
            "completed",
        }
    ):
        abort(409)
    return render_template("transactions/pay.html", transaction=transaction)


@bp.post("/<int:transaction_id>/transfer/complete")
@login_required
def transfer_complete(transaction_id):
    transaction = db.session.get(Transaction, transaction_id) or abort(404)
    ensure_transaction_participant(transaction)
    complete_transfer(transaction, current_user.user_id)
    flash("송금 완료로 처리했습니다.")
    return redirect(url_for("transactions.detail", transaction_id=transaction.transaction_id))


@bp.post("/<int:transaction_id>/ship")
@login_required
def ship(transaction_id):
    transaction = db.session.get(Transaction, transaction_id) or abort(404)
    form = DeliveryForm()
    if form.validate_on_submit():
        register_delivery(
            transaction,
            form.courier.data,
            form.tracking_number.data,
            current_user.user_id,
        )
        flash("?댁넚?μ씠 ?깅줉?섏뿀?듬땲??")
    return redirect(url_for("transactions.detail", transaction_id=transaction.transaction_id))


@bp.post("/<int:transaction_id>/confirm")
@login_required
def confirm(transaction_id):
    transaction = db.session.get(Transaction, transaction_id) or abort(404)
    confirm_purchase(transaction, current_user.user_id)
    flash("援щℓ媛 ?뺤젙?섏뿀?듬땲??")
    return redirect(url_for("transactions.detail", transaction_id=transaction.transaction_id))


@bp.route("/<int:transaction_id>/review", methods=["GET", "POST"])
@login_required
def review(transaction_id):
    transaction = db.session.get(Transaction, transaction_id) or abort(404)
    form = ReviewForm()
    if form.validate_on_submit():
        add_review(transaction, current_user.user_id, form.rating.data, form.content.data)
        flash("?됯?媛 ?깅줉?섏뿀?듬땲??")
        return redirect(url_for("transactions.detail", transaction_id=transaction.transaction_id))
    return render_template("transactions/review.html", transaction=transaction, form=form)


@bp.post("/<int:transaction_id>/cancel")
@login_required
def cancel(transaction_id):
    transaction = db.session.get(Transaction, transaction_id) or abort(404)
    ensure_transaction_participant(transaction)
    if transaction.transaction_status in {
        "shipping",
        "delivered",
        "purchase_confirmed",
        "completed",
    }:
        flash("배송이 시작된 거래는 취소할 수 없습니다.")
        return redirect(url_for("transactions.detail", transaction_id=transaction.transaction_id))
    cancel_transaction(transaction, current_user.user_id)
    flash("거래 취소가 처리되었습니다.")
    return redirect(url_for("transactions.detail", transaction_id=transaction.transaction_id))
