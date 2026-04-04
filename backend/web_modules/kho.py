from decimal import Decimal

from flask import g, flash, redirect, render_template, request, url_for
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.models import InventoryItem, InventoryStock, InventoryTransaction
from backend.web import (
    get_current_branch_scope,
    list_scope_branches,
    normalize_choice,
    paginate,
    parse_int,
    parse_page,
    resolve_selected_branch_id,
    roles_required,
    web_bp,
)


@web_bp.get("/inventory")
@roles_required("super_admin", "branch_manager")
def inventory():
    scope_ids = get_current_branch_scope()
    if not scope_ids:
        return redirect(url_for("web.dashboard"))

    q = (request.args.get("q") or "").strip()
    low = request.args.get("low") == "1"
    selected_branch_id = resolve_selected_branch_id(scope_ids, parse_int(request.args.get("branch_id")))
    page = parse_page(request.args.get("page"), default=1)

    stock_query = (
        InventoryStock.query.join(InventoryItem, InventoryStock.item_id == InventoryItem.id)
        .filter(InventoryStock.branch_id.in_(scope_ids))
    )
    if selected_branch_id:
        stock_query = stock_query.filter(InventoryStock.branch_id == selected_branch_id)
    if q:
        keyword = f"%{q}%"
        stock_query = stock_query.filter(
            or_(
                InventoryItem.name.ilike(keyword),
                InventoryItem.group_name.ilike(keyword),
            )
        )
    if low:
        stock_query = stock_query.filter(InventoryStock.quantity <= InventoryItem.min_stock)

    pager = paginate(stock_query.order_by(InventoryStock.id.asc()), page=page, per_page=12)

    tx_query = (
        InventoryTransaction.query.join(InventoryItem, InventoryTransaction.item_id == InventoryItem.id)
        .filter(InventoryTransaction.branch_id.in_(scope_ids))
    )
    if selected_branch_id:
        tx_query = tx_query.filter(InventoryTransaction.branch_id == selected_branch_id)
    if q:
        tx_query = tx_query.filter(InventoryItem.name.ilike(f"%{q}%"))
    tx_rows = tx_query.order_by(InventoryTransaction.id.asc()).limit(20).all()

    branch_options = list_scope_branches(scope_ids, order_by="id")
    item_rows = InventoryItem.query.order_by(InventoryItem.id.asc()).all()

    return render_template(
        "web/inventory.html",
        rows=pager.items,
        pager=pager,
        tx_rows=tx_rows,
        branch_options=branch_options,
        item_rows=item_rows,
        selected_branch_id=selected_branch_id,
        q=q,
        low=low,
        is_super_admin=g.web_user.is_super_admin,
    )


@web_bp.post("/inventory/items/save")
@roles_required("super_admin")
def inventory_items_save():
    item_id = parse_int(request.form.get("item_id"))
    name = (request.form.get("name") or "").strip()
    unit = (request.form.get("unit") or "").strip()
    group_name = (request.form.get("group_name") or "").strip() or None
    min_stock_value = parse_int(request.form.get("min_stock"))
    status = normalize_choice(request.form.get("status"), {"active", "inactive"}, "active")

    if not name or not unit:
        flash("Tên sản phẩm và đơn vị không được để trống.", "error")
        return redirect(url_for("web.inventory"))
    if min_stock_value is None or min_stock_value < 0:
        flash("Mức tồn tối thiểu phải là số nguyên không âm.", "error")
        return redirect(url_for("web.inventory"))

    min_stock = Decimal(min_stock_value)

    if item_id:
        row = db.session.get(InventoryItem, item_id)
        if row is None:
            flash("Không tìm thấy sản phẩm kho.", "error")
            return redirect(url_for("web.inventory"))
    else:
        row = InventoryItem()
        db.session.add(row)

    row.name = name
    row.unit = unit
    row.group_name = group_name
    row.min_stock = min_stock
    row.status = status

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Tên sản phẩm kho đã tồn tại.", "error")
        return redirect(url_for("web.inventory"))

    flash("Đã lưu danh mục sản phẩm kho.", "success")
    return redirect(url_for("web.inventory"))


@web_bp.post("/inventory/txn")
@roles_required("super_admin", "branch_manager")
def inventory_txn():
    scope_ids = get_current_branch_scope()
    item_id = parse_int(request.form.get("item_id"))
    tx_type = normalize_choice(request.form.get("type"), {"in", "out", "adjust"}, "")
    qty_value = parse_int(request.form.get("quantity"))
    note = (request.form.get("note") or "").strip() or None

    if g.web_user.is_super_admin:
        branch_id = parse_int(request.form.get("branch_id"))
    else:
        branch_id = g.active_branch_id

    if branch_id not in scope_ids:
        flash("Chi nhánh không hợp lệ.", "error")
        return redirect(url_for("web.inventory"))
    if not tx_type:
        flash("Loại giao dịch kho không hợp lệ.", "error")
        return redirect(url_for("web.inventory"))
    if qty_value is None or qty_value < 0:
        flash("Số lượng phải là số nguyên không âm.", "error")
        return redirect(url_for("web.inventory"))

    qty_input = Decimal(qty_value)

    item = db.session.get(InventoryItem, item_id) if item_id else None
    if item is None:
        flash("Sản phẩm kho không hợp lệ.", "error")
        return redirect(url_for("web.inventory"))

    if tx_type in {"in", "out"} and qty_input <= 0:
        flash("Số lượng nhập/xuất phải lớn hơn 0.", "error")
        return redirect(url_for("web.inventory"))

    stock = InventoryStock.query.filter_by(branch_id=branch_id, item_id=item.id).first()
    if stock is None:
        stock = InventoryStock(branch_id=branch_id, item_id=item.id, quantity=Decimal("0.00"))
        db.session.add(stock)
        db.session.flush()

    current_qty = Decimal(str(stock.quantity or 0))
    if tx_type == "in":
        delta = qty_input
        new_qty = current_qty + delta
    elif tx_type == "out":
        delta = -qty_input
        new_qty = current_qty + delta
    else:
        new_qty = qty_input
        delta = new_qty - current_qty

    if new_qty < 0:
        flash("Không thể xuất kho vượt số lượng hiện có.", "error")
        return redirect(url_for("web.inventory"))

    stock.quantity = new_qty
    db.session.add(
        InventoryTransaction(
            branch_id=branch_id,
            item_id=item.id,
            type=tx_type,
            quantity=delta,
            note=note,
        )
    )
    db.session.commit()
    flash("Đã cập nhật tồn kho.", "success")
    return redirect(url_for("web.inventory"))
