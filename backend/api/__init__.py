# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnusedImport=false

from flask import Blueprint

api_bp = Blueprint("api", __name__, url_prefix="/api")

from . import auth  # noqa: E402,F401
from . import audit_logs  # noqa: E402,F401
from . import appointments  # noqa: E402,F401
from . import branches  # noqa: E402,F401
from . import commission_records  # noqa: E402,F401
from . import customers  # noqa: E402,F401
from . import customer_packages  # noqa: E402,F401
from . import health  # noqa: E402,F401
from . import invoices  # noqa: E402,F401
from . import inventory_items  # noqa: E402,F401
from . import packages  # noqa: E402,F401
from . import payments  # noqa: E402,F401
from . import reports  # noqa: E402,F401
from . import resources  # noqa: E402,F401
from . import services  # noqa: E402,F401
from . import shifts  # noqa: E402,F401
from . import staffs  # noqa: E402,F401
from . import stock_transactions  # noqa: E402,F401
from . import users  # noqa: E402,F401
