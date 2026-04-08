from decimal import Decimal

from flask import g, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.logs import write_log
from backend.models import InventoryItem, InventoryStock, InventoryTransaction
from backend.web import (
    collect_non_empty_text,
    get_current_branch_scope,
    list_scope_branches,
    normalize_choice,
    paginate,
    parse_int,
    parse_optional_text,
    parse_page,
    parse_text,
    resolve_selected_branch_id,
    roles_required,
    web_bp,
)


def format_integer_input(value) -> str:
    if value is None:
        return ""
    try:
        return str(int(Decimal(str(value))))
    except (ValueError, TypeError):
        return ""


def redirect_inventory_with_filters(default_branch_id=None, default_page=1):
    q = parse_text(request.form.get("q"))
    group_name = parse_text(request.form.get("group_name"))
    low = request.form.get("low") == "1"
    branch_id = parse_int(request.form.get("branch_id"))
    if branch_id is None:
        branch_id = default_branch_id
    page = parse_page(request.form.get("page"), default=default_page)
    return redirect(
        url_for(
            "web.inventory",
            q=q or None,
            group_name=group_name or None,
            low=1 if low else None,
            branch_id=branch_id,
            page=page,
        )
    )


def inventory_error(message: str, default_branch_id=None, default_page=1):
    flash(message, "error")
    return redirect_inventory_with_filters(default_branch_id=default_branch_id, default_page=default_page)


def inventory_home_error(message: str):
    flash(message, "error")
    return redirect(url_for("web.inventory"))


@web_bp.get("/inventory")
@roles_required("super_admin", "branch_manager", "inventory_controller")
def inventory():
    scope_ids = get_current_branch_scope()
    if not scope_ids:
        return redirect(url_for("web.dashboard"))

    user = g.web_user
    q = parse_text(request.args.get("q"))
    group_name = parse_text(request.args.get("group_name"))
    low = request.args.get("low") == "1"
    selected_branch_id = resolve_selected_branch_id(scope_ids, parse_int(request.args.get("branch_id")))
    edit_stock_id = parse_int(request.args.get("edit_stock_id"))
    page = parse_page(request.args.get("page"), default=1)

    stock_query = (
        InventoryStock.query.join(InventoryItem, InventoryStock.item_id == InventoryItem.id)
        .filter(InventoryStock.branch_id.in_(scope_ids))
    )
    if selected_branch_id:
        stock_query = stock_query.filter(InventoryStock.branch_id == selected_branch_id)
    if q:
        stock_query = stock_query.filter(InventoryItem.name.ilike(f"%{q}%"))
    if group_name:
        stock_query = stock_query.filter(InventoryItem.group_name == group_name)
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
    if group_name:
        tx_query = tx_query.filter(InventoryItem.group_name == group_name)
    tx_rows = tx_query.order_by(InventoryTransaction.id.asc()).limit(20).all()

    branch_options = list_scope_branches(scope_ids, order_by="id")
    item_rows = InventoryItem.query.order_by(InventoryItem.id.asc()).all()
    group_rows = (
        db.session.query(InventoryItem.group_name)
        .filter(InventoryItem.group_name.isnot(None), InventoryItem.group_name != "")
        .distinct()
        .order_by(InventoryItem.group_name.asc())
        .all()
    )
    group_options = collect_non_empty_text(group_rows)
    if group_name and group_name not in group_options:
        group_options.insert(0, group_name)

    edit_stock = None
    if edit_stock_id:
        edit_stock = (
            InventoryStock.query.join(InventoryItem, InventoryStock.item_id == InventoryItem.id)
            .filter(
                InventoryStock.id == edit_stock_id,
                InventoryStock.branch_id.in_(scope_ids),
            )
            .first()
        )
        if edit_stock is None:
            flash("Không tìm thấy dòng tồn kho.", "error")
            return redirect(
                url_for(
                    "web.inventory",
                    page=page,
                    q=q,
                    group_name=group_name,
                    low=1 if low else None,
                    branch_id=selected_branch_id,
                )
            )

    stock_form_data = {
        "stock_id": edit_stock.id if edit_stock else None,
        "branch_id": edit_stock.branch_id if edit_stock else None,
        "branch_name": edit_stock.branch.name if edit_stock and edit_stock.branch else "-",
        "item_id": edit_stock.item_id if edit_stock else None,
        "item_name": edit_stock.item.name if edit_stock and edit_stock.item else "",
        "group_name": edit_stock.item.group_name if edit_stock and edit_stock.item else "",
        "unit": edit_stock.item.unit if edit_stock and edit_stock.item else "",
        "quantity": format_integer_input(edit_stock.quantity) if edit_stock else "",
        "min_stock": format_integer_input(edit_stock.item.min_stock) if edit_stock and edit_stock.item else "",
        "status": edit_stock.item.status if edit_stock and edit_stock.item else "active",
    }

    return render_template(
        "web/inventory.html",
        rows=pager.items,
        pager=pager,
        tx_rows=tx_rows,
        branch_options=branch_options,
        item_rows=item_rows,
        selected_branch_id=selected_branch_id,
        q=q,
        group_name=group_name,
        group_options=group_options,
        low=low,
        is_super_admin=user.is_super_admin,
        stock_edit_mode=bool(edit_stock),
        stock_form_data=stock_form_data,
    )


