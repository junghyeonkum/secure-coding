import re

from app import create_app
from app.extensions import db
from app.models import AuditLog, Product, Report, User
from tests.conftest import TestConfig, create_product, create_user, login


def create_admin():
    admin = User(username="admin", nickname="admin", is_admin=True)
    admin.set_password("Admin1234!")
    db.session.add(admin)
    db.session.commit()
    return admin


def create_user_report(reporter, reported_user):
    report = Report(
        reporter_id=reporter.user_id,
        reported_user_id=reported_user.user_id,
        report_type="user",
        reason="bad user",
    )
    reported_user.report_count += 1
    db.session.add(report)
    db.session.commit()
    return report


def create_product_report(reporter, product):
    report = Report(
        reporter_id=reporter.user_id,
        reported_product_id=product.product_id,
        report_type="product",
        reason="bad product",
    )
    product.report_count += 1
    db.session.add(report)
    db.session.commit()
    return report


def admin_action(client, report_id, action, reason="admin reason"):
    return client.post(
        f"/admin/reports/{report_id}/action",
        data={"action": action, "reason": reason},
        follow_redirects=True,
    )


def user_status_action(client, user_id, status, reason="status reason"):
    return client.post(
        f"/admin/users/{user_id}/status",
        data={"account_status": status, "reason": reason},
        follow_redirects=True,
    )


def test_regular_user_cannot_access_admin(client, app):
    with app.app_context():
        create_user("user")
    login(client, "user")
    assert client.get("/admin/").status_code == 403


def test_admin_can_access_dashboard(client, app):
    with app.app_context():
        create_admin()
    login(client, "admin", "Admin1234!")
    response = client.get("/admin/")
    assert response.status_code == 200
    assert "관리자 대시보드".encode() in response.data


def test_admin_restricts_user(client, app):
    with app.app_context():
        create_admin()
        reporter = create_user("reporter")
        target = create_user("target")
        report = create_user_report(reporter, target)
        report_id = report.report_id
        target_id = target.user_id
    login(client, "admin", "Admin1234!")
    response = admin_action(client, report_id, "restrict_user")
    assert response.status_code == 200
    with app.app_context():
        assert db.session.get(User, target_id).account_status == "restricted"


def test_regular_user_cannot_change_user_status(client, app):
    with app.app_context():
        create_user("regular")
        target = create_user("target")
        target_id = target.user_id
    login(client, "regular")
    response = client.post(
        f"/admin/users/{target_id}/status",
        data={"account_status": "restricted", "reason": "bad user"},
    )
    assert response.status_code == 403


def test_admin_user_management_page_shows_report_counts(client, app):
    with app.app_context():
        create_admin()
        target = create_user("target")
        target.report_count = 3
        db.session.commit()
    login(client, "admin", "Admin1234!")
    response = client.get("/admin/users")
    assert response.status_code == 200
    assert "target".encode() in response.data
    assert "제재 검토".encode() in response.data


def test_admin_changes_user_status_to_restricted(client, app):
    with app.app_context():
        create_admin()
        target = create_user("target")
        target_id = target.user_id
    login(client, "admin", "Admin1234!")
    response = user_status_action(client, target_id, "restricted", "review required")
    assert response.status_code == 200
    with app.app_context():
        assert db.session.get(User, target_id).account_status == "restricted"


def test_admin_changes_user_status_to_blocked_and_login_is_blocked(client, app):
    with app.app_context():
        create_admin()
        target = create_user("target")
        target_id = target.user_id
    login(client, "admin", "Admin1234!")
    response = user_status_action(client, target_id, "blocked", "severe abuse")
    assert response.status_code == 200
    client.post("/auth/logout")
    response = client.post("/auth/login", data={"username": "target", "password": "Password1!"})
    assert response.status_code == 401


def test_blocked_user_cannot_login(client, app):
    with app.app_context():
        create_admin()
        reporter = create_user("reporter")
        target = create_user("target")
        report = create_user_report(reporter, target)
        report_id = report.report_id
    login(client, "admin", "Admin1234!")
    admin_action(client, report_id, "block_user")
    client.post("/auth/logout")
    response = client.post("/auth/login", data={"username": "target", "password": "Password1!"})
    assert response.status_code == 401


