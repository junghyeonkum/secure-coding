# 시큐어 중고거래 Flask 애플리케이션

Flask, SQLite, Flask-SQLAlchemy, Flask-Login, Flask-WTF로 만든 중고거래 예제입니다. 상품 등록, 1:1 채팅, 사용자 간 송금 확인, 배송 등록, 구매 확정, 리뷰, 신고, 관심상품 기능을 제공합니다.

## 설치 및 실행

### 요구사항

- Python 3.11 이상
- Git

프로젝트를 내려받습니다.

```bash
git clone https://github.com/junghyeonkum/secure-coding.git
cd secure-coding
```

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env

$env:FLASK_APP="manage.py"
flask init-db
flask seed
flask run
```

또는 최신 Flask 실행 형식으로 다음 명령을 사용할 수 있습니다.

```powershell
flask --app manage run
```

PowerShell에서 가상환경 활성화가 차단되면 다음 명령어를 먼저 실행합니다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Windows CMD

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
copy .env.example .env

set FLASK_APP=manage.py
flask init-db
flask seed
flask run
```

또는 최신 Flask 실행 형식으로 다음 명령을 사용할 수 있습니다.

```cmd
flask --app manage run
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

export FLASK_APP=manage.py
flask init-db
flask seed
flask run
```

또는 최신 Flask 실행 형식으로 다음 명령을 사용할 수 있습니다.

```bash
flask --app manage run
```

실행 후 브라우저에서 다음 주소로 접속합니다.

```text
http://127.0.0.1:5000
```

개발 환경에서 HTTPS를 테스트하려면 다음처럼 adhoc SSL을 켜고 직접 실행합니다.

```powershell
$env:FLASK_ADHOC_SSL="true"
python manage.py
```

이 경우 다음 주소로 접속합니다.

```text
https://127.0.0.1:5000
```

`.env`에서는 `SECRET_KEY`, 업로드 경로, 세션 쿠키 설정을 관리합니다. 기본 개발 환경에서는 복사한 설정 그대로 실행할 수 있습니다.

`flask init-db`와 `flask seed`는 최초 실행 시에만 필요합니다. 이후에는 가상환경을 활성화한 뒤 `flask run`만 실행하면 됩니다.

## 초기 계정

| 역할 | 아이디 | 비밀번호 |
|---|---|---|
| 판매자 | `seller` | `Password1!` |
| 구매자 | `buyer` | `Password1!` |
| 관리자 | `admin` | `Admin1234!` |

초기 계정은 개발 및 테스트용입니다. 관리자 계정 정보는 `flask seed` 실행 전에 환경변수로 변경할 수 있습니다.

```powershell
$env:ADMIN_USERNAME="admin"
$env:ADMIN_PASSWORD="ChangeMe1234!"
flask seed
```

관리자 로그인 후 `/admin`에서 대시보드와 신고 관리 페이지를 사용할 수 있습니다.

## 사용자 간 송금 흐름

이 프로젝트는 실제 은행 송금이나 자동 결제를 실행하지 않습니다. 구매자는 화면에 표시된 판매자 계좌 정보를 확인하고 직접 송금한 뒤, 앱에서 송금 완료 버튼을 눌러 거래 상태를 갱신합니다.

1. 상품 상세에서 `구매하기`를 누르면 거래와 송금 기록이 생성됩니다.
2. 구매자는 송금 안내 페이지에서 상품명, 금액, 판매자 닉네임, 은행명, 계좌번호, 예금주를 확인합니다.
3. 화면에는 “판매자 계좌로 송금한 후 송금 완료 버튼을 눌러주세요.” 문구가 표시됩니다.
4. 구매자가 `송금 완료`를 누르면 서버가 `payments.transfer_status=completed`, `payments.transfer_time`을 저장합니다.
5. 거래 상태는 `preparing_shipment`로 변경됩니다.
6. 동일 거래의 송금 완료 처리는 중복 실행할 수 없습니다.
7. 판매자는 송금 완료된 거래에 대해서만 운송장을 등록할 수 있습니다.

판매자 계좌 정보는 마이페이지에서 `은행명`, `계좌번호`, `예금주`로 관리합니다.

## 관심상품

- 상품 카드와 상품 상세에 하트 버튼이 표시됩니다.
- 로그인 사용자가 하트를 누르면 관심상품 추가/삭제가 토글됩니다.
- 비로그인 사용자가 하트를 누르면 로그인 페이지로 이동합니다.
- 마이페이지와 상단 메뉴에서 `관심상품` 페이지로 이동할 수 있습니다.
- 관심상품 목록은 최신 등록순으로 표시됩니다.
- 판매 완료 또는 차단된 상품도 관심상품 목록에 표시되며 상태가 함께 보입니다.
- 상품이 삭제되면 연결된 관심상품 기록도 함께 삭제됩니다.

## 데이터베이스 스키마 변경

이번 버전에서 `users`, `payments`, `favorites`, `audit_logs` 스키마가 변경되었습니다. 기존 개발 DB를 보존하려면 먼저 백업하세요.

```powershell
Copy-Item .\secure_market.db ".\secure_market.backup.$(Get-Date -Format yyyyMMddHHmmss).db"
```

개발 환경에서 가장 단순한 초기화 방법:

```powershell
Remove-Item .\secure_market.db
$env:FLASK_APP="manage.py"
flask init-db
flask seed
```

운영 데이터가 있는 환경에서는 위 초기화 방식을 사용하지 말고, `users` 계좌 컬럼 추가, `payments` 재생성 또는 데이터 변환, `favorites` 생성 마이그레이션을 별도로 작성해야 합니다.

상태 불일치 점검 및 보정:

```powershell
$env:FLASK_APP="manage.py"
flask reconcile-statuses
```

이 명령은 송금 완료된 거래의 상품이 아직 `selling`이면 `sold`로 변경합니다. 반대로 송금 완료되지 않은 거래 때문에 `sold`가 된 상품은 자동으로 되돌리지 않고 검토 목록으로 출력합니다.

## 보안 점검

```powershell
pytest
pytest tests/test_admin.py
bandit -r .
pylint app
pip-audit
```

## 최소 관리자 기능

- `/admin`: 처리 대기 신고, 제한 사용자, 차단 사용자, 차단 상품 수 확인
- `/admin/reports`: 신고 목록 확인
- `/admin/reports/<id>`: 신고 상세 및 관리자 조치

관리자 조치:

- 신고 검토 중 변경, 승인, 기각
- 신고된 사용자 이용 제한, 차단, 차단 해제
- 신고된 상품 차단, 차단 해제

관리자 조치는 모두 POST 요청과 CSRF 토큰 검사를 사용합니다. 조치 내용은 `audit_logs`에 관리자 ID, 대상 ID, 조치, 신고 ID, 처리 시각, 관리자 입력 사유와 함께 저장됩니다.

## 주요 구조

- `app/models.py`: 테이블, 관계, 제약조건
- `app/routes/`: 기능별 Blueprint
- `app/services/transaction.py`: 거래 상태 전환, 송금 완료, 배송, 구매 확정, 리뷰 처리
- `app/utils/security.py`: 권한 검사, 업로드 검증
- `tests/`: 기능 및 보안 테스트
