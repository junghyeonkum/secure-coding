from flask import Blueprint, render_template, request
from flask_login import current_user

from app.extensions import db
from app.models import Favorite, Product
from app.services.recommendation import recommended_products

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    sort = request.args.get("sort", "latest")
    products_query = Product.query.filter_by(product_status="selling")
    if query:
        products_query = products_query.filter(Product.product_name.contains(query))
    if category:
        products_query = products_query.filter_by(category=category)
    if sort == "price_asc":
        products_query = products_query.order_by(Product.price.asc())
    elif sort == "price_desc":
        products_query = products_query.order_by(Product.price.desc())
    elif sort == "views":
        products_query = products_query.order_by(Product.view_count.desc())
    else:
        products_query = products_query.order_by(Product.created_at.desc())
    products = products_query.limit(12).all()
    latest = (
        Product.query.filter_by(product_status="selling")
        .order_by(Product.created_at.desc())
        .limit(5)
        .all()
    )
    popular = (
        Product.query.filter_by(product_status="selling")
        .order_by(Product.view_count.desc())
        .limit(5)
        .all()
    )
    recommendations = recommended_products(current_user)
    categories = [row[0] for row in db.session.query(Product.category).distinct().all()]
    favorite_product_ids = set()
    if current_user.is_authenticated:
        favorite_product_ids = {
            row[0]
            for row in db.session.query(Favorite.product_id)
            .filter_by(user_id=current_user.user_id)
            .all()
        }
    return render_template(
        "main/index.html",
        products=products,
        latest=latest,
        popular=popular,
        recommendations=recommendations,
        q=query,
        category=category,
        sort=sort,
        categories=categories,
        favorite_product_ids=favorite_product_ids,
    )
