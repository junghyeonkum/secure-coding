from app.extensions import db
from app.models import ChatRoom, Payment, Product, Report, Review, Transaction
from tests.conftest import create_product, create_user, login, png_file


def test_register_and_login(client):
    response = client.post(
        "/auth/register",
        data={"username": "alice", "password": "Password1!", "nickname": "앨리스"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "회원가입이 완료되었습니다".encode() in response.data
    response = login(client, "alice")
    assert response.status_code == 200


def test_product_create_and_view(client, app):
    with app.app_context():
        create_user("seller")
    login(client, "seller")
    response = client.post(
        "/products/new",
        data={
            "product_name": "카메라",
            "category": "전자기기",
            "price": 30000,
            "description": "깨끗합니다.",
            "image": png_file(),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "카메라".encode() in response.data
    response = client.get("/products/1")
    assert response.status_code == 200
    assert "카메라".encode() in response.data


def test_chat_room_and_message(client, app):
    with app.app_context():
        seller = create_user("seller")
        create_user("buyer")
        product = create_product(seller)
    login(client, "buyer")
    response = client.post(f"/chat/start/{product.product_id}", follow_redirects=True)
    assert response.status_code == 200
    response = client.post("/chat/rooms/1", data={"content": "구매 가능할까요?"}, follow_redirects=True)
    assert response.status_code == 200
    assert "구매 가능할까요?".encode() in response.data
    with app.app_context():
        assert ChatRoom.query.count() == 1


def test_seller_mypage_shows_chat_for_own_product(client, app):
    with app.app_context():
        seller = create_user("kjh", nickname="kjh")
        create_user("white", nickname="white")
        product = create_product(seller, name="kjh 상품")
        product_id = product.product_id

    login(client, "white")
    response = client.post(f"/chat/start/{product_id}", follow_redirects=True)
    assert response.status_code == 200
    client.post("/auth/logout")

    login(client, "kjh")
    response = client.get("/users/mypage")
    assert response.status_code == 200
    assert "내 상품에 온 채팅".encode() in response.data
    assert "kjh 상품".encode() in response.data
    assert "구매자 white".encode() in response.data


def test_transaction_payment_delivery_confirm_review_report(client, app):
    with app.app_context():
        seller = create_user("seller")
        create_user("buyer")
        product = create_product(seller)
    login(client, "buyer")
    response = client.post(f"/transactions/buy/{product.product_id}", follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        transaction = Transaction.query.first()
        payment = Payment.query.first()
        transaction_id = transaction.transaction_id
    response = client.post(
        f"/transactions/{transaction_id}/transfer/complete",
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        transaction = db.session.get(Transaction, transaction_id)
        assert transaction.transaction_status == "preparing_shipment"
        assert transaction.payment.transfer_status == "completed"
    client.post("/auth/logout")
    login(client, "seller")
    response = client.post(
        f"/transactions/{transaction_id}/ship",
        data={"courier": "우체국", "tracking_number": "12345"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    client.post("/auth/logout")
    login(client, "buyer")
    response = client.post(f"/transactions/{transaction_id}/confirm", follow_redirects=True)
    assert response.status_code == 200
    response = client.post(
        f"/transactions/{transaction_id}/review",
        data={"rating": "5", "content": "좋은 판매자입니다."},
        follow_redirects=True,
    )
    assert response.status_code == 200
    response = client.post(
        "/reports/new",
        data={
            "report_type": "fraud",
            "reported_product_id": product.product_id,
            "seller_id": product.seller_id,
            "reason": "금지 물품으로 의심됩니다.",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert Review.query.count() == 1
        assert Report.query.count() == 1


def test_transfer_pending_until_buyer_marks_complete(client, app):
    with app.app_context():
        seller = create_user("seller")
        create_user("buyer")
        product = create_product(seller)
    login(client, "buyer")
    client.post(f"/transactions/buy/{product.product_id}")
    with app.app_context():
        transaction = Transaction.query.first()
        transaction_id = transaction.transaction_id
    response = client.get(f"/transactions/{transaction_id}/pay")
    assert response.status_code == 200
    with app.app_context():
        assert db.session.get(Transaction, transaction_id).transaction_status == "payment_pending"
