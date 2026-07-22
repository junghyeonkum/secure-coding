from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Favorite, Product

bp = Blueprint("favorites", __name__, url_prefix="/favorites")


@bp.route("/")
@login_required
def index():
    favorites = (
        Favorite.query.filter_by(user_id=current_user.user_id)
        .join(Favorite.product)
        .order_by(Favorite.created_at.desc(), Favorite.favorite_id.desc())
        .all()
    )
    return render_template("favorites/index.html", favorites=favorites)


@bp.post("/<int:product_id>/toggle")
@login_required
def toggle(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    favorite = Favorite.query.filter_by(
        user_id=current_user.user_id,
        product_id=product.product_id,
    ).first()
    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        favorited = False
    else:
        db.session.add(Favorite(user_id=current_user.user_id, product_id=product.product_id))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        favorited = True

    wants_json = (
        request.accept_mimetypes.best == "application/json"
        or request.headers.get("X-Requested-With") == "fetch"
    )
    if wants_json:
        return jsonify({"favorited": favorited})
    return redirect(request.referrer or url_for("products.detail", product_id=product.product_id))


@bp.post("/<int:product_id>/delete")
@login_required
def delete(product_id):
    favorite = Favorite.query.filter_by(
        user_id=current_user.user_id,
        product_id=product_id,
    ).first_or_404()
    db.session.delete(favorite)
    db.session.commit()
    return redirect(url_for("favorites.index"))
