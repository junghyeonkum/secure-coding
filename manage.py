import os

from app import create_app
from app.extensions import db
from app.models import Payment, Product, Transaction, User


app = create_app()


@app.cli.command("init-db")
def init_db():
    db.create_all()
    print("데이터베이스 테이블을 생성했습니다.")


@app.cli.command("seed")
def seed():
    db.create_all()
    if User.query.filter_by(username="seller").first():
        print("초기 데이터가 이미 있습니다.")
        return

    seller = User(
        username="seller",
        nickname="판매자",
        bank_name="테스트은행",
        account_number="123-456-7890",
        account_holder="판매자",
    )
    seller.set_password("Password1!")
    buyer = User(username="buyer", nickname="구매자")
    buyer.set_password("Password1!")
    admin = User(
        username=os.environ.get("ADMIN_USERNAME", "admin"),
        nickname="관리자",
        is_admin=True,
    )
    admin.set_password(os.environ.get("ADMIN_PASSWORD", "Admin1234!"))
    db.session.add_all([seller, buyer, admin])
    db.session.flush()
    db.session.add_all(
        [
            Product(
                seller_id=seller.user_id,
                product_name="보안 입문서",
                category="도서",
                price=12000,
                description="깨끗한 중고 도서입니다.",
            ),
            Product(
                seller_id=seller.user_id,
                product_name="무선 키보드",
                category="전자기기",
                price=25000,
                description="정상 동작합니다.",
            ),
        ]
    )
    db.session.commit()
    print("테스트용 초기 데이터를 추가했습니다. seller/buyer 비밀번호: Password1!")


@app.cli.command("reconcile-statuses")
def reconcile_statuses():
    fixed = []
    review = []

    completed_transfers = (
        Transaction.query.join(Payment)
        .join(Product)
        .filter(Payment.transfer_status == "completed", Product.product_status == "selling")
        .all()
    )
    for transaction in completed_transfers:
        transaction.product.product_status = "sold"
        fixed.append((transaction.transaction_id, transaction.product_id, transaction.product.product_name))

    suspicious_sold = (
        Transaction.query.join(Payment)
        .join(Product)
        .filter(Product.product_status == "sold", Payment.transfer_status != "completed")
        .all()
    )
    for transaction in suspicious_sold:
        review.append((transaction.transaction_id, transaction.product_id, transaction.product.product_name, payment_status(transaction)))

    db.session.commit()
    print(f"fixed_completed_transfers={len(fixed)}")
    for row in fixed:
        print(f"fixed transaction_id={row[0]} product_id={row[1]} product_name={row[2]}")
    print(f"review_required={len(review)}")
    for row in review:
        print(f"review transaction_id={row[0]} product_id={row[1]} product_name={row[2]} transfer_status={row[3]}")


def payment_status(transaction):
    return transaction.payment.transfer_status if transaction.payment else "missing"


if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"], ssl_context=app.config["SSL_CONTEXT"])
