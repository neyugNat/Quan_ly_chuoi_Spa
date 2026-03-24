from flask import request
from flask_jwt_extended import get_jwt


def get_allowed_branch_ids():
    claims = get_jwt() or {}
    branch_ids = claims.get("branch_ids") or []

    try:
        claim_branch_ids = [int(b) for b in branch_ids]
    except Exception:
        claim_branch_ids = []

    roles = claims.get("roles") or []
    if isinstance(roles, str):
        roles = [roles]

    if "super_admin" in roles:
        try:
            from backend.models.branch import Branch

            return [branch_id for (branch_id,) in Branch.query.with_entities(Branch.id).order_by(Branch.id.asc()).all()]
        except Exception:
            return claim_branch_ids

    return claim_branch_ids


def get_current_branch_id():
    allowed = get_allowed_branch_ids()
    if not allowed:
        return None, {"error": "no_branch_scope"}, 403

    header = request.headers.get("X-Branch-Id")
    if header:
        try:
            branch_id = int(header)
        except ValueError:
            return None, {"error": "invalid_branch_id"}, 400
        if branch_id not in allowed:
            return None, {"error": "forbidden_branch"}, 403
        return branch_id, None, None

    if len(allowed) == 1:
        return allowed[0], None, None
    if len(allowed) > 1:
        return None, {"error": "branch_required", "allowed_branch_ids": allowed}, 400
    return None, {"error": "no_branch_scope"}, 403
