import pytest

from app.extensions import db
from app.models import Favorite, Payment, Product, Transaction
from tests.conftest import create_product, create_user, login


def start_purchase(client, app):
    with app.app_context():
        seller = create_user("seller")
        create_user("buyer")
        product = create_product(seller)
        product_id = product.product_id
    login(client, "buyer")
    response = client.post(f"/transactions/buy/{product_id}")
    assert response.status_code == 302
    with app.app_context():
        transaction = Transaction.query.filter_by(product_id=product_id).first()
        return product_id, transaction.transaction_id


def test_transfer_completion_marks_product_sold(client, app):
    product_id, transaction_id = start_purchase(client, app)
    response = client.post(f"/transactions/{transaction_id}/transfer/complete")
    assert response.status_code == 302
    with app.app_context():
        product = db.session.get(Product, product_id)
        transaction = db.session.get(Transaction, transaction_id)
        assert product.product_status == "sold"
        assert transaction.transaction_status == "preparing_shipment"
        assert transaction.payment.transfer_status == "completed"


def test_sold_product_repurchase_blocked(client, app):
    product_id, transaction_id = start_purchase(client, app)
    client.post(f"/transactions/{transaction_id}/transfer/complete")
    client.post("/auth/logout")
    with app.app_context():
        create_user("other")
    login(client, "other")
    assert client.post(f"/transactions/buy/{product_id}").status_code == 400


def test_active_transaction_blocks_other_buyers(client, app):
    product_id, _transaction_id = start_purchase(client, app)
    client.post("/auth/logout")
    with app.app_context():
        create_user("other")
    login(client, "other")
    assert client.post(f"/transactions/buy/{product_id}").status_code == 409


def test_sold_product_excluded_from_selling_lists(client, app):
    product_id, transaction_id = start_purchase(client, app)
    client.post(f"/transactions/{transaction_id}/transfer/complete")
    list_response = client.get("/products/")
    main_response = client.get("/")
    with app.app_context():
        product_name = db.session.get(Product, product_id).product_name.encode()
    assert product_name not in list_response.data
    assert product_name not in main_response.data


def test_sold_favorite_remains_with_sold_badge(client, app):
    product_id, transaction_id = start_purchase(client, app)
    with app.app_context():
        buyer = create_user("favorite_owner")
        db.session.add(Favorite(user_id=buyer.user_id, product_id=product_id))
        db.session.commit()
    client.post(f"/transactions/{transaction_id}/transfer/complete")
    client.post("/auth/logout")
    login(client, "favorite_owner")
    response = client.get("/favorites/")
    assert response.status_code == 200
    assert "품절".encode() in response.data


def test_duplicate_transfer_completion_blocked_by_status(client, app):
    _product_id, transaction_id = start_purchase(client, app)
    assert client.post(f"/transactions/{transaction_id}/transfer/complete").status_code == 302
    assert client.post(f"/transactions/{transaction_id}/transfer/complete").status_code == 409


def test_before_shipping_shows_not_shipped_and_allows_cancel_after_transfer(client, app):
    product_id, transaction_id = start_purchase(client, app)
    client.post(f"/transactions/{transaction_id}/transfer/complete")
    detail = client.get(f"/transactions/{transaction_id}")
    assert detail.status_code == 200
    assert "배송 전".encode() in detail.data
    assert "거래 취소".encode() in detail.data
    response = client.post(f"/transactions/{transaction_id}/cancel")
    assert response.status_code == 302
    with app.app_context():
        product = db.session.get(Product, product_id)
        transaction = db.session.get(Transaction, transaction_id)
        assert product.product_status == "selling"
        assert transaction.transaction_status == "cancelled"
        assert transaction.payment.transfer_status == "cancelled"


def test_cancel_hidden_and_redirected_after_shipping(client, app):
    _product_id, transaction_id = start_purchase(client, app)
    client.post(f"/transactions/{transaction_id}/transfer/complete")
    client.post("/auth/logout")
    login(client, "seller")
    client.post(f"/transactions/{transaction_id}/ship", data={"courier": "택배", "tracking_number": "12345"})
    detail = client.get(f"/transactions/{transaction_id}")
    assert detail.status_code == 200
    assert "거래 취소".encode() not in detail.data
    response = client.post(f"/transactions/{transaction_id}/cancel")
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Transaction, transaction_id).transaction_status == "shipping"


def test_transfer_completion_rolls_back_on_error(client, app, monkeypatch):
    product_id, transaction_id = start_purchase(client, app)

    def fail_record_audit(*_args, **_kwargs):
        raise RuntimeError("audit failed")

    monkeypatch.setattr("app.services.transaction.record_audit", fail_record_audit)
    with pytest.raises(RuntimeError):
        client.post(f"/transactions/{transaction_id}/transfer/complete")
    with app.app_context():
        product = db.session.get(Product, product_id)
        transaction = db.session.get(Transaction, transaction_id)
        assert product.product_status == "selling"
        assert transaction.transaction_status == "payment_pending"
        assert transaction.payment.transfer_status == "pending"


def test_cancel_before_transfer_restores_selling_and_cancels_payment(client, app):
    product_id, transaction_id = start_purchase(client, app)
    response = client.post(f"/transactions/{transaction_id}/cancel")
    assert response.status_code == 302
    with app.app_context():
        product = db.session.get(Product, product_id)
        transaction = db.session.get(Transaction, transaction_id)
        assert product.product_status == "selling"
        assert transaction.transaction_status == "cancelled"
        assert transaction.payment.transfer_status == "cancelled"
