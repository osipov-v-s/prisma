"""Report facade used by IPC handlers.

Binary content is base64-encoded because the worker protocol is JSON-lines.
"""

import base64

from src.core.models import Account
from .experiments import get_session, list_sessions
from .report_pdf import build_session_pdf
from .report_xlsx import build_admin_xlsx, build_session_xlsx


def session_pdf(session_id: str, account: Account) -> str:
    session = get_session(session_id, account.id, "ADMIN" in account.roles, True)
    return _encode(build_session_pdf(session))


def session_xlsx(session_id: str, account: Account) -> str:
    session = get_session(session_id, account.id, "ADMIN" in account.roles, True)
    return _encode(build_session_xlsx(session))


def admin_xlsx(account: Account) -> str:
    if "ADMIN" not in account.roles:
        raise ValueError("Требуются права администратора.")
    sessions = [get_session(item["id"], account.id, True, True)
                for item in list_sessions(account)]
    return _encode(build_admin_xlsx(sessions))


def _encode(content: bytes) -> str:
    return base64.b64encode(content).decode("ascii")
