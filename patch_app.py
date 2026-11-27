import ast
from pathlib import Path

APP = Path("app.py")
source = APP.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global source
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"AKI patch aborted: expected one match for {label}, found {count}")
    source = source.replace(old, new, 1)


replace_once(
'''    expires = ensure_utc(license_item.expires_at)
    if expires is None or now >= expires:
        return "expired"
''',
'''    # duration_days == 0 is a lifetime license (no expiry timestamp).
    if license_item.duration_days == 0:
        return "active"
    expires = ensure_utc(license_item.expires_at)
    if expires is None or now >= expires:
        return "expired"
''',
"lifetime license state",
)

replace_once(
'''    @app.before_request
    def protect_admin_posts():
        if request.method == "POST" and not request.path.startswith("/api/"):
            sent = request.form.get("_csrf", "")
            saved = session.get("_csrf_token", "")
            if not sent or not saved or not hmac.compare_digest(sent, saved):
                abort(400, description="CSRF check failed. Reload the page and try again.")
''',
'''    @app.before_request
    def enforce_admin_boundary():
        path = request.path
        protected_admin_page = path == "/admin" or path.startswith("/admin/")
        protected_admin_api = path.startswith("/api/") and path != "/api/verify"
        if path == "/admin/login":
            return None
        if (protected_admin_page or protected_admin_api) and session.get("admin_logged_in") is not True:
            if protected_admin_api or request.is_json:
                return jsonify({"ok": False, "error": "admin_auth_required"}), 401
            return redirect(url_for("admin_login"))

    @app.before_request
    def protect_admin_posts():
        # Only the public license verification endpoint is exempt from CSRF.
        # Future admin APIs must send X-CSRF-Token or the standard _csrf form field.
        if request.method == "POST" and request.path != "/api/verify":
            sent = request.form.get("_csrf", "") or request.headers.get("X-CSRF-Token", "")
            saved = session.get("_csrf_token", "")
            if not sent or not saved or not hmac.compare_digest(sent, saved):
                abort(400, description="CSRF check failed. Reload the page and try again.")
''',
"central admin authorization and CSRF",
)