@web_bp.post("/inventory/stocks/save")
@roles_required("super_admin", "branch_manager", "inventory_controller")
def inventory_stocks_save():
    scope_ids = get_current_branch_scope()
    stock_id = parse_int(request.form.get("stock_id"))
    branch_id_raw = parse_int(request.form.get("branch_id"))
    item_name = parse_text(request.form.get("item_name"))
    group_name = parse_optional_text(request.form.get("group_name"))
    unit = parse_text(request.form.get("unit"))
    quantity_value = parse_int(request.form.get("quantity"))
    min_stock_value = parse_int(request.form.get("min_stock"))
    status = normalize_choice(request.form.get("status"), {"active", "inactive"}, "active")

    row = (
        InventoryStock.query.filter(
            InventoryStock.id == stock_id,
            InventoryStock.branch_id.in_(scope_ids),
        ).first()
        if stock_id
        else None
    )
    if row is None:
        return inventory_error("Không tìm thấy dòng tồn kho.")

    user = g.web_user
    if not user.is_super_admin and row.branch_id != g.active_branch_id:
        return inventory_error("Bạn không có quyền sửa tồn kho của chi nhánh này.", default_branch_id=g.active_branch_id)

    if user.is_super_admin:
        target_branch_id = branch_id_raw
        if target_branch_id not in scope_ids:
            return inventory_error("Chi nhánh không hợp lệ.", default_branch_id=row.branch_id)
    else:
        target_branch_id = row.branch_id

    if not item_name:
        return inventory_error("Tên sản phẩm không được để trống.", default_branch_id=row.branch_id)
    if not unit:
        return inventory_error("Đơn vị không được để trống.", default_branch_id=row.branch_id)

    if quantity_value is None:
        return inventory_error("Số lượng tồn kho phải là số nguyên.", default_branch_id=row.branch_id)
    if min_stock_value is None:
        return inventory_error("Mức tồn tối thiểu phải là số nguyên.", default_branch_id=row.branch_id)

    new_qty = Decimal(quantity_value)
    min_stock = Decimal(min_stock_value)

    if new_qty < 0:
        return inventory_error("Số lượng tồn kho không được âm.", default_branch_id=row.branch_id)
    if min_stock < 0:
        return inventory_error("Mức tồn tối thiểu không được âm.", default_branch_id=row.branch_id)

    old_qty = Decimal(str(row.quantity or 0))
    delta = new_qty - old_qty
    row.branch_id = target_branch_id
    row.quantity = new_qty
    row.item.name = item_name
    row.item.group_name = group_name
    row.item.unit = unit
    row.item.min_stock = min_stock
    row.item.status = status

    if delta != 0:
        db.session.add(
            InventoryTransaction(
                branch_id=target_branch_id,
                item_id=row.item_id,
                type="adjust",
                quantity=delta,
                note="Sửa dữ liệu kho",
            )
        )

    write_log(
        "update_inventory_stock",
        branch_id=target_branch_id,
        entity_type="inventory_stock",
        entity_id=row.id,
        message=f"Sửa kho cho sản phẩm {row.item.name}",
        details={
            "old_qty": format_integer_input(old_qty),
            "new_qty": format_integer_input(new_qty),
            "delta": format_integer_input(delta),
        },
    )

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return inventory_error(
            "Không thể lưu dữ liệu kho do trùng thông tin tồn kho hoặc tên sản phẩm.",
            default_branch_id=row.branch_id,
        )

    flash("Đã cập nhật tồn kho.", "success")
    return redirect_inventory_with_filters(default_branch_id=target_branch_id)


