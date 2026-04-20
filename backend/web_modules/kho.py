from decimal import Decimal

from flask import g, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.logs import write_log
from backend.models import (
    InventoryItem,
    InventoryLot,
    InventoryStock,
    InventoryTransaction,
    Supplier,
    ensure_stock_row,
)
from backend.web import (
    collect_non_empty_text,
    get_current_branch_scope,
    list_scope_branches,
    normalize_choice,
    paginate,
    parse_int,
    parse_optional_text,
    parse_date,
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


def apply_inventory_filters(query, branch_column, selected_branch_id: int | None, q: str, group_name: str):
    if selected_branch_id:
        query = query.filter(branch_column == selected_branch_id)
    if q:
        query = query.filter(InventoryItem.name.ilike(f"%{q}%"))
    return query.filter(InventoryItem.group_name == group_name) if group_name else query


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

    stock_query = apply_inventory_filters(
        InventoryStock.query.join(InventoryItem, InventoryStock.item_id == InventoryItem.id).filter(InventoryStock.branch_id.in_(scope_ids)),
        InventoryStock.branch_id,
        selected_branch_id,
        q,
        group_name,
    )
    if low:
        stock_query = stock_query.filter(InventoryStock.quantity <= InventoryItem.min_stock)

    pager = paginate(stock_query.order_by(InventoryStock.id.asc()), page=page, per_page=12)

    tx_query = apply_inventory_filters(
        InventoryTransaction.query.join(InventoryItem, InventoryTransaction.item_id == InventoryItem.id).filter(InventoryTransaction.branch_id.in_(scope_ids)),
        InventoryTransaction.branch_id,
        selected_branch_id,
        q,
        group_name,
    )
    tx_rows = tx_query.order_by(InventoryTransaction.created_at.desc(), InventoryTransaction.id.desc()).limit(20).all()

    branch_options = list_scope_branches(scope_ids, order_by="id")
    group_rows = (
        db.session.query(InventoryItem.group_name)
        .filter(InventoryItem.group_name.isnot(None), InventoryItem.group_name != "")
        .distinct()
        .order_by(InventoryItem.group_name.asc())
        .all()
    )
    group_options = collect_non_empty_text(group_rows)

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

    form_branch_id = edit_stock.branch_id if edit_stock else selected_branch_id
    if form_branch_id is None and scope_ids:
        if user.is_super_admin:
            form_branch_id = scope_ids[0]
        else:
            form_branch_id = g.active_branch_id if g.active_branch_id in scope_ids else scope_ids[0]
    branch_name_map = {row.id: row.name for row in branch_options}

    stock_form_data = {
        "stock_id": edit_stock.id if edit_stock else None,
        "branch_id": form_branch_id,
        "branch_name": edit_stock.branch.name if edit_stock and edit_stock.branch else branch_name_map.get(form_branch_id, "-"),
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
    if not scope_ids:
        return inventory_error("Tài khoản không có phạm vi chi nhánh hợp lệ.")

    user = g.web_user
    stock_id = parse_int(request.form.get("stock_id"))
    branch_id_raw = parse_int(request.form.get("branch_id"))
    item_name = parse_text(request.form.get("item_name"))
    group_choice = parse_text(request.form.get("group_name"))
    new_group_name = parse_optional_text(request.form.get("new_group_name"))
    unit = parse_text(request.form.get("unit"))
    quantity_value = parse_int(request.form.get("quantity"))
    min_stock_value = parse_int(request.form.get("min_stock"))
    status = normalize_choice(request.form.get("status"), {"active", "inactive"}, "active")

    if group_choice == "__new__":
        if not new_group_name:
            return inventory_error("Vui lòng nhập tên nhóm mới hoặc chọn nhóm có sẵn.")
        group_name = new_group_name
    else:
        group_name = parse_optional_text(group_choice)

    if user.is_super_admin:
        target_branch_id = branch_id_raw
        if target_branch_id not in scope_ids:
            return inventory_error("Chi nhánh không hợp lệ.")
    else:
        target_branch_id = g.active_branch_id
        if target_branch_id not in scope_ids:
            return inventory_error("Chi nhánh không hợp lệ.")

    if not item_name:
        return inventory_error("Tên sản phẩm không được để trống.", default_branch_id=target_branch_id)
    if not unit:
        return inventory_error("Đơn vị không được để trống.", default_branch_id=target_branch_id)

    if quantity_value is None:
        return inventory_error("Số lượng tồn kho phải là số nguyên.", default_branch_id=target_branch_id)
    if min_stock_value is None:
        return inventory_error("Mức tồn tối thiểu phải là số nguyên.", default_branch_id=target_branch_id)

    new_qty = Decimal(quantity_value)
    min_stock = Decimal(min_stock_value)

    if new_qty < 0:
        return inventory_error("Số lượng tồn kho không được âm.", default_branch_id=target_branch_id)
    if min_stock < 0:
        return inventory_error("Mức tồn tối thiểu không được âm.", default_branch_id=target_branch_id)

    row = (
        InventoryStock.query.filter(
            InventoryStock.id == stock_id,
            InventoryStock.branch_id.in_(scope_ids),
        ).first()
        if stock_id
        else None
    )
    if stock_id and row is None:
        return inventory_error("Không tìm thấy dòng tồn kho.", default_branch_id=target_branch_id)

    if row is not None and not user.is_super_admin and row.branch_id != g.active_branch_id:
        return inventory_error("Bạn không có quyền sửa tồn kho của chi nhánh này.", default_branch_id=g.active_branch_id)
    if row is not None and not user.is_super_admin:
        target_branch_id = row.branch_id

    created = row is None
    if created:
        item = InventoryItem.query.filter_by(name=item_name).first()
        if item is None:
            item = InventoryItem(name=item_name)
            db.session.add(item)
            db.session.flush()

        duplicate_stock = InventoryStock.query.filter_by(branch_id=target_branch_id, item_id=item.id).first()
        if duplicate_stock is not None:
            return inventory_error(
                "Sản phẩm đã có trong chi nhánh này. Vui lòng bấm Sửa ở danh sách để cập nhật.",
                default_branch_id=target_branch_id,
            )

        row = InventoryStock(branch_id=target_branch_id, item_id=item.id, quantity=new_qty)
        db.session.add(row)
        old_qty = Decimal("0")
    else:
        item = row.item
        old_qty = Decimal(str(row.quantity or 0))
        if target_branch_id != row.branch_id:
            duplicate_stock = InventoryStock.query.filter_by(branch_id=target_branch_id, item_id=row.item_id).first()
            if duplicate_stock is not None and duplicate_stock.id != row.id:
                return inventory_error(
                    "Sản phẩm đã có trong chi nhánh đích, không thể chuyển dòng kho.",
                    default_branch_id=row.branch_id,
                )
        row.branch_id = target_branch_id
        row.quantity = new_qty

    item.name = item_name
    item.group_name = group_name
    item.unit = unit
    item.min_stock = min_stock
    item.status = status

    delta = new_qty - old_qty
    if delta != 0:
        db.session.add(
            InventoryTransaction(
                branch_id=target_branch_id,
                item_id=row.item_id,
                type="adjust",
                quantity=delta,
                note="Cập nhật từ biểu mẫu sản phẩm kho",
            )
        )

    db.session.flush()
    write_log(
        "update_inventory_stock",
        branch_id=target_branch_id,
        entity_type="inventory_stock",
        entity_id=row.id,
        message=f"{'Thêm' if created else 'Sửa'} kho cho sản phẩm {row.item.name}",
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
            default_branch_id=target_branch_id,
        )

    flash("Đã thêm sản phẩm kho." if created else "Đã cập nhật tồn kho.", "success")
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
        return inventory_error("Tên sản phẩm và đơn vị không được để trống.")
    if min_stock_value is None or min_stock_value < 0:
        return inventory_error("Mức tồn tối thiểu phải là số nguyên không âm.")

    min_stock = Decimal(min_stock_value)

    if item_id:
        row = db.session.get(InventoryItem, item_id)
        if row is None:
            return inventory_error("Không tìm thấy sản phẩm kho.")
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
        return inventory_error("Tên sản phẩm kho đã tồn tại.")

    flash("Đã lưu danh mục sản phẩm kho.", "success")
    return redirect(url_for("web.inventory"))


@web_bp.post("/inventory/txn")
@roles_required("super_admin", "branch_manager", "inventory_controller")
def inventory_txn():
    scope_ids = get_current_branch_scope()
    item_id = parse_int(request.form.get("item_id"))
    qty_value = parse_int(request.form.get("quantity"))
    note = parse_optional_text(request.form.get("note"))
    supplier_name = parse_optional_text(request.form.get("supplier_name"))
    lot_code = parse_optional_text(request.form.get("lot_code"))
    expiry_date = parse_date(request.form.get("expiry_date"))

    if g.web_user.is_super_admin:
        branch_id = parse_int(request.form.get("branch_id"))
    else:
        branch_id = g.active_branch_id

    if branch_id not in scope_ids:
        return inventory_error("Chi nhánh không hợp lệ.")
    if qty_value is None or qty_value < 0:
        return inventory_error("Số lượng phải là số nguyên không âm.")

    qty_input = Decimal(qty_value)

    item = db.session.get(InventoryItem, item_id) if item_id else None
    if item is None:
        return inventory_error("Sản phẩm kho không hợp lệ.")

    supplier = None
    if supplier_name:
        supplier = Supplier.query.filter(Supplier.name.ilike(supplier_name)).first()
        if supplier is None:
            supplier = Supplier(name=supplier_name, status="active")
            db.session.add(supplier)
            db.session.flush()

    stock = ensure_stock_row(branch_id, item.id)
    current_qty = Decimal(str(stock.quantity or 0))
    new_qty = qty_input
    delta = new_qty - current_qty

    if new_qty < 0:
        return inventory_error("Không thể xuất kho vượt số lượng hiện có.")

    stock.quantity = new_qty

    if lot_code:
        lot = InventoryLot.query.filter_by(branch_id=branch_id, item_id=item.id, lot_code=lot_code).first()
        if lot is None:
            lot = InventoryLot(
                branch_id=branch_id,
                item_id=item.id,
                lot_code=lot_code,
                quantity=Decimal("0.00"),
            )
            db.session.add(lot)
        lot.supplier_id = supplier.id if supplier else lot.supplier_id
        lot.expiry_date = expiry_date or lot.expiry_date
        lot.quantity = qty_input

    db.session.add(
        InventoryTransaction(
            branch_id=branch_id,
            item_id=item.id,
            supplier_id=supplier.id if supplier else None,
            source_branch_id=None,
            target_branch_id=None,
            type="adjust",
            quantity=delta,
            lot_code=lot_code,
            expiry_date=expiry_date,
            supplier_name=supplier.name if supplier else supplier_name,
            note=note,
        )
    )
    db.session.flush()
    write_log(
        "inventory_transaction",
        branch_id=branch_id,
        entity_type="inventory_transaction",
        entity_id=None,
        message=f"Cập nhật kho {item.name}",
        details={"type": "adjust", "qty": str(qty_input)},
    )
    db.session.commit()
    flash("Đã cập nhật tồn kho.", "success")
    return redirect(url_for("web.inventory"))
