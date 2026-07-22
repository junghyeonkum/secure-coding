from sqlite3 import Connection as SQLite3Connection

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import current_user, logout_user
from sqlalchemy import event
from sqlalchemy.engine import Engine

from .config import Config
from .extensions import csrf, db, login_manager
from .models import User


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, _connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app(config_object=None):
    app = Flask(__name__)
    app.config.from_object(config_object or Config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "로그인이 필요합니다."

    from .routes.auth import bp as auth_bp  # pylint: disable=import-outside-toplevel
    from .routes.admin import bp as admin_bp  # pylint: disable=import-outside-toplevel
    from .routes.chat import bp as chat_bp  # pylint: disable=import-outside-toplevel
    from .routes.favorites import bp as favorites_bp  # pylint: disable=import-outside-toplevel
    from .routes.main import bp as main_bp  # pylint: disable=import-outside-toplevel
    from .routes.products import bp as products_bp  # pylint: disable=import-outside-toplevel
    from .routes.reports import bp as reports_bp  # pylint: disable=import-outside-toplevel
    from .routes.transactions import bp as transactions_bp  # pylint: disable=import-outside-toplevel
    from .routes.users import bp as users_bp  # pylint: disable=import-outside-toplevel

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(favorites_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(reports_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.before_request
    def logout_blocked_users():
        if (
            current_user.is_authenticated
            and current_user.account_status == "blocked"
            and request.endpoint not in {"auth.login", "auth.logout", "static"}
        ):
            logout_user()
            flash("차단된 계정입니다.")
            return redirect(url_for("auth.login"))
        return None

    @app.after_request
    def add_security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.context_processor
    def status_labels():
        transaction_labels = {
            "purchase_requested": "구매 요청",
            "payment_pending": "송금 대기",
            "preparing_shipment": "배송 준비",
            "shipping": "배송 중",
            "delivered": "배송 완료",
            "purchase_confirmed": "구매 확정",
            "completed": "거래 완료",
            "cancelled": "취소",
            "refund_requested": "환불 요청",
            "refunded": "환불 완료",
            "disputed": "분쟁",
        }
        transfer_labels = {
            "pending": "송금 대기",
            "completed": "송금 완료",
        }
        delivery_labels = {
            "shipping": "배송 중",
            "delivered": "배송 완료",
        }
        product_labels = {
            "selling": "판매 중",
            "reserved": "거래 진행 중",
            "sold": "품절",
            "blocked": "판매 중지",
        }
        return {
            "transaction_status_label": lambda status: transaction_labels.get(status, status),
            "payment_status_label": lambda status: transfer_labels.get(status, status),
            "delivery_status_label": lambda status: delivery_labels.get(status, status),
            "product_status_label": lambda status: product_labels.get(status, status),
        }

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    return app
