from flask import g, redirect, render_template, request, url_for

from backend.logs import ACTION_LABELS
from backend.models import ActivityLog
from backend.web import (
    get_current_branch_scope,
    list_scope_branches,
    normalize_choice,
    paginate,
    parse_int,
    parse_page,
    parse_text,
    resolve_selected_branch_id,
    roles_required,
    web_bp,
)


@web_bp.get("/activity-logs")
@roles_required("super_admin", "branch_manager")
def activity_logs():
    scope_ids = get_current_branch_scope()
    if not scope_ids:
        return redirect(url_for("web.dashboard"))

    user = g.web_user
    q = parse_text(request.args.get("q"))
    action = normalize_choice(request.args.get("action"), set(ACTION_LABELS.keys()), "")
    page = parse_page(request.args.get("page"), default=1)

    if user.is_super_admin:
        selected_branch_id = resolve_selected_branch_id(scope_ids, parse_int(request.args.get("branch_id")))
        query = ActivityLog.query
        if selected_branch_id:
            query = query.filter(ActivityLog.branch_id == selected_branch_id)
    else:
        selected_branch_id = user.branch_id
        query = ActivityLog.query.filter(ActivityLog.branch_id == selected_branch_id)

    if q:
        keyword = f"%{q}%"
        query = query.filter(
            (ActivityLog.actor_username.ilike(keyword))
            | (ActivityLog.message.ilike(keyword))
            | (ActivityLog.action_label.ilike(keyword))
        )
    if action:
        query = query.filter(ActivityLog.action == action)

    pager = paginate(
        query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()),
        page=page,
        per_page=20,
    )

    branch_options = list_scope_branches(scope_ids, order_by="name") if user.is_super_admin else []

    return render_template(
        "web/activity_logs.html",
        rows=pager.items,
        pager=pager,
        q=q,
        action=action,
        selected_branch_id=selected_branch_id,
        branch_options=branch_options,
        action_labels=ACTION_LABELS,
        is_super_admin=user.is_super_admin,
    )
