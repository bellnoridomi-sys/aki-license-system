import os
import json
import secrets
import hashlib
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from functools import wraps

from flask import (
    abort, flash, redirect, render_template_string, request, session,
    url_for, jsonify
)
from markupsafe import Markup
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func, inspect


def register_aki_shop(app, License, utcnow):
    """Add the manual-payment storefront without changing existing license APIs."""
    registry = inspect(License).registry
    Base = registry.generate_base()
    class AKIShopCustomer(Base):
        __tablename__ = "aki_shop_customers"
        id = Column(Integer, primary_key=True)
        username = Column(String(32), unique=True, nullable=False)
        password_hash = Column(String(255), nullable=False)
        discord_id = Column(String(32), unique=True, nullable=True)
        discord_name = Column(String(100), nullable=True)
        created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    class AKIShopOrder(Base):
        __tablename__ = "aki_shop_orders"
        id = Column(Integer, primary_key=True)
        order_code = Column(String(20), unique=True, nullable=False, index=True)
        customer_id = Column(Integer, ForeignKey("aki_shop_customers.id"), nullable=False, index=True)
        duration_days = Column(Integer, nullable=False)
        amount_vnd = Column(Integer, nullable=False)
        status = Column(String(20), nullable=False, default="pending", index=True)
        payment_ref = Column(String(120), nullable=True)
        created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
        reported_at = Column(DateTime(timezone=True), nullable=True)
        paid_at = Column(DateTime(timezone=True), nullable=True)
        license_id = Column(Integer, ForeignKey("licenses.id"), nullable=True)
        issued_key = Column(Text, nullable=True)
        discord_dm_status = Column(String(32), nullable=True)

    with app.app_context():
        Base.metadata.create_all(bind=License.query.session.get_bind())

    def _db_session():
        # Resolve Flask-SQLAlchemy's scoped session for the current request context.
        return License.query.session

    plans = {
        "7d": {"days": 7, "price": 5000, "name": "7 ngày"},
        "10d": {"days": 10, "price": 20000, "name": "10 ngày"},
        "forever": {"days": 0, "price": 80000, "name": "Vĩnh viễn"},
    }
    qr_page_url = "https://ibb.co/Ps7bJrJ8"
    qr_image_url = os.environ.get("AKI_PAYMENT_QR_IMAGE_URL", "").strip()

    BASE = """
<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }} · AKI DEV</title>
<style>
:root{color-scheme:dark;font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;color:#f4f4f2;background:#080808}
a{color:inherit;text-decoration:none}
button,input{font:inherit}
.aki-shop-shell{width:min(1080px,calc(100% - 32px));margin:0 auto;padding:28px 0 64px}
.aki-shop-nav{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:30px}
.aki-shop-brand{font-size:16px;font-weight:800;letter-spacing:.13em}
.aki-shop-brand small{display:block;color:#92928c;font-weight:500;font-size:10px;letter-spacing:.2em;margin-top:4px}
.aki-shop-navlinks{display:flex;gap:9px;align-items:center;flex-wrap:wrap}
.aki-shop-btn,.aki-shop-link{display:inline-flex;justify-content:center;align-items:center;gap:8px;border:1px solid rgba(255,255,255,.14);background:rgba(255,255,255,.07);color:#fff;border-radius:999px;padding:11px 17px;font-weight:650;cursor:pointer;transition:.2s}
.aki-shop-btn:hover,.aki-shop-link:hover{background:rgba(255,255,255,.14);transform:translateY(-1px)}
.aki-shop-btn.primary{background:#f0f0eb;color:#111;border-color:#f0f0eb}
.aki-shop-btn.danger{border-color:rgba(255,110,110,.3);color:#ffbaba}
.aki-shop-hero{padding:30px 0 24px}
.aki-shop-eyebrow{color:#aaa;font-size:11px;letter-spacing:.22em;text-transform:uppercase}
.aki-shop-h1{font-size:clamp(32px,6vw,56px);line-height:1.02;letter-spacing:-.055em;margin:13px 0}
.aki-shop-muted{color:#aaa;line-height:1.65}
.aki-shop-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:22px}
.aki-shop-card,.aki-shop-panel{border:1px solid rgba(255,255,255,.13);background:rgba(255,255,255,.055);backdrop-filter:blur(22px);-webkit-backdrop-filter:blur(22px);border-radius:24px;padding:22px;box-shadow:0 18px 50px rgba(0,0,0,.24)}
.aki-shop-card h3{font-size:15px;margin:0 0 12px;color:#bbb}
.aki-shop-price{font-size:34px;font-weight:800;letter-spacing:-.04em;margin:5px 0 15px}
.aki-shop-card p{color:#999;font-size:13px;min-height:38px;line-height:1.55}
.aki-shop-card form{margin-top:18px}
.aki-shop-panel{max-width:680px;margin:24px auto}
.aki-shop-panel h1{font-size:29px;letter-spacing:-.04em;margin:0 0 8px}
.aki-shop-field{display:grid;gap:7px;margin:14px 0}
.aki-shop-field label{font-size:13px;color:#bbb}
.aki-shop-field input{width:100%;border:1px solid rgba(255,255,255,.15);border-radius:14px;background:rgba(0,0,0,.25);color:#fff;padding:13px 14px;outline:none}
.aki-shop-field input:focus{border-color:rgba(255,255,255,.45)}
.aki-shop-table{width:100%;border-collapse:collapse;margin-top:16px}
.aki-shop-table th,.aki-shop-table td{text-align:left;padding:13px 10px;border-bottom:1px solid rgba(255,255,255,.09);font-size:13px;vertical-align:middle}
.aki-shop-table th{color:#999;font-weight:600}
.aki-shop-pill{display:inline-block;border:1px solid rgba(255,255,255,.14);border-radius:99px;padding:5px 10px;color:#ddd;font-size:11px;white-space:nowrap}
.aki-shop-pill.good{border-color:rgba(150,220,170,.35);color:#b9edc7}
.aki-shop-pill.wait{border-color:rgba(230,200,130,.32);color:#e8d29e}
.aki-shop-qr{padding:22px;text-align:center;border:1px dashed rgba(255,255,255,.25);border-radius:20px;margin:18px 0;background:rgba(0,0,0,.18)}
.aki-shop-qrmark{width:112px;height:112px;border:1px solid rgba(255,255,255,.18);border-radius:16px;margin:0 auto 14px;display:grid;place-items:center;font-size:12px;color:#aaa;background:repeating-linear-gradient(45deg,rgba(255,255,255,.05) 0 5px,transparent 5px 10px)}
.aki-shop-key{font-family:ui-monospace,monospace;word-break:break-all;padding:16px;border:1px solid rgba(255,255,255,.16);border-radius:15px;background:rgba(0,0,0,.32);font-size:16px;margin:14px 0}
.aki-shop-flash{padding:12px 15px;border:1px solid rgba(255,255,255,.14);border-radius:14px;margin:12px 0;background:rgba(255,255,255,.06);color:#ddd}
.aki-shop-footer{color:#777;text-align:center;font-size:11px;margin-top:48px}
@media(max-width:720px){.aki-shop-grid{grid-template-columns:1fr}.aki-shop-nav{align-items:flex-start;flex-direction:column}.aki-shop-panel{padding:18px}.aki-shop-table{display:block;overflow-x:auto}}
</style>
</head>
<body>
<div class="aki-shop-shell">
<nav class="aki-shop-nav">
<a class="aki-shop-brand" href="{{ url_for('aki_store_home') }}">AKI DEV<small>LICENSE STORE</small></a>
<div class="aki-shop-navlinks">
<a class="aki-shop-link" href="{{ url_for('aki_store_home') }}">Cửa hàng</a>
{% if customer %}
<a class="aki-shop-link" href="{{ url_for('aki_store_orders') }}">Đơn của tôi</a>
<a class="aki-shop-link" href="{{ url_for('aki_store_account') }}">Tài khoản</a>
<a class="aki-shop-link" href="{{ url_for('aki_store_logout') }}">Đăng xuất</a>
{% else %}
<a class="aki-shop-link" href="{{ url_for('aki_store_login') }}">Đăng nhập</a>
<a class="aki-shop-btn primary" href="{{ url_for('aki_store_register') }}">Tạo tài khoản</a>
{% endif %}
</div>
</nav>
{% with messages = get_flashed_messages() %}
{% for message in messages %}<div class="aki-shop-flash">{{ message }}</div>{% endfor %}
{% endwith %}
{{ content }}
<div class="aki-shop-footer">AKI DEV · License Store</div>
</div>
</body></html>
"""

    def _customer():
        customer_id = session.get("aki_shop_customer_id")
        if not customer_id:
            return None
        try:
            return _db_session().get(AKIShopCustomer, int(customer_id))
        except Exception:
            session.pop("aki_shop_customer_id", None)
            return None

    def _csrf():
        if not session.get("_csrf_token"):
            session["_csrf_token"] = secrets.token_urlsafe(32)
        return session["_csrf_token"]

    def _page(title, inner, **values):
        customer = _customer()
        csrf_token = _csrf()
        rendered = render_template_string(inner, csrf=csrf_token, customer=customer, **values)
        return render_template_string(BASE, title=title, content=Markup(rendered), customer=customer)

    def _owned_order(order_id, customer):
        order = _db_session().query(AKIShopOrder).filter_by(id=order_id, customer_id=customer.id).first()
        if order is None:
            abort(404)
        return order

    def _money(value):
        return f"{int(value):,}".replace(",", ".") + "đ"

    @app.before_request
    def aki_store_root_redirect():
        # Send visitors to the storefront instead of the admin login screen.
        if request.path == "/":
            return redirect(url_for("aki_store_home"))

    @app.get("/store")
    @app.get("/store/")
    def aki_store_home():
        inner = """
<section class="aki-shop-hero">
<div class="aki-shop-eyebrow">AKI DEV · LICENSE SYSTEM</div>
<h1 class="aki-shop-h1">Chọn license.<br>Nhận key sau khi duyệt.</h1>
<p class="aki-shop-muted">Chọn gói phù hợp, thanh toán bằng QR ZaloPay và gửi yêu cầu xác nhận. Key sẽ xuất hiện trong tài khoản sau khi quản trị viên kiểm tra giao dịch.</p>
</section>
<div class="aki-shop-grid">
{% for code, plan in plans.items() %}
<article class="aki-shop-card">
<h3>{{ plan.name }}</h3>
<div class="aki-shop-price">{{ money(plan.price) }}</div>
<p>{% if plan.days == 0 %}Sử dụng vĩnh viễn{% else %}Thời hạn {{ plan.days }} ngày kể từ lần kích hoạt đầu tiên{% endif %}</p>
<form method="post" action="{{ url_for('aki_store_create_order') }}">
<input type="hidden" name="_csrf" value="{{ csrf }}">
<input type="hidden" name="plan" value="{{ code }}">
<button class="aki-shop-btn primary" type="submit" style="width:100%">Mua gói này</button>
</form>
</article>
{% endfor %}
</div>
"""
        return _page("Cửa hàng", inner, plans=plans, money=_money)

    @app.get("/store/register")
    def aki_store_register():
        inner = """
<section class="aki-shop-panel">
<div class="aki-shop-eyebrow">NEW CUSTOMER</div><h1>Tạo tài khoản AKI</h1>
<p class="aki-shop-muted">Tài khoản dùng để lưu đơn hàng và license đã mua.</p>
<form method="post">
<input type="hidden" name="_csrf" value="{{ csrf }}">
<div class="aki-shop-field"><label>Tên tài khoản</label><input name="username" minlength="3" maxlength="32" autocomplete="username" required></div>
<div class="aki-shop-field"><label>Mật khẩu (tối thiểu 8 ký tự)</label><input name="password" type="password" minlength="8" autocomplete="new-password" required></div>
<button class="aki-shop-btn primary" type="submit">Tạo tài khoản</button>
<a class="aki-shop-link" href="{{ url_for('aki_store_login') }}">Đã có tài khoản?</a>
</form></section>
"""
        return _page("Tạo tài khoản", inner)

    @app.post("/store/register")
    def aki_store_register_post():
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if len(username) < 3 or len(username) > 32 or not username.replace("_", "").isalnum():
            flash("Tên tài khoản chỉ gồm chữ, số hoặc dấu gạch dưới (3–32 ký tự).")
            return redirect(url_for("aki_store_register"))
        if len(password) < 8:
            flash("Mật khẩu cần ít nhất 8 ký tự.")
            return redirect(url_for("aki_store_register"))
        if _db_session().query(AKIShopCustomer).filter(func.lower(AKIShopCustomer.username) == username.lower()).first():
            flash("Tên tài khoản đã được sử dụng.")
            return redirect(url_for("aki_store_register"))
        customer = AKIShopCustomer(username=username, password_hash=generate_password_hash(password))
        _db_session().add(customer)
        _db_session().commit()
        session.clear()
        session["aki_shop_customer_id"] = customer.id
        session["_csrf_token"] = secrets.token_urlsafe(32)
        flash("Tạo tài khoản thành công. Bro có thể chọn gói license.")
        return redirect(url_for("aki_store_home"))

    @app.get("/store/login")
    def aki_store_login():
        inner = """
<section class="aki-shop-panel">
<div class="aki-shop-eyebrow">WELCOME BACK</div><h1>Đăng nhập</h1>
<form method="post">
<input type="hidden" name="_csrf" value="{{ csrf }}">
<div class="aki-shop-field"><label>Tên tài khoản</label><input name="username" autocomplete="username" required></div>
<div class="aki-shop-field"><label>Mật khẩu</label><input name="password" type="password" autocomplete="current-password" required></div>
<button class="aki-shop-btn primary" type="submit">Đăng nhập</button>
<a class="aki-shop-link" href="{{ url_for('aki_store_register') }}">Tạo tài khoản</a>
</form></section>
"""
        return _page("Đăng nhập", inner)

    @app.post("/store/login")
    def aki_store_login_post():
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        customer = _db_session().query(AKIShopCustomer).filter(func.lower(AKIShopCustomer.username) == username.lower()).first()
        if customer is None or not check_password_hash(customer.password_hash, password):
            flash("Tên tài khoản hoặc mật khẩu không đúng.")
            return redirect(url_for("aki_store_login"))
        session.clear()
        session["aki_shop_customer_id"] = customer.id
        session["_csrf_token"] = secrets.token_urlsafe(32)
        return redirect(url_for("aki_store_home"))

    @app.get("/store/logout")
    def aki_store_logout():
        session.pop("aki_shop_customer_id", None)
        session["_csrf_token"] = secrets.token_urlsafe(32)
        flash("Đã đăng xuất.")
        return redirect(url_for("aki_store_home"))

    @app.post("/store/create-order")
    def aki_store_create_order():
        customer = _customer()
        if customer is None:
            flash("Bro đăng nhập hoặc tạo tài khoản trước khi mua key nhé.")
            return redirect(url_for("aki_store_login"))
        plan = plans.get(request.form.get("plan", ""))
        if plan is None:
            abort(400)
        code = "AKI" + secrets.token_hex(4).upper()
        order = AKIShopOrder(
            order_code=code,
            customer_id=customer.id,
            duration_days=plan["days"],
            amount_vnd=plan["price"],
            status="pending",
        )
        _db_session().add(order)
        _db_session().commit()
        return redirect(url_for("aki_store_order_detail", order_id=order.id))

    @app.get("/store/orders")
    def aki_store_orders():
        customer = _customer()
        if customer is None:
            return redirect(url_for("aki_store_login"))
        rows = _db_session().query(AKIShopOrder).filter_by(customer_id=customer.id).order_by(AKIShopOrder.created_at.desc()).all()
        labels = {"pending": "Chưa báo chuyển khoản", "reported": "Chờ admin xác nhận", "paid": "Đã thanh toán · Đã cấp key", "rejected": "Đơn bị từ chối"}
        inner = """
<section class="aki-shop-panel" style="max-width:900px">
<div class="aki-shop-eyebrow">YOUR PURCHASES</div><h1>Đơn hàng của tôi</h1>
{% if rows %}
<table class="aki-shop-table"><thead><tr><th>Mã đơn</th><th>Gói</th><th>Giá</th><th>Trạng thái</th><th></th></tr></thead><tbody>
{% for order in rows %}<tr>
<td>{{ order.order_code }}</td><td>{{ "Vĩnh viễn" if order.duration_days == 0 else order.duration_days|string + " ngày" }}</td>
<td>{{ money(order.amount_vnd) }}</td><td><span class="aki-shop-pill {{ 'good' if order.status == 'paid' else 'wait' }}">{{ labels[order.status] }}</span></td>
<td><a class="aki-shop-link" href="{{ url_for('aki_store_order_detail', order_id=order.id) }}">Chi tiết</a></td>
</tr>{% endfor %}</tbody></table>
{% else %}<p class="aki-shop-muted">Bro chưa có đơn hàng nào.</p>{% endif %}
</section>
"""
        return _page("Đơn hàng", inner, rows=rows, labels=labels, money=_money)

    @app.get("/store/orders/<int:order_id>")
    def aki_store_order_detail(order_id):
        customer = _customer()
        if customer is None:
            return redirect(url_for("aki_store_login"))
        order = _owned_order(order_id, customer)
        inner = """
<section class="aki-shop-panel">
<div class="aki-shop-eyebrow">ORDER {{ order.order_code }}</div>
<h1>{{ "Vĩnh viễn" if order.duration_days == 0 else order.duration_days|string + " ngày" }} · {{ money(order.amount_vnd) }}</h1>
<p class="aki-shop-muted">Trạng thái: <span class="aki-shop-pill {{ 'good' if order.status == 'paid' else 'wait' }}">{{ labels[order.status] }}</span></p>
{% if order.status == 'paid' and order.issued_key %}
<h3>License key của bro</h3><div class="aki-shop-key" id="aki-key">{{ order.issued_key }}</div>
<button class="aki-shop-btn primary" onclick="navigator.clipboard.writeText(document.getElementById('aki-key').innerText).then(()=>this.innerText='Đã copy')">Copy key</button>
<p class="aki-shop-muted">Key {{ "vĩnh viễn" if order.duration_days == 0 else "10 ngày" if order.duration_days == 10 else order.duration_days|string + " ngày" }}. Thời hạn bắt đầu khi kích hoạt lần đầu.</p>
{% elif order.status == 'rejected' %}
<p class="aki-shop-muted">Đơn này đã bị từ chối. Liên hệ AKI DEV nếu bro cần kiểm tra lại.</p>
{% else %}
<div class="aki-shop-qr">
{% if qr_image_url %}<img src="{{ qr_image_url }}" alt="QR thanh toán ZaloPay" style="display:block;width:min(100%,300px);height:auto;margin:0 auto 14px;border-radius:14px;background:#fff;padding:8px">{% else %}<div class="aki-shop-qrmark">QR ZaloPay</div>{% endif %}
<p class="aki-shop-muted">Quét mã QR của AKI để chuyển đúng số tiền và nhập đúng nội dung chuyển khoản bên dưới.</p>
<a class="aki-shop-btn primary" href="{{ qr_page_url }}" target="_blank" rel="noopener">Mở ảnh QR thanh toán</a>
</div>
<div class="aki-shop-field"><label>Số tiền cần chuyển</label><input readonly value="{{ money(order.amount_vnd) }}"></div>
<div class="aki-shop-field"><label>Nội dung chuyển khoản bắt buộc</label><input readonly id="aki-memo" value="{{ order.order_code }}"></div>
<button class="aki-shop-btn" type="button" onclick="navigator.clipboard.writeText(document.getElementById('aki-memo').value).then(()=>this.innerText='Đã copy nội dung')">Copy nội dung</button>
{% if order.status == 'pending' %}
<form method="post" action="{{ url_for('aki_store_report_payment', order_id=order.id) }}" style="margin-top:22px">
<input type="hidden" name="_csrf" value="{{ csrf }}">
<div class="aki-shop-field"><label>Mã giao dịch / ghi chú (không bắt buộc)</label><input name="payment_ref" maxlength="120" placeholder="Nhập mã giao dịch nếu có"></div>
<button class="aki-shop-btn primary" type="submit">Tôi đã chuyển khoản</button>
</form>
{% else %}
<p class="aki-shop-muted">Đã gửi thông báo thanh toán. Đơn đang chờ bro kiểm tra và xác nhận.</p>
{% endif %}
{% endif %}
<p style="margin-top:20px"><a class="aki-shop-link" href="{{ url_for('aki_store_orders') }}">Quay lại đơn hàng</a></p>
</section>
"""
        labels = {"pending": "Chưa báo chuyển khoản", "reported": "Chờ admin xác nhận", "paid": "Đã thanh toán · Đã cấp key", "rejected": "Đơn bị từ chối"}
        return _page("Chi tiết đơn", inner, order=order, labels=labels, money=_money, qr_page_url=qr_page_url, qr_image_url=qr_image_url)

    @app.post("/store/orders/<int:order_id>/report")
    def aki_store_report_payment(order_id):
        customer = _customer()
        if customer is None:
            return redirect(url_for("aki_store_login"))
        order = _owned_order(order_id, customer)
        if order.status != "pending":
            flash("Đơn này đã được gửi hoặc xử lý trước đó.")
            return redirect(url_for("aki_store_order_detail", order_id=order.id))
        order.payment_ref = (request.form.get("payment_ref") or "").strip()[:120] or None
        order.status = "reported"
        order.reported_at = utcnow()
        _db_session().commit()
        flash("Đã gửi thông báo. Key sẽ được cấp sau khi admin kiểm tra tiền vào ví.")
        return redirect(url_for("aki_store_order_detail", order_id=order.id))

    @app.get("/store/account")
    def aki_store_account():
        customer = _customer()
        if customer is None:
            return redirect(url_for("aki_store_login"))
        paid_orders = (
            _db_session().query(AKIShopOrder)
            .filter_by(customer_id=customer.id, status="paid")
            .order_by(AKIShopOrder.paid_at.desc())
            .all()
        )
        inner = """
<section class="aki-shop-panel" style="max-width:900px">
<div class="aki-shop-eyebrow">MY AKI ACCOUNT</div><h1>{{ customer.username }}</h1>
<p class="aki-shop-muted">Tất cả license đã mua được lưu tại đây. Sau khi admin xác nhận thanh toán, key sẽ tự xuất hiện trong tài khoản này.</p>
<h2 style="font-size:18px;margin-top:28px">License của tôi</h2>
{% if paid_orders %}
<div style="display:grid;gap:14px;margin-top:14px">
{% for order in paid_orders %}
<article class="aki-shop-card">
<div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap">
<h3 style="margin:0">{{ "Vĩnh viễn" if order.duration_days == 0 else order.duration_days|string + " ngày" }}</h3>
<span class="aki-shop-pill good">Đã cấp key</span>
</div>
<p class="aki-shop-muted" style="margin:9px 0 0">Đơn {{ order.order_code }} · {{ money(order.amount_vnd) }}</p>
<div class="aki-shop-key" id="aki-key-{{ order.id }}">{{ order.issued_key }}</div>
<button class="aki-shop-btn primary" type="button" onclick="navigator.clipboard.writeText(document.getElementById('aki-key-{{ order.id }}').innerText).then(()=>this.innerText='Đã copy key')">Copy key</button>
<a class="aki-shop-link" href="{{ url_for('aki_store_order_detail', order_id=order.id) }}" style="margin-left:6px">Chi tiết đơn</a>
<p class="aki-shop-muted" style="font-size:12px;margin-bottom:0">Thời hạn bắt đầu tính từ lần kích hoạt đầu tiên.</p>
</article>
{% endfor %}
</div>
{% else %}
<p class="aki-shop-muted">Bro chưa có license nào. Chọn một gói ở cửa hàng để bắt đầu nhé.</p>
<a class="aki-shop-btn primary" href="{{ url_for('aki_store_home') }}">Chọn license</a>
{% endif %}
<div style="margin-top:24px"><a class="aki-shop-link" href="{{ url_for('aki_store_orders') }}">Xem toàn bộ lịch sử đơn hàng</a></div>
</section>
"""
        return _page("Tài khoản", inner, customer=customer, paid_orders=paid_orders, money=_money)

    @app.get("/admin/orders")
    def aki_admin_orders():
        if session.get("admin_logged_in") is not True:
            abort(403)
        rows = _db_session().query(AKIShopOrder).order_by(AKIShopOrder.created_at.desc()).limit(200).all()
        inner = """
<section class="aki-shop-panel" style="max-width:1050px">
<div class="aki-shop-eyebrow">PAYMENT REVIEW</div><h1>Đơn mua license</h1>
<p class="aki-shop-muted">Kiểm tra tiền đã vào ví ZaloPay trước khi xác nhận. Nút xác nhận sẽ tạo license và lưu key trực tiếp vào tài khoản khách.</p>
{% if rows %}
<table class="aki-shop-table"><thead><tr><th>Đơn</th><th>Khách</th><th>Gói</th><th>Tiền</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody>
{% for order in rows %}<tr>
<td>{{ order.order_code }}<br><small style="color:#888">{{ order.created_at }}</small></td>
<td>{{ order.customer.username if order.customer else order.customer_id }}</td>
<td>{{ "Vĩnh viễn" if order.duration_days == 0 else order.duration_days|string + " ngày" }}</td>
<td>{{ money(order.amount_vnd) }}{% if order.payment_ref %}<br><small style="color:#aaa">Ref: {{ order.payment_ref }}</small>{% endif %}</td>
<td><span class="aki-shop-pill {{ 'good' if order.status == 'paid' else 'wait' }}">{{ labels[order.status] }}</span></td>
<td>
{% if order.status in ('pending','reported') %}
<form method="post" action="{{ url_for('aki_admin_order_action', order_id=order.id) }}" style="display:flex;gap:6px;flex-wrap:wrap">
<input type="hidden" name="_csrf" value="{{ csrf }}">
<button class="aki-shop-btn primary" name="action" value="approve" type="submit">Xác nhận + cấp key</button>
<button class="aki-shop-btn danger" name="action" value="reject" type="submit">Từ chối</button>
</form>
{% elif order.status == 'paid' %}
<small style="color:#aaa">Key đã lưu trên web</small>
{% endif %}
</td>
</tr>{% endfor %}</tbody></table>
{% else %}<p class="aki-shop-muted">Chưa có đơn hàng nào.</p>{% endif %}
</section>
"""
        labels = {"pending": "Chưa báo chuyển khoản", "reported": "Khách báo đã chuyển", "paid": "Đã cấp key", "rejected": "Đã từ chối"}
        # Attach the customer object for the template without creating ORM relationships.
        for order in rows:
            order.customer = _db_session().get(AKIShopCustomer, order.customer_id)
        return _page("Duyệt đơn hàng", inner, rows=rows, labels=labels, money=_money)

    @app.post("/admin/orders/<int:order_id>/action")
    def aki_admin_order_action(order_id):
        if session.get("admin_logged_in") is not True:
            abort(403)
        order = _db_session().get(AKIShopOrder, order_id)
        if order is None:
            abort(404)
        action = request.form.get("action")
        if order.status == "paid":
            flash("Đơn đã được duyệt, hệ thống không tạo key trùng.")
            return redirect(url_for("aki_admin_orders"))
        if order.status == "rejected":
            flash("Đơn này đã bị từ chối.")
            return redirect(url_for("aki_admin_orders"))
        if action == "reject":
            order.status = "rejected"
            _db_session().commit()
            flash("Đã từ chối đơn hàng.")
            return redirect(url_for("aki_admin_orders"))
        if action != "approve":
            abort(400)
        customer = _db_session().get(AKIShopCustomer, order.customer_id)
        if customer is None:
            abort(400)
        license_key = "AKI-" + secrets.token_hex(5).upper() + "-" + secrets.token_hex(5).upper()
        key_digest = hashlib.sha256(license_key.encode("utf-8")).hexdigest()
        item = License(
            key_hash=key_digest,
            key_hint=license_key[-4:],
            duration_days=order.duration_days,
            label="SALE-" + order.order_code,
            created_at=utcnow(),
            activated_at=None,
            expires_at=None,
        )
        try:
            _db_session().add(item)
            _db_session().flush()
            order.license_id = item.id
            order.issued_key = license_key
            order.status = "paid"
            order.paid_at = utcnow()
            _db_session().commit()
        except Exception:
            _db_session().rollback()
            app.logger.exception("AKI failed to issue license for order %s", order.order_code)
            flash("Không thể tạo key. Hãy kiểm tra log và thử lại.")
            return redirect(url_for("aki_admin_orders"))
        flash("Đã xác nhận thanh toán và tạo license. Key đã lưu trong tài khoản khách.")
        return redirect(url_for("aki_admin_orders"))

    @app.after_request
    def aki_store_security_headers(response):
        if request.path.startswith("/store") or request.path.startswith("/admin/orders"):
            response.headers.setdefault("Cache-Control", "no-store, max-age=0")
            response.headers.setdefault("X-Content-Type-Options", "nosniff")

        # Put a prominent shortcut on the existing admin dashboard so the
        # payment review queue is easy to find without remembering its URL.
        if request.path == "/admin" and response.mimetype == "text/html":
            try:
                waiting_count = (
                    _db_session().query(AKIShopOrder)
                    .filter_by(status="reported")
                    .count()
                )
            except Exception:
                app.logger.exception("Could not count AKI orders awaiting review")
                waiting_count = 0

            pending_label = (
                f"{waiting_count} đơn khách báo đã chuyển khoản"
                if waiting_count
                else "Không có đơn nào đang chờ xác nhận"
            )
            entry = """
<style id="aki-admin-order-entry-style">
.aki-admin-order-entry{width:min(1180px,calc(100% - 36px));margin:18px auto 22px;padding:19px 22px;display:flex;align-items:center;justify-content:space-between;gap:18px;flex-wrap:wrap;border:1px solid rgba(255,255,255,.16);border-radius:20px;background:linear-gradient(115deg,rgba(255,255,255,.105),rgba(255,255,255,.035));backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);box-shadow:0 14px 38px rgba(0,0,0,.22);color:#f5f5f2;font-family:Inter,system-ui,sans-serif}
.aki-admin-order-entry *{box-sizing:border-box}
.aki-admin-order-entry .aki-order-eyebrow{display:block;color:#aaa;font-size:10px;letter-spacing:.2em;font-weight:750;text-transform:uppercase;margin-bottom:7px}
.aki-admin-order-entry h2{margin:0 0 6px;font-size:19px;letter-spacing:-.035em;color:#fff}
.aki-admin-order-entry p{margin:0;color:#aaa;font-size:12px;line-height:1.55;max-width:650px}
.aki-admin-order-entry .aki-order-actions{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.aki-admin-order-entry .aki-order-count{font-size:11px;color:#ddd;border:1px solid rgba(255,255,255,.15);border-radius:999px;padding:7px 11px;background:rgba(0,0,0,.16)}
.aki-admin-order-entry .aki-order-link{display:inline-flex;align-items:center;justify-content:center;gap:9px;border-radius:999px;padding:12px 17px;background:#f0f0eb;color:#111!important;font-size:12px;font-weight:800;text-decoration:none!important;white-space:nowrap;transition:transform .18s ease,background .18s ease}
.aki-admin-order-entry .aki-order-link:hover{transform:translateY(-2px);background:#fff}
@media(max-width:620px){.aki-admin-order-entry{padding:17px}.aki-admin-order-entry .aki-order-actions{width:100%;justify-content:space-between}.aki-admin-order-entry .aki-order-link{flex:1}}
</style>
<section class="aki-admin-order-entry" aria-label="Quản lý đơn mua license">
  <div>
    <span class="aki-order-eyebrow">Payment center · AKI DEV</span>
    <h2>Duyệt đơn mua license</h2>
    <p>Kiểm tra giao dịch ZaloPay, xác nhận hoặc từ chối đơn và cấp key thẳng vào tài khoản khách hàng.</p>
  </div>
  <div class="aki-order-actions">
    <span class="aki-order-count">__PENDING_LABEL__</span>
    <a class="aki-order-link" href="__ORDER_URL__">Mở danh sách đơn <span aria-hidden="true">↗</span></a>
  </div>
</section>
"""
            entry = entry.replace("__PENDING_LABEL__", pending_label)
            entry = entry.replace("__ORDER_URL__", url_for("aki_admin_orders"))
            page = response.get_data(as_text=True)
            body_start = page.lower().find("<body")
            body_end = page.find(">", body_start) if body_start >= 0 else -1
            if body_end >= 0 and "aki-admin-order-entry" not in page:
                page = page[:body_end + 1] + entry + page[body_end + 1:]
                response.set_data(page)

        return response

    app.logger.info("AKI manual storefront registered: /store, /admin and /admin/orders")