replace_once(
'''    @app.get("/healthz")
    def healthz():
''',
'''    @app.after_request
    def add_security_headers_and_monochrome_theme(response):
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.is_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        if request.path == "/admin" or request.path.startswith("/admin/"):
            response.headers["Cache-Control"] = "no-store, max-age=0"
            response.headers["Pragma"] = "no-cache"

        if response.mimetype == "text/html":
            page = response.get_data(as_text=True)
            if request.path in ("/admin", "/admin/keys/create"):
                select_match = re.search(
                    r'<select\\b[^>]*\\bid\\s*=\\s*"plan-select"[^>]*>',
                    page,
                    flags=re.IGNORECASE,
                )
                if select_match and 'value="permanent"' not in page:
                    page = (
                        page[:select_match.end()]
                        + '<option value="permanent">Vĩnh viễn</option>'
                        + page[select_match.end():]
                    )

            theme = """
<style id="aki-monochrome-theme">
:root {
  color-scheme: dark;
  --bg:#080808; --panel:#111111; --panel2:#191919;
  --line:rgba(255,255,255,.13); --text:#f5f5f5; --muted:#a0a0a0;
  --purple:#eeeeee; --purple2:#cfcfcf; --green:#e5e5e5;
  --red:#bdbdbd; --blue:#ffffff;
  --font:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
  --display:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
}
html,body { background:#080808!important; color:#f5f5f5!important; }
body { font-family:var(--font)!important; }
a { color:#ededed!important; }
.ambient { background:#ffffff!important; opacity:.035!important; }
.sidebar,.topbar,.panel,.card,.stat-card,.feature-card,.key-card,.table-wrap,
[class*="panel"],[class*="card"] {
  background-color:rgba(17,17,17,.96)!important;
  border-color:var(--line)!important;
  box-shadow:0 14px 42px rgba(0,0,0,.28)!important;
}
h1,h2,h3,h4,strong,b { color:#fff; }
p,label,small,.muted,.lede,.description { color:#b5b5b5; }
button,.btn,.btn-primary,input[type="submit"] {
  background:#f2f2f2!important; color:#090909!important;
  border:1px solid #f2f2f2!important; border-radius:10px!important;
  font-weight:700!important; transition:transform .15s ease,background .15s ease!important;
}
button:hover,.btn:hover,.btn-primary:hover,input[type="submit"]:hover {
  background:#d8d8d8!important; transform:translateY(-1px);
}
.btn-secondary,.btn-ghost,.icon-btn,button.secondary {
  background:#191919!important; color:#f4f4f4!important;
  border:1px solid #444!important;
}
input,select,textarea {
  background:#0d0d0d!important; color:#f5f5f5!important;
  border:1px solid #454545!important; border-radius:10px!important;
}
input:focus,select:focus,textarea:focus {
  outline:none!important; border-color:#eee!important;
  box-shadow:0 0 0 3px rgba(255,255,255,.10)!important;
}
table { color:#eee!important; border-color:#333!important; }
th { background:#191919!important; color:#ddd!important; }
td { border-color:#292929!important; }
tr:hover td { background:rgba(255,255,255,.035)!important; }
.badge,.pill,.status,.status-pill {
  background:#252525!important; color:#f0f0f0!important;
  border:1px solid #444!important;
}
hr { border-color:#292929!important; }
::selection { background:#eee!important; color:#080808!important; }
@media(max-width:760px) {
  .topbar { gap:12px!important; flex-wrap:wrap!important; }
  table { min-width:640px; }
}
</style>
"""
            if "</head>" in page.lower():
                page = re.sub(r"</head>", lambda _m: theme + "</head>", page, count=1, flags=re.IGNORECASE)
            elif "</body>" in page.lower():
                page = re.sub(r"</body>", lambda _m: theme + "</body>", page, count=1, flags=re.IGNORECASE)
            else:
                page = theme + page
            response.set_data(page)
        return response

    @app.get("/healthz")
    def healthz():
''',
"security headers and monochrome theme",
)

replace_once(
'''        plan = request.form.get("plan", "30")
        if plan == "custom":
            try:
                days = int(request.form.get("custom_days", "0"))
            except ValueError:
                days = 0
        else:
            try:
                days = int(plan)
            except ValueError:
                days = 0
        if days < 1 or days > 3650:
            flash("Số ngày phải nằm trong khoảng 1–3650.", "error")
            return redirect(url_for("dashboard"))
''',
'''        plan = request.form.get("plan", "30")
        permanent = plan in {"permanent", "lifetime", "forever"}
        if permanent:
            days = 0
        elif plan == "custom":
            try:
                days = int(request.form.get("custom_days", "0"))
            except ValueError:
                days = 0
        else:
            try:
                days = int(plan)
            except ValueError:
                days = 0
        if not permanent and (days < 1 or days > 3650):
            flash("Số ngày phải nằm trong khoảng 1–3650.", "error")
            return redirect(url_for("dashboard"))
''',
"permanent key creation",
)

replace_once(
'''            item.expires_at = now + timedelta(days=item.duration_days)
''',
'''            item.expires_at = None if item.duration_days == 0 else now + timedelta(days=item.duration_days)
''',
"permanent activation",
)

