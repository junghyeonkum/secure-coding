from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms import ProfileForm
from app.models import ChatRoom, Product, Transaction, User

bp = Blueprint("users", __name__, url_prefix="/users")


@bp.route("/<int:user_id>")
def profile(user_id):
    user = db.session.get(User, user_id) or abort(404)
    products = Product.query.filter_by(seller_id=user.user_id, product_status="selling").all()
    return render_template("users/profile.html", user=user, products=products)


@bp.route("/mypage", methods=["GET", "POST"])
@login_required
def mypage():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.nickname = form.nickname.data
        current_user.introduction = form.introduction.data or ""
        current_user.bank_name = form.bank_name.data or ""
        current_user.account_number = form.account_number.data or ""
        current_user.account_holder = form.account_holder.data or ""
        db.session.commit()
        flash("회원정보가 수정되었습니다.")
        return redirect(url_for("users.mypage"))
    selling = Product.query.filter_by(seller_id=current_user.user_id).all()
    purchases = Transaction.query.filter_by(buyer_id=current_user.user_id).all()
    sales = Transaction.query.filter_by(seller_id=current_user.user_id).all()
    buying_rooms = (
        ChatRoom.query.filter_by(buyer_id=current_user.user_id)
        .order_by(ChatRoom.created_at.desc())
        .all()
    )
    selling_rooms = (
        ChatRoom.query.filter_by(seller_id=current_user.user_id)
        .order_by(ChatRoom.created_at.desc())
        .all()
    )
    return render_template(
        "users/mypage.html",
        form=form,
        selling=selling,
        purchases=purchases,
        sales=sales,
        buying_rooms=buying_rooms,
        selling_rooms=selling_rooms,
    )
