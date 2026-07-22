import io

import pytest

from app import create_app
from app.extensions import db
from app.models import Product, User


class TestConfig:
    SECRET_KEY = "test-secret"
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = "app/static/uploads"
    MAX_CONTENT_LENGTH = 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def create_user(username, nickname=None):
    user = User(
        username=username,
        nickname=nickname or username,
        bank_name="테스트은행",
        account_number="123-456-7890",
        account_holder=nickname or username,
    )
    user.set_password("Password1!")
    db.session.add(user)
    db.session.commit()
    return user


def login(client, username, password="Password1!"):
    return client.post("/auth/login", data={"username": username, "password": password}, follow_redirects=True)


def create_product(seller, name="노트북", price=10000, description="상태 좋음"):
    product = Product(seller_id=seller.user_id, product_name=name, category="전자기기", price=price, description=description)
    db.session.add(product)
    db.session.commit()
    return product


def png_file(name="item.png", body=None):
    data = body or b"\x89PNG\r\n\x1a\n" + b"0" * 20
    return io.BytesIO(data), name
