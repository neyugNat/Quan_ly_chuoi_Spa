from flask import flash, g, redirect, render_template, request, session, url_for

from backend.models import User
from backend.web import login_required, web_bp


@web_bp.get("/")
def index():
    if getattr(g, "web_user", None):
        return redirect(url_for("web.dashboard"))
    return redirect(url_for("web.login"))


@web_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if getattr(g, "web_user", None):
            return redirect(url_for("web.dashboard"))
        return render_template("web/login.html")

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if not username or not password:
        flash("Vui lòng nhập đầy đủ tài khoản và mật khẩu.", "error")
        return render_template("web/login.html"), 400

    user = User.query.filter_by(username=username, is_active=True).first()
    if not user or not user.verify_password(password):
        flash("Thông tin đăng nhập không đúng.", "error")
        return render_template("web/login.html"), 401

    session["web_user_id"] = user.id
    if user.branch_id:
        session["web_branch_id"] = int(user.branch_id)
    return redirect(url_for("web.dashboard"))


@web_bp.post("/logout")
@login_required
def logout():
    session.pop("web_user_id", None)
    session.pop("web_branch_id", None)
    return redirect(url_for("web.login"))
