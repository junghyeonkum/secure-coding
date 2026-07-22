import io

from app import create_app
from app.extensions import db
from app.models import ChatRoom, Payment, PrivateMessage, Product, Report, Review, Transaction
from app.services.transaction import change_status
from tests.conftest import TestConfig, create_product, create_user, login, png_file


def test_duplicate_username_blocked(client):
    data = {"username": "alice", "password": "Password1!", "nickname": "alice"}
    client.post("/auth/register", data=data)
    response = client.post("/auth/register", data=data)
    assert response.status_code == 400


def test_wrong_password_fails(client, app):
    with app.app_context():
        create_user("alice")
    response = client.post("/auth/login", data={"username": "alice", "password": "bad"})
    assert response.status_code == 401


def test_sql_injection_string_is_data(client, app):
    with app.app_context():
        seller = create_user("seller")
        create_product(seller, name="' OR 1=1 --")
    response = client.get("/products/?q=%27%20OR%201%3D1%20--")
    assert response.status_code == 200
    assert b"OR 1=1" in response.data


def test_stored_xss_is_escaped(client, app):
    with app.app_context():
        seller = create_user("seller")
        product = create_product(seller, description="<script>alert(1)</script>")
    response = client.get(f"/products/{product.product_id}")
    assert b"<script>alert(1)</script>" not in response.data
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in response.data


def test_csrf_missing_post_blocked():
    class CsrfConfig(TestConfig):
        WTF_CSRF_ENABLED = True

    app = create_app(CsrfConfig)
    with app.app_context():
        db.create_all()
        create_user("seller")
    client = app.test_client()
    login(client, "seller")
    response = client.post("/products/new", data={"product_name": "x"})
    assert response.status_code == 400


def test_other_user_cannot_modify_or_delete_product(client, app):
    with app.app_context():
        owner = create_user("owner")
        create_user("other")
        product = create_product(owner)
    login(client, "other")
    assert client.get(f"/products/{product.product_id}/edit").status_code == 403
    assert client.post(f"/products/{product.product_id}/delete").status_code == 403


def test_other_user_cannot_access_chat_room(client, app):
    with app.app_context():
        seller = create_user("seller")
        buyer = create_user("buyer")
        create_user("other")
        product = create_product(seller)
        room = ChatRoom(product_id=product.product_id, buyer_id=buyer.user_id, seller_id=seller.user_id)
        db.session.add(room)
        db.session.commit()
    login(client, "other")
    assert client.get(f"/chat/rooms/{room.room_id}").status_code == 403


def test_other_user_cannot_access_transaction(client, app):
    with app.app_context():
        seller = create_user("seller")
        buyer = create_user("buyer")
        create_user("other")
        product = create_product(seller)
        tx = Transaction(product_id=product.product_id, buyer_id=buyer.user_id, seller_id=seller.user_id, amount=product.price)
        db.session.add(tx)
        db.session.commit()
    login(client, "other")
    assert client.get(f"/transactions/{tx.transaction_id}").status_code == 403


def test_non_buyer_cannot_access_transfer_page(client, app):
    with app.app_context():
        seller = create_user("seller")
        buyer = create_user("buyer")
        create_user("other")
        product = create_product(seller)
        tx = Transaction(product_id=product.product_id, buyer_id=buyer.user_id, seller_id=seller.user_id, amount=product.price, transaction_status="payment_pending")
        db.session.add(tx)
        db.session.flush()
        db.session.add(Payment(transaction_id=tx.transaction_id, sender_id=buyer.user_id, receiver_id=seller.user_id, amount=product.price))
        db.session.commit()
        tx_id = tx.transaction_id
    login(client, "seller")
    assert client.get(f"/transactions/{tx_id}/pay").status_code == 403
    client.post("/auth/logout")
    login(client, "other")
    assert client.get(f"/transactions/{tx_id}/pay").status_code == 403


