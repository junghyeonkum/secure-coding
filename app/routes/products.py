from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms import ProductForm
from app.models import Favorite, Product, ProductView, Transaction
from app.utils.security import (
    active_account_required,
    ensure_product_owner,
    save_validated_image,
)

bp = Blueprint("products", __name__, url_prefix="/products")


@bp.route("/")
def list_products():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    sort = request.args.get("sort", "latest")
    query = Product.query.filter_by(product_status="selling")
    if q:
        query = query.filter(Product.product_name.contains(q))
    if category:
        query = query.filter_by(category=category)
    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "views":
        query = query.order_by(Product.view_count.desc())
    else:
        query = query.order_by(Product.created_at.desc())
    categories = [row[0] for row in db.session.query(Product.category).distinct().all()]
    products = query.all()
    favorite_product_ids = set()
    if current_user.is_authenticated:
        favorite_product_ids = {
            row[0]
            for row in db.session.query(Favorite.product_id)
            .filter_by(user_id=current_user.user_id)
            .all()
        }
    return render_template(
        "products/list.html",
        products=products,
        q=q,
        category=category,
        sort=sort,
        categories=categories,
        favorite_product_ids=favorite_product_ids,
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
@active_account_required
def create():
    form = ProductForm()
    if form.validate_on_submit():
        image_path = save_validated_image(form.image.data)
        product = Product(
            seller_id=current_user.user_id,
            product_name=form.product_name.data,
            category=form.category.data,
            price=form.price.data,
            description=form.description.data,
            image_path=image_path,
        )
        db.session.add(product)
        db.session.commit()
        flash("상품이 등록되었습니다.")
        return redirect(url_for("products.detail", product_id=product.product_id))
    return render_template("products/form.html", form=form, title="상품 등록")


@bp.route("/<int:product_id>")
def detail(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    if product.product_status == "blocked" and (
        not current_user.is_authenticated
        or (current_user.user_id != product.seller_id and not current_user.is_admin)
    ):
        abort(404)
    product.view_count += 1
    if current_user.is_authenticated:
        db.session.add(ProductView(user_id=current_user.user_id, product_id=product.product_id))
    db.session.commit()
    is_favorite = False
    if current_user.is_authenticated:
        is_favorite = (
            Favorite.query.filter_by(
                user_id=current_user.user_id,
                product_id=product.product_id,
            ).first()
            is not None
        )
    return render_template("products/detail.html", product=product, is_favorite=is_favorite)


@bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
@active_account_required
def edit(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    ensure_product_owner(product)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        product.product_name = form.product_name.data
        product.category = form.category.data
        product.price = form.price.data
        product.description = form.description.data
        image_path = save_validated_image(form.image.data)
        if image_path:
            product.image_path = image_path
        db.session.commit()
        flash("상품이 수정되었습니다.")
        return redirect(url_for("products.detail", product_id=product.product_id))
    return render_template("products/form.html", form=form, title="상품 수정")


@bp.post("/<int:product_id>/delete")
@login_required
def delete(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    ensure_product_owner(product)
    active_transaction = Transaction.query.filter(
        Transaction.product_id == product.product_id,
        Transaction.transaction_status != "cancelled",
    ).first()
    if active_transaction:
        abort(400)
    db.session.delete(product)
    db.session.commit()
    flash("상품이 삭제되었습니다.")
    return redirect(url_for("products.list_products"))