@web_bp.post("/inventory/stocks/delete")
@roles_required("super_admin", "branch_manager", "inventory_controller")
def inventory_stocks_delete():
    scope_ids = get_current_branch_scope()
    stock_id = parse_int(request.form.get("stock_id"))
    row = (
        InventoryStock.query.filter(
            InventoryStock.id == stock_id,
            InventoryStock.branch_id.in_(scope_ids),
        ).first()
        if stock_id
        else None
    )
    if row is None:
        return inventory_error("Không tìm thấy dòng tồn kho.")

    if not g.web_user.is_super_admin and row.branch_id != g.active_branch_id:
        return inventory_error("Bạn không có quyền xóa tồn kho của chi nhánh này.", default_branch_id=g.active_branch_id)

    branch_id = row.branch_id
    db.session.delete(row)
    db.session.commit()
    flash("Đã xóa dòng tồn kho.", "success")
    return redirect_inventory_with_filters(default_branch_id=branch_id)


@web_bp.post("/inventory/items/save")
@roles_required("super_admin")
def inventory_items_save():
    item_id = parse_int(request.form.get("item_id"))
    name = parse_text(request.form.get("name"))
    unit = parse_text(request.form.get("unit"))
    group_name = parse_optional_text(request.form.get("group_name"))
    min_stock_value = parse_int(request.form.get("min_stock"))
    status = normalize_choice(request.form.get("status"), {"active", "inactive"}, "active")

    if not name or not unit:
        return inventory_home_error("Tên sản phẩm và đơn vị không được để trống.")
    if min_stock_value is None or min_stock_value < 0:
        return inventory_home_error("Mức tồn tối thiểu phải là số nguyên không âm.")

    min_stock = Decimal(min_stock_value)

    if item_id:
        row = db.session.get(InventoryItem, item_id)
        if row is None:
            return inventory_home_error("Không tìm thấy sản phẩm kho.")
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
        return inventory_home_error("Tên sản phẩm kho đã tồn tại.")

    flash("Đã lưu danh mục sản phẩm kho.", "success")
    return redirect(url_for("web.inventory"))


@web_bp.post("/inventory/txn")
@roles_required("super_admin", "branch_manager", "inventory_controller")
def inventory_txn():
    scope_ids = get_current_branch_scope()
    item_id = parse_int(request.form.get("item_id"))
    tx_type = normalize_choice(request.form.get("type"), {"in", "out", "adjust"}, "")
    qty_value = parse_int(request.form.get("quantity"))
    note = parse_optional_text(request.form.get("note"))

    if g.web_user.is_super_admin:
        branch_id = parse_int(request.form.get("branch_id"))
    else:
        branch_id = g.active_branch_id

    if branch_id not in scope_ids:
        return inventory_home_error("Chi nhánh không hợp lệ.")
    if not tx_type:
        return inventory_home_error("Loại giao dịch kho không hợp lệ.")
    if qty_value is None or qty_value < 0:
        return inventory_home_error("Số lượng phải là số nguyên không âm.")

    qty_input = Decimal(qty_value)

    item = db.session.get(InventoryItem, item_id) if item_id else None
    if item is None:
        return inventory_home_error("Sản phẩm kho không hợp lệ.")

    if tx_type in {"in", "out"} and qty_input <= 0:
        return inventory_home_error("Số lượng nhập/xuất phải lớn hơn 0.")

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
        return inventory_home_error("Không thể xuất kho vượt số lượng hiện có.")

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
