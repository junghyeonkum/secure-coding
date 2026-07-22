from datetime import timedelta
import re

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Favorite, Product, utcnow
from tests.conftest import create_product, create_user, login


def test_logged_in_user_can_add_favorite(client, app):
    with app.app_context():
        seller = create_user("seller")
        create_user("buyer")
        product = create_product(seller)
        product_id = product.product_id
    login(client, "buyer")
    response = client.post(f"/favorites/{product_id}/toggle", headers={"Accept": "application/json"})
    assert response.status_code == 200
    assert response.json["favorited"] is True
    with app.app_context():
        assert Favorite.query.count() == 1


def test_favorite_toggle_deletes_existing_favorite(client, app):
    with app.app_context():
        seller = create_user("seller")
        buyer = create_user("buyer")
        product = create_product(seller)
        db.session.add(Favorite(user_id=buyer.user_id, product_id=product.product_id))
        db.session.commit()
        product_id = product.product_id
    login(client, "buyer")
    response = client.post(f"/favorites/{product_id}/toggle", headers={"Accept": "application/json"})
    assert response.status_code == 200
    assert response.json["favorited"] is False
    with app.app_context():
        assert Favorite.query.count() == 0


def test_duplicate_favorite_is_blocked_by_unique_constraint(app):
    with app.app_context():
        seller = create_user("seller")
        buyer = create_user("buyer")
        product = create_product(seller)
        db.session.add(Favorite(user_id=buyer.user_id, product_id=product.product_id))
        db.session.commit()
        db.session.add(Favorite(user_id=buyer.user_id, product_id=product.product_id))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_anonymous_user_cannot_add_favorite(client, app):
    with app.app_context():
        seller = create_user("seller")
        product = create_product(seller)
        product_id = product.product_id
    response = client.post(f"/favorites/{product_id}/toggle")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_favorites_page_only_shows_current_user_items(client, app):
    with app.app_context():
        seller = create_user("seller")
        buyer = create_user("buyer")
        other = create_user("other")
        mine = create_product(seller, name="mine")
        theirs = create_product(seller, name="theirs")
        db.session.add(Favorite(user_id=buyer.user_id, product_id=mine.product_id))
        db.session.add(Favorite(user_id=other.user_id, product_id=theirs.product_id))
        db.session.commit()
    login(client, "buyer")
    response = client.get("/favorites/")
    assert response.status_code == 200
    assert b"mine" in response.data
    assert b"theirs" not in response.data


def test_product_delete_removes_favorites(client, app):
    with app.app_context():
        seller = create_user("seller")
        buyer = create_user("buyer")
        product = create_product(seller)
        product_id = product.product_id
        db.session.add(Favorite(user_id=buyer.user_id, product_id=product_id))
        db.session.commit()
    login(client, "seller")
    assert client.post(f"/products/{product_id}/delete").status_code == 302
    with app.app_context():
        assert db.session.get(Product, product_id) is None
        assert Favorite.query.count() == 0


def test_favorites_page_orders_newest_first(client, app):
    with app.app_context():
        seller = create_user("seller")
        buyer = create_user("buyer")
        older = create_product(seller, name="older")
        newer = create_product(seller, name="newer")
        now = utcnow()
        db.session.add(Favorite(user_id=buyer.user_id, product_id=older.product_id, created_at=now - timedelta(days=1)))
        db.session.add(Favorite(user_id=buyer.user_id, product_id=newer.product_id, created_at=now))
        db.session.commit()
    login(client, "buyer")
    response = client.get("/favorites/")
    assert response.status_code == 200
    names = re.findall(rb'<h2 class="h5 mb-0">(.*?)</h2>', response.data)
    assert names == [b"newer", b"older"]
