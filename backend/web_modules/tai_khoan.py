from flask import g, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.models import User
from backend.web import list_scope_branches, parse_int, roles_required, web_bp


@web_bp.get("/accounts")
@roles_required("super_admin")
def accounts():
    scope_ids = getattr(g, "scope_branch_ids", [])
    edit_id = parse_int(request.args.get("edit_id"))

    rows = User.query.filter(User.role == "branch_manager").order_by(User.id.desc()).all()
    branch_options = list_scope_branches(scope_ids, order_by="name")

    edit_row = None
    if edit_id:
        edit_row = User.query.filter(User.id == edit_id, User.role == "branch_manager").first()
        if edit_row is None:
            flash("Không tìm thấy tài khoản quản lí chi nhánh.", "error")
            return redirect(url_for("web.accounts"))

    form_data = {
        "user_id": edit_row.id if edit_row else None,
        "username": edit_row.username if edit_row else "",
        "branch_id": edit_row.branch_id if edit_row else "",
        "is_active": "1" if (edit_row.is_active if edit_row else True) else "0",
    }

    return render_template(
        "web/accounts.html",
        rows=rows,
        branch_options=branch_options,
        edit_mode=bool(edit_row),
        form_data=form_data,
    )


@web_bp.post("/accounts/save")
@roles_required("super_admin")
def accounts_save():
    scope_ids = getattr(g, "scope_branch_ids", [])
    user_id = parse_int(request.form.get("user_id"))
    username = (request.form.get("username") or "").strip()
    branch_id = parse_int(request.form.get("branch_id"))
    password = request.form.get("password") or ""
    is_active = (request.form.get("is_active") or "1") == "1"

    if not username:
        flash("Username không được để trống.", "error")
        return redirect(url_for("web.accounts"))
    if branch_id not in scope_ids:
        flash("Chi nhánh là bắt buộc và phải hợp lệ.", "error")
        return redirect(url_for("web.accounts"))

    if user_id:
        row = User.query.filter(User.id == user_id, User.role == "branch_manager").first()
        if row is None:
            flash("Không tìm thấy tài khoản quản lí chi nhánh.", "error")
            return redirect(url_for("web.accounts"))
    else:
        if len(password) < 6:
            flash("Mật khẩu tối thiểu 6 ký tự.", "error")
            return redirect(url_for("web.accounts"))
        row = User(role="branch_manager")
        db.session.add(row)

    row.username = username
    row.role = "branch_manager"
    row.is_active = is_active
    row.branch_id = branch_id
    if password:
        if len(password) < 6:
            flash("Mật khẩu tối thiểu 6 ký tự.", "error")
            return redirect(url_for("web.accounts"))
        row.set_password(password)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Username đã tồn tại.", "error")
        return redirect(url_for("web.accounts"))

    flash("Đã lưu tài khoản.", "success")
    return redirect(url_for("web.accounts"))


@web_bp.post("/accounts/password")
@roles_required("super_admin")
def accounts_change_password():
    current_password = request.form.get("current_password") or ""
    new_password = request.form.get("new_password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if not g.web_user.verify_password(current_password):
        flash("Mật khẩu hiện tại không đúng.", "error")
        return redirect(url_for("web.accounts"))
    if len(new_password) < 6:
        flash("Mật khẩu mới tối thiểu 6 ký tự.", "error")
        return redirect(url_for("web.accounts"))
    if new_password != confirm_password:
        flash("Xác nhận mật khẩu chưa khớp.", "error")
        return redirect(url_for("web.accounts"))

    g.web_user.set_password(new_password)
    db.session.commit()
    flash("Đổi mật khẩu thành công.", "success")
    return redirect(url_for("web.accounts"))
