from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import login_user, logout_user

from app.extensions import db
from app.forms import LoginForm, RegisterForm
from app.models import User
from app.utils.security import check_rate_limit

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash("이미 사용 중인 아이디입니다.")
            return render_template("auth/register.html", form=form), 400
        user = User(username=form.username.data, nickname=form.nickname.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("회원가입이 완료되었습니다.")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@bp.route("/check-username")
def check_username():
    username = request.args.get("username", "")
    available = bool(username) and User.query.filter_by(username=username).first() is None
    return {"available": available}


@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        check_rate_limit("login_attempts", 5)
        user = User.query.filter_by(username=form.username.data).first()
        if (
            not user
            or not user.check_password(form.password.data)
            or user.account_status == "blocked"
        ):
            flash("아이디 또는 비밀번호가 올바르지 않습니다.")
            return render_template("auth/login.html", form=form), 401
        session.clear()
        session.permanent = True
        login_user(user)
        session["login_attempts"] = 0
        return redirect(url_for("main.index"))
    return render_template("auth/login.html", form=form)


@bp.post("/logout")
def logout():
    logout_user()
    session.clear()
    flash("로그아웃되었습니다.")
    return redirect(url_for("main.index"))