def test_buyer_cannot_register_delivery_and_seller_cannot_confirm(client, app):
    with app.app_context():
        seller = create_user("seller")
        buyer = create_user("buyer")
        product = create_product(seller)
        tx = Transaction(product_id=product.product_id, buyer_id=buyer.user_id, seller_id=seller.user_id, amount=product.price, transaction_status="preparing_shipment")
        db.session.add(tx)
        db.session.commit()
        tx_id = tx.transaction_id
    login(client, "buyer")
    assert client.post(f"/transactions/{tx_id}/ship", data={"courier": "x", "tracking_number": "1"}).status_code == 403
    client.post("/auth/logout")
    login(client, "seller")
    assert client.post(f"/transactions/{tx_id}/confirm").status_code == 403


def test_duplicate_review_and_report_blocked(client, app):
    with app.app_context():
        seller = create_user("seller")
        buyer = create_user("buyer")
        product = create_product(seller)
        tx = Transaction(product_id=product.product_id, buyer_id=buyer.user_id, seller_id=seller.user_id, amount=product.price, transaction_status="completed")
        db.session.add(tx)
        db.session.flush()
        db.session.add(Review(transaction_id=tx.transaction_id, reviewer_id=buyer.user_id, seller_id=seller.user_id, rating=5, content="ok"))
        db.session.commit()
        tx_id = tx.transaction_id
    login(client, "buyer")
    assert client.post(f"/transactions/{tx_id}/review", data={"rating": "4", "content": "again"}).status_code == 403
    report_data = {"report_type": "abuse", "reported_user_id": seller.user_id, "reason": "반복적인 욕설 신고입니다."}
    assert client.post("/reports/new", data=report_data).status_code == 302
    assert client.post("/reports/new", data=report_data).status_code == 400


def test_file_upload_validation(client, app):
    with app.app_context():
        create_user("seller")
    login(client, "seller")
    response = client.post(
        "/products/new",
        data={"product_name": "x", "category": "전자기기", "price": 1, "description": "d", "image": (io.BytesIO(b"not image"), "x.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    response = client.post(
        "/products/new",
        data={"product_name": "x", "category": "전자기기", "price": 1, "description": "d", "image": png_file(body=b"\x89PNG\r\n\x1a\n" + b"x" * 2000)},
        content_type="multipart/form-data",
    )
    assert response.status_code == 413


def test_duplicate_transfer_completion_blocked(client, app):
    with app.app_context():
        seller = create_user("seller")
        create_user("buyer")
        product = create_product(seller, price=10000)
    login(client, "buyer")
    client.post(f"/transactions/buy/{product.product_id}")
    with app.app_context():
        tx = Transaction.query.first()
        tx_id = tx.transaction_id
    assert client.post(
        f"/transactions/{tx_id}/transfer/complete",
    ).status_code == 302
    assert client.post(
        f"/transactions/{tx_id}/transfer/complete",
    ).status_code == 409


def test_seller_cannot_ship_before_transfer_completed(client, app):
    with app.app_context():
        seller = create_user("seller")
        buyer = create_user("buyer")
        product = create_product(seller)
        tx = Transaction(product_id=product.product_id, buyer_id=buyer.user_id, seller_id=seller.user_id, amount=product.price, transaction_status="payment_pending")
        db.session.add(tx)
        db.session.flush()
        db.session.add(Payment(transaction_id=tx.transaction_id, sender_id=buyer.user_id, receiver_id=seller.user_id, amount=product.price))
        db.session.commit()
        tx_id = tx.transaction_id
    login(client, "seller")
    assert client.post(f"/transactions/{tx_id}/ship", data={"courier": "x", "tracking_number": "1"}).status_code == 403


def test_invalid_transaction_state_change_blocked(app):
    with app.app_context():
        seller = create_user("seller")
        buyer = create_user("buyer")
        product = create_product(seller)
        tx = Transaction(product_id=product.product_id, buyer_id=buyer.user_id, seller_id=seller.user_id, amount=product.price)
        db.session.add(tx)
        db.session.commit()
        try:
            change_status(tx, "completed", buyer.user_id)
            assert False
        except Exception as exc:
            assert getattr(exc, "code", None) == 400
