from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms import MessageForm
from app.models import ChatRoom, PrivateMessage, Product
from app.utils.security import active_account_required, check_rate_limit, ensure_chat_participant

bp = Blueprint("chat", __name__, url_prefix="/chat")


@bp.post("/start/<int:product_id>")
@login_required
@active_account_required
def start(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    if product.seller_id == current_user.user_id or product.product_status != "selling":
        abort(400)
    chat_room = ChatRoom.query.filter_by(
        product_id=product.product_id,
        buyer_id=current_user.user_id,
        seller_id=product.seller_id,
    ).first()
    if not chat_room:
        chat_room = ChatRoom(
            product_id=product.product_id,
            buyer_id=current_user.user_id,
            seller_id=product.seller_id,
        )
        db.session.add(chat_room)
        db.session.commit()
    return redirect(url_for("chat.room", room_id=chat_room.room_id))


@bp.route("/rooms/<int:room_id>", methods=["GET", "POST"])
@login_required
def room(room_id):
    chat_room = db.session.get(ChatRoom, room_id) or abort(404)
    ensure_chat_participant(chat_room)
    form = MessageForm()
    if form.validate_on_submit():
        if current_user.account_status != "active":
            abort(403)
        check_rate_limit("chat_messages", 20)
        db.session.add(
            PrivateMessage(
                room_id=chat_room.room_id,
                sender_id=current_user.user_id,
                content=form.content.data,
            )
        )
        db.session.commit()
        flash("메시지를 보냈습니다.")
        return redirect(url_for("chat.room", room_id=chat_room.room_id))
    messages = (
        PrivateMessage.query.filter_by(room_id=chat_room.room_id)
        .order_by(PrivateMessage.created_at.asc())
        .all()
    )
    return render_template("chat/room.html", room=chat_room, messages=messages, form=form)
