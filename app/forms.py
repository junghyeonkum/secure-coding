from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileSize
from wtforms import FileField, IntegerField, PasswordField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Regexp


class RegisterForm(FlaskForm):
    username = StringField(
        "아이디",
        validators=[
            DataRequired(),
            Length(min=4, max=40),
            Regexp(r"^[A-Za-z0-9_]+$"),
        ],
    )
    password = PasswordField(
        "비밀번호",
        validators=[
            DataRequired(),
            Length(min=8, max=128),
            Regexp(
                r"^(?=.*[A-Za-z])(?=.*\d).+$",
                message="비밀번호는 영문과 숫자를 포함해야 합니다.",
            ),
        ],
    )
    nickname = StringField("닉네임", validators=[DataRequired(), Length(min=2, max=40)])


class LoginForm(FlaskForm):
    username = StringField("아이디", validators=[DataRequired(), Length(max=40)])
    password = PasswordField("비밀번호", validators=[DataRequired(), Length(max=128)])


class ProfileForm(FlaskForm):
    nickname = StringField("닉네임", validators=[DataRequired(), Length(min=2, max=40)])
    introduction = TextAreaField("소개글", validators=[Optional(), Length(max=1000)])
    bank_name = StringField("은행명", validators=[Optional(), Length(max=80)])
    account_number = StringField("계좌번호", validators=[Optional(), Length(max=120)])
    account_holder = StringField("예금주", validators=[Optional(), Length(max=80)])


class ProductForm(FlaskForm):
    CATEGORY_CHOICES = [
        ("전자기기", "전자기기"),
        ("의류", "의류"),
        ("도서", "도서"),
        ("생활용품", "생활용품"),
        ("스포츠", "스포츠"),
        ("기타", "기타"),
    ]

    product_name = StringField("상품명", validators=[DataRequired(), Length(max=120)])
    category = SelectField(
        "카테고리",
        choices=CATEGORY_CHOICES,
        validators=[DataRequired(), Length(max=50)],
    )
    price = IntegerField(
        "가격",
        validators=[DataRequired(), NumberRange(min=0, max=100000000)],
    )
    description = TextAreaField("설명", validators=[DataRequired(), Length(max=3000)])
    image = FileField(
        "상품 이미지",
        validators=[
            Optional(),
            FileAllowed(["jpg", "jpeg", "png"], "jpg, jpeg, png만 허용됩니다."),
            FileSize(max_size=2 * 1024 * 1024),
        ],
    )


class MessageForm(FlaskForm):
    content = TextAreaField("메시지", validators=[DataRequired(), Length(max=1000)])


class DeliveryForm(FlaskForm):
    courier = StringField("택배사", validators=[DataRequired(), Length(max=80)])
    tracking_number = StringField(
        "운송장 번호",
        validators=[DataRequired(), Length(max=120)],
    )


class ReviewForm(FlaskForm):
    rating = SelectField(
        "평점",
        choices=[(str(i), str(i)) for i in range(1, 6)],
        validators=[DataRequired()],
    )
    content = TextAreaField("내용", validators=[DataRequired(), Length(max=1000)])


class ReportForm(FlaskForm):
    report_type = SelectField(
        "신고 유형",
        choices=[
            ("fraud", "사기 의심"),
            ("fake_product", "허위 상품"),
            ("abuse", "욕설 및 비방"),
            ("inappropriate", "부적절한 콘텐츠"),
            ("other", "기타"),
        ],
        validators=[DataRequired()],
    )
    reported_user_id = IntegerField("사용자 ID", validators=[Optional()])
    reported_product_id = IntegerField("상품 ID", validators=[Optional()])
    reason = TextAreaField(
        "신고 사유",
        validators=[DataRequired(), Length(min=10, max=1000)],
    )
