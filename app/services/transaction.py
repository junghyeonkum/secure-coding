from flask import abort

from app.extensions import db
from app.models import Delivery, Payment, Review, Transaction, User, utcnow
from app.services.audit import record_audit

ACTIVE_TRANSACTION_STATUSES = {
    "purchase_requested",
    "payment_pending",
    "preparing_shipment",
    "shipping",
    "delivered",
    "purchase_confirmed",
    "completed",
}

TRANSFER_COMPLETED_OR_LATER_STATUSES = {
    "preparing_shipment",
    "shipping",
    "delivered",
    "purchase_confirmed",
    "completed",
}

SHIPPING_STARTED_STATUSES = {
    "shipping",
    "delivered",
    "purchase_confirmed",
    "completed",
}

VALID_TRANSITIONS = {
    "purchase_requested": {"payment_pending", "cancelled"},
    "payment_pending": {"preparing_shipment", "cancelled"},
    "preparing_shipment": {"shipping", "cancelled", "refund_requested"},
    "shipping": {"delivered", "disputed"},
    "delivered": {"purchase_confirmed", "disputed"},
    "purchase_confirmed": {"completed"},
    "completed": set(),
    "cancelled": set(),
    "refund_requested": {"refunded", "disputed"},
    "refunded": set(),
    "disputed": {"refunded", "completed"},
}


def change_status(transaction, new_status, actor_id):
    if new_status not in VALID_TRANSITIONS.get(transaction.transaction_status, set()):
        abort(400)
    transaction.transaction_status = new_status
    record_audit(actor_id, f"transaction:{new_status}", "transaction", transaction.transaction_id)


def create_transaction(product, buyer):
    if (
        product.seller_id == buyer.user_id
        or product.product_status in {"sold", "blocked"}
        or product.product_status != "selling"
    ):
        abort(400)
    existing = Transaction.query.filter(
        Transaction.product_id == product.product_id,
        Transaction.transaction_status.in_(ACTIVE_TRANSACTION_STATUSES),
    ).first()
    if existing:
        abort(409)
    transaction = Transaction(
        product_id=product.product_id,
        buyer_id=buyer.user_id,
        seller_id=product.seller_id,
        amount=product.price,
    )
    db.session.add(transaction)
    db.session.flush()
    payment = Payment(
        transaction_id=transaction.transaction_id,
        sender_id=buyer.user_id,
        receiver_id=product.seller_id,
        amount=transaction.amount,
    )
    db.session.add(payment)
    change_status(transaction, "payment_pending", buyer.user_id)
    db.session.commit()
    return transaction


def complete_transfer(transaction, actor_id):
    try:
        payment = transaction.payment
        product = transaction.product
        if transaction.buyer_id != actor_id:
            abort(403)
        if not payment or not product or product.product_id != transaction.product_id:
            abort(400)
        if payment.receiver_id != product.seller_id:
            abort(400)
        if payment.amount != transaction.amount:
            abort(400)
        if product.product_status != "selling":
            abort(409)
        if (
            payment.transfer_status == "completed"
            or transaction.transaction_status in TRANSFER_COMPLETED_OR_LATER_STATUSES
        ):
            abort(409)
        payment.transfer_status = "completed"
        payment.transfer_time = utcnow()
        transaction.payment_date = payment.transfer_time
        change_status(transaction, "preparing_shipment", actor_id)
        product.product_status = "sold"
        db.session.commit()
        return payment
    except Exception:
        db.session.rollback()
        raise


def register_delivery(transaction, courier, tracking_number, actor_id):
    if transaction.seller_id != actor_id or transaction.transaction_status != "preparing_shipment":
        abort(403)
    if not transaction.payment or transaction.payment.transfer_status != "completed":
        abort(403)
    delivery = Delivery(
        transaction_id=transaction.transaction_id,
        courier=courier,
        tracking_number=tracking_number,
    )
    db.session.add(delivery)
    change_status(transaction, "shipping", actor_id)
    db.session.commit()
    return delivery


def confirm_purchase(transaction, actor_id):
    if (
        transaction.buyer_id != actor_id
        or transaction.transaction_status not in {"shipping", "delivered"}
    ):
        abort(403)
    if transaction.transaction_status == "shipping" and transaction.delivery:
        transaction.delivery.delivery_status = "delivered"
        transaction.delivery.delivered_at = utcnow()
        change_status(transaction, "delivered", actor_id)
    transaction.confirmed_at = utcnow()
    change_status(transaction, "purchase_confirmed", actor_id)
    change_status(transaction, "completed", actor_id)
    transaction.product.product_status = "sold"
    db.session.commit()


def add_review(transaction, reviewer_id, rating, content):
    if (
        transaction.buyer_id != reviewer_id
        or transaction.transaction_status != "completed"
        or transaction.review
    ):
        abort(403)
    review = Review(
        transaction_id=transaction.transaction_id,
        reviewer_id=reviewer_id,
        seller_id=transaction.seller_id,
        rating=int(rating),
        content=content,
    )
    db.session.add(review)
    db.session.flush()
    ratings = [row.rating for row in Review.query.filter_by(seller_id=transaction.seller_id).all()]
    seller = db.session.get(User, transaction.seller_id)
    seller.trust_score = max(1, min(100, round((sum(ratings) / len(ratings)) * 20)))
    record_audit(reviewer_id, "review:create", "transaction", transaction.transaction_id)
    db.session.commit()
    return review


def cancel_transaction(transaction, actor_id, _reason="사용자 취소"):
    if transaction.transaction_status in SHIPPING_STARTED_STATUSES:
        abort(400)
    change_status(transaction, "cancelled", actor_id)
    transaction.cancelled_at = utcnow()
    if transaction.payment:
        transaction.payment.transfer_status = "cancelled"
    other_active = Transaction.query.filter(
        Transaction.product_id == transaction.product_id,
        Transaction.transaction_id != transaction.transaction_id,
        Transaction.transaction_status.in_(ACTIVE_TRANSACTION_STATUSES),
    ).first()
    if not other_active:
        transaction.product.product_status = "selling"
    db.session.commit()
    return True
