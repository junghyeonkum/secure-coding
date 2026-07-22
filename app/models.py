from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(80), nullable=False)
    introduction = db.Column(db.Text, default="")
    bank_name = db.Column(db.String(80), default="")
    account_number = db.Column(db.String(120), default="")
    account_holder = db.Column(db.String(80), default="")
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    trust_score = db.Column(db.Integer, nullable=False, default=100)
    account_status = db.Column(db.String(20), nullable=False, default="active")
    report_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    products = db.relationship("Product", back_populates="seller", lazy=True)
    favorites = db.relationship(
        "Favorite",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "account_status in ('active','restricted','blocked')",
            name="ck_user_status",
        ),
    )

    def get_id(self):
        return str(self.user_id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    __tablename__ = "products"
    product_id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    product_name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(255))
    view_count = db.Column(db.Integer, nullable=False, default=0)
    product_status = db.Column(db.String(20), nullable=False, default="selling")
    report_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    seller = db.relationship("User", back_populates="products")
    transactions = db.relationship("Transaction", back_populates="product")
    favorites = db.relationship(
        "Favorite",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_product_price"),
        CheckConstraint(
            "product_status in ('selling','reserved','sold','blocked')",
            name="ck_product_status",
        ),
    )


class ProductView(db.Model):
    __tablename__ = "product_views"
    view_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.product_id", ondelete="CASCADE"),
        nullable=False,
    )
    viewed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    user = db.relationship("User")
    product = db.relationship("Product")


class ChatRoom(db.Model):
    __tablename__ = "chat_rooms"
    room_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.product_id", ondelete="CASCADE"),
        nullable=False,
    )
    buyer_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    seller_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    product = db.relationship("Product")
    buyer = db.relationship("User", foreign_keys=[buyer_id])
    seller = db.relationship("User", foreign_keys=[seller_id])
    messages = db.relationship(
        "PrivateMessage",
        back_populates="room",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "buyer_id",
            "seller_id",
            name="uq_chat_room_parties",
        ),
    )


class PrivateMessage(db.Model):
    __tablename__ = "private_messages"
    message_id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(
        db.Integer,
        db.ForeignKey("chat_rooms.room_id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    room = db.relationship("ChatRoom", back_populates="messages")
    sender = db.relationship("User")


class Transaction(db.Model):
    __tablename__ = "transactions"
    transaction_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.product_id", ondelete="RESTRICT"),
        nullable=False,
    )
    buyer_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    seller_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount = db.Column(db.Integer, nullable=False)
    transaction_status = db.Column(
        db.String(30),
        nullable=False,
        default="purchase_requested",
    )
    payment_date = db.Column(db.DateTime(timezone=True))
    shipping_deadline = db.Column(db.DateTime(timezone=True))
    confirmed_at = db.Column(db.DateTime(timezone=True))
    cancelled_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    product = db.relationship("Product", back_populates="transactions")
    buyer = db.relationship("User", foreign_keys=[buyer_id])
    seller = db.relationship("User", foreign_keys=[seller_id])
    payment = db.relationship("Payment", back_populates="transaction", uselist=False)
    delivery = db.relationship("Delivery", back_populates="transaction", uselist=False)
    review = db.relationship("Review", back_populates="transaction", uselist=False)


class Payment(db.Model):
    __tablename__ = "payments"
    payment_id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(
        db.Integer,
        db.ForeignKey("transactions.transaction_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    receiver_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount = db.Column(db.Integer, nullable=False)
    transfer_status = db.Column(db.String(30), nullable=False, default="pending")
    transfer_time = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    transaction = db.relationship("Transaction", back_populates="payment")
    sender = db.relationship("User", foreign_keys=[sender_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])

    __table_args__ = (
        CheckConstraint(
            "transfer_status in ('pending','completed','cancelled')",
            name="ck_payment_transfer_status",
        ),
    )


class Favorite(db.Model):
    __tablename__ = "favorites"
    favorite_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.product_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    user = db.relationship("User", back_populates="favorites")
    product = db.relationship("Product", back_populates="favorites")

    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_favorite_user_product"),
    )


class Delivery(db.Model):
    __tablename__ = "deliveries"
    delivery_id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(
        db.Integer,
        db.ForeignKey("transactions.transaction_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    courier = db.Column(db.String(80), nullable=False)
    tracking_number = db.Column(db.String(120), nullable=False)
    delivery_status = db.Column(db.String(30), nullable=False, default="shipping")
    shipped_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    delivered_at = db.Column(db.DateTime(timezone=True))

    transaction = db.relationship("Transaction", back_populates="delivery")


class Review(db.Model):
    __tablename__ = "reviews"
    review_id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(
        db.Integer,
        db.ForeignKey("transactions.transaction_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    reviewer_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    seller_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    rating = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    transaction = db.relationship("Transaction", back_populates="review")
    seller = db.relationship("User", foreign_keys=[seller_id])

    __table_args__ = (
        CheckConstraint("rating between 1 and 5", name="ck_review_rating"),
    )


class Report(db.Model):
    __tablename__ = "reports"
    report_id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    reported_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="CASCADE"),
    )
    reported_product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.product_id", ondelete="CASCADE"),
    )
    report_type = db.Column(db.String(30), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    report_status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    reporter = db.relationship("User", foreign_keys=[reporter_id])
    reported_user = db.relationship("User", foreign_keys=[reported_user_id])
    reported_product = db.relationship("Product", foreign_keys=[reported_product_id])

    __table_args__ = (
        CheckConstraint(
            "reported_user_id is not null or reported_product_id is not null",
            name="ck_report_target",
        ),
        CheckConstraint(
            "report_status in ('pending','reviewing','resolved','rejected')",
            name="ck_report_status",
        ),
        UniqueConstraint("reporter_id", "reported_user_id", name="uq_report_user_once"),
        UniqueConstraint(
            "reporter_id",
            "reported_product_id",
            name="uq_report_product_once",
        ),
    )


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    audit_id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="SET NULL"),
    )
    action = db.Column(db.String(80), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    report_id = db.Column(
        db.Integer,
        db.ForeignKey("reports.report_id", ondelete="SET NULL"),
    )
    reason = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    report = db.relationship("Report")