replace_once(
'''        expires_at = ensure_utc(item.expires_at)
        if expires_at is None or now >= expires_at:
            return jsonify({"valid": False, "message": "License key đã hết hạn."}), 403

        seconds_left = max(0, int((expires_at - now).total_seconds()))
        days_left = (seconds_left + 86399) // 86400
        return jsonify({
            "valid": True,
            "message": "License verified.",
            "status": "active",
            "duration_days": item.duration_days,
            "expires_at": expires_at.isoformat(),
            "days_remaining": days_left,
        })
''',
'''        permanent = item.duration_days == 0
        expires_at = ensure_utc(item.expires_at)
        if not permanent and (expires_at is None or now >= expires_at):
            return jsonify({"valid": False, "message": "License key đã hết hạn."}), 403

        if permanent:
            days_left = None
            expiry_value = None
        else:
            seconds_left = max(0, int((expires_at - now).total_seconds()))
            days_left = (seconds_left + 86399) // 86400
            expiry_value = expires_at.isoformat()
        return jsonify({
            "valid": True,
            "message": "License verified.",
            "status": "active",
            "duration_days": item.duration_days,
            "expires_at": expiry_value,
            "days_remaining": days_left,
            "permanent": permanent,
            "expires_label": "Vĩnh viễn" if permanent else expiry_value,
        })
''',
"permanent API verification",
)

ast.parse(source)  # Fail the build instead of deploying invalid patched Python.

replace_once(
'''            response.set_data(page)
        return response

    @app.get("/healthz")
''',
'''            if request.path in ("/admin", "/admin/keys/create") and "aki-custom-elements" not in page:
                now = utcnow()
                licenses = License.query.all()
                total_count = len(licenses)
                active_count = sum(1 for item in licenses if license_state(item, now) == "active")
                unused_count = sum(1 for item in licenses if license_state(item, now) == "unused")
                stat_values = [
                    (format(total_count, ","), "Tổng license"),
                    (format(active_count, ","), "Đang hoạt động"),
                    (format(unused_count, ","), "Chưa kích hoạt"),
                ]
                stat_items = "".join(
                    '<li class="u426-c" data-v="' + value + '"><span class="u426-n"></span><small>' + label + '</small></li>'
                    for value, label in stat_values
                )
                addon = (
                    '<section class="aki-custom-elements" aria-label="AKI License statistics and Discord contact">'
                    '<div class="u426" aria-label="License statistics">'
                    '<ul class="u426-cd">' + stat_items + '</ul>'
                    '</div>'
                    '<article class="aki-uv-card" aria-label="Contact AKI Dev">'
                    '<div class="aki-uv-blob" aria-hidden="true"></div>'
                    '<div class="aki-uv-bg">'
                    '<p class="aki-uv-kicker">CUSTOM DEVELOPMENT</p>'
                    '<h2 class="aki-uv-title">AKI DEV</h2>'
                    '<p class="aki-uv-copy">Custom tools &amp; automation<br>Liên hệ để đặt tool riêng</p>'
                    '<button type="button" class="aki-uv-discord" data-discord="s0l">DISCORD · s0l</button>'
                    '<span class="aki-uv-status" role="status" aria-live="polite"></span>'
                    '</div></article></section>'
                )
                asset_tags = (
                    '<link rel="stylesheet" href="' + url_for("static", filename="aki-custom-elements.css") + '">'
                    '<script defer src="' + url_for("static", filename="aki-custom-elements.js") + '"></script>'
                )
                if "</head>" in page.lower():
                    page = re.sub(r"</head>", lambda _m: asset_tags + "</head>", page, count=1, flags=re.IGNORECASE)
                else:
                    page = asset_tags + page
                if "</body>" in page.lower():
                    page = re.sub(r"</body>", lambda _m: addon + "</body>", page, count=1, flags=re.IGNORECASE)
                else:
                    page += addon
            response.set_data(page)
        return response

    @app.get("/healthz")
''',
"AKI dashboard stats and Discord contact components",
)

APP.write_text(source, encoding="utf-8")

client = Path("aki_license_client_snippet.py")
if client.exists():
    client_source = client.read_text(encoding="utf-8")
    client_source = client_source.replace(
        'print("[AKI] Expires:", result.get("expires_at", "Unknown"))',
        'print("[AKI] Expires:", "Vĩnh viễn" if result.get("permanent") else (result.get("expires_at") or "Unknown"))',
    )
    client.write_text(client_source, encoding="utf-8")

print("AKI patch applied: server-side admin gate, CSRF hardening, security headers, lifetime keys, monochrome theme.")