def test_restricted_user_major_actions_blocked(client, app):
    with app.app_context():
        seller = create_user("seller")
        restricted = create_user("restricted")
        restricted.account_status = "restricted"
        product = create_product(seller)
        product_id = product.product_id
        seller_id = seller.user_id
    login(client, "restricted")
    assert client.post("/products/new", data={"product_name": "x"}).status_code == 403
    assert client.post(f"/transactions/buy/{product_id}").status_code == 403
    assert client.post(f"/chat/start/{product_id}").status_code == 403
    assert client.post(
        "/reports/new",
        data={
            "report_type": "fraud",
            "reported_product_id": product_id,
            "seller_id": seller_id,
            "reason": "악성 상품 신고입니다.",
        },
    ).status_code == 403


def test_restricted_user_blocked_until_admin_activates(client, app):
    with app.app_context():
        create_admin()
        seller = create_user("seller")
        target = create_user("target")
        product = create_product(seller)
        target_id = target.user_id
        product_id = product.product_id

    login(client, "admin", "Admin1234!")
    user_status_action(client, target_id, "restricted")
    client.post("/auth/logout")

    login(client, "target")
    assert client.post("/products/new", data={"product_name": "x"}).status_code == 403
    assert client.post(f"/transactions/buy/{product_id}").status_code == 403
    client.post("/auth/logout")

    login(client, "admin", "Admin1234!")
    user_status_action(client, target_id, "active")
    client.post("/auth/logout")

    login(client, "target")
    assert client.post(f"/transactions/buy/{product_id}").status_code == 302


def test_blocked_product_excluded_from_listing(client, app):
    with app.app_context():
        create_admin()
        reporter = create_user("reporter")
        seller = create_user("seller")
        product = create_product(seller, name="blocked product")
        report = create_product_report(reporter, product)
        report_id = report.report_id
        product_id = product.product_id
    login(client, "admin", "Admin1234!")
    admin_action(client, report_id, "block_product")
    response = client.get("/products/")
    assert b"blocked product" not in response.data
    with app.app_context():
        assert db.session.get(Product, product_id).product_status == "blocked"


def test_admin_approves_and_rejects_reports(client, app):
    with app.app_context():
        create_admin()
        reporter = create_user("reporter")
        first_target = create_user("first_target")
        second_target = create_user("second_target")
        approve_report = create_user_report(reporter, first_target)
        reject_report = create_user_report(reporter, second_target)
        approve_id = approve_report.report_id
        reject_id = reject_report.report_id
    login(client, "admin", "Admin1234!")
    admin_action(client, approve_id, "approve")
    admin_action(client, reject_id, "reject")
    with app.app_context():
        assert db.session.get(Report, approve_id).report_status == "resolved"
        assert db.session.get(Report, reject_id).report_status == "rejected"


def test_admin_action_without_csrf_blocked():
    class CsrfConfig(TestConfig):
        WTF_CSRF_ENABLED = True

    app = create_app(CsrfConfig)
    with app.app_context():
        db.create_all()
        create_admin()
        reporter = create_user("reporter")
        target = create_user("target")
        report = create_user_report(reporter, target)
        report_id = report.report_id
    client = app.test_client()
    login_page = client.get("/auth/login")
    token = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', login_page.data).group(1).decode()
    client.post("/auth/login", data={"csrf_token": token, "username": "admin", "password": "Admin1234!"})
    response = client.post(f"/admin/reports/{report_id}/action", data={"action": "restrict_user"})
    assert response.status_code == 400


def test_admin_action_audit_log_saved(client, app):
    with app.app_context():
        create_admin()
        reporter = create_user("reporter")
        target = create_user("target")
        report = create_user_report(reporter, target)
        report_id = report.report_id
        target_id = target.user_id
    login(client, "admin", "Admin1234!")
    admin_action(client, report_id, "restrict_user", reason="policy violation")
    with app.app_context():
        audit = AuditLog.query.filter_by(action="user:restrict", target_type="user", target_id=target_id).first()
        assert audit is not None
        assert audit.report_id == report_id
        assert audit.reason == "policy violation"


def test_user_status_action_audit_log_saved(client, app):
    with app.app_context():
        create_admin()
        target = create_user("target")
        target_id = target.user_id
    login(client, "admin", "Admin1234!")
    user_status_action(client, target_id, "restricted", reason="multiple reports")
    with app.app_context():
        audit = AuditLog.query.filter_by(
            action="user:status:active->restricted",
            target_type="user",
            target_id=target_id,
        ).first()
        assert audit is not None
        assert audit.reason == "multiple reports"
