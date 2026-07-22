from functools import wraps
from pathlib import Path
from uuid import uuid4

from flask import abort, current_app, session
from flask_login import current_user

ALLOWED_IMAGE_SIGNATURES = {
    "jpg": [bytes.fromhex("ffd8ff")],
    "jpeg": [bytes.fromhex("ffd8ff")],
    "png": [bytes.fromhex("89504e470d0a1a0a")],
}


def active_account_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user.account_status != "active":
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def check_rate_limit(key, limit):
    count = session.get(key, 0)
    if count >= limit:
        abort(429)
    session[key] = count + 1


def save_validated_image(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    suffix = Path(file_storage.filename).suffix.lower().lstrip(".")
    if suffix not in ALLOWED_IMAGE_SIGNATURES:
        abort(400)
    head = file_storage.stream.read(16)
    file_storage.stream.seek(0)
    if not any(head.startswith(signature) for signature in ALLOWED_IMAGE_SIGNATURES[suffix]):
        abort(400)
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.{suffix}"
    target = upload_dir / filename
    file_storage.save(target)
    return f"uploads/{filename}"


def ensure_product_owner(product):
    if product.seller_id != current_user.user_id:
        abort(403)


def ensure_chat_participant(room):
    if current_user.user_id not in {room.buyer_id, room.seller_id}:
        abort(403)


def ensure_transaction_participant(transaction):
    if current_user.user_id not in {transaction.buyer_id, transaction.seller_id}:
        abort(403)
