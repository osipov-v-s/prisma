"""Small method registry exposed to Electron through the Python worker."""

from typing import Any, Callable

from prisma.analytics import ALGORITHM_VERSION
from src.db.migrate import migrate, schema_version
from . import auth, collections, experiments, reports


def initialize() -> None:
    """Prepare the database and deterministic prototype data once per worker."""

    migrate()
    auth.seed_accounts()
    collections.seed_collection()


def handle(method: str, params: dict[str, Any]) -> Any:
    """Validate authentication once, then call one direct service function."""

    if method == "health":
        return {"status": "ok", "service": "ПРИЗМА Desktop Worker",
                "service_version": "2.0.0", "analytics_version": ALGORITHM_VERSION,
                "schema_version": schema_version()}
    if method == "auth.login":
        return auth.login(params["login"], params["password"])
    if method == "auth.logout":
        auth.logout(params.get("token", ""))
        return None

    account = auth.verify_token(params.get("token", ""), method.startswith(("collections.", "users.")))
    return _authenticated(method, params, account)


def _authenticated(method: str, params: dict, account) -> Any:
    actions: dict[str, Callable[[], Any]] = {
        "auth.me": lambda: account.to_dict(),
        "collections.list": collections.list_collections,
        "collections.create": lambda: collections.create_collection(params["data"]),
        "collections.update": lambda: collections.update_collection(params["collection_id"], params["data"]),
        "collections.activate": lambda: collections.set_active(params["collection_id"], True),
        "collections.deactivate": lambda: collections.set_active(params["collection_id"], False),
        "collections.upload": lambda: collections.assign_image(
            params["collection_id"], params["row_index"], params["level_index"],
            params["content_type"], params["content_base64"]),
        "users.list": auth.list_users,
        "users.create": lambda: auth.create_user(params["data"]),
        "users.delete": lambda: auth.delete_user(params["account_id"], account.id),
        "tests.list": experiments.available_tests,
        "sessions.create": lambda: experiments.create_session(
            account.id, params["collection_id"], params.get("random_seed")),
        "sessions.list": lambda: experiments.list_sessions(account),
        "sessions.get": lambda: experiments.get_session(
            params["session_id"], account.id, "ADMIN" in account.roles, params.get("trace", False)),
        "sessions.present": lambda: experiments.present_next(params["session_id"], account.id),
        "sessions.start": lambda: experiments.start_main(params["session_id"], account.id),
        "sessions.respond": lambda: experiments.save_response(
            params["session_id"], params["presentation_index"], account.id, params["data"]),
        "reports.pdf": lambda: reports.session_pdf(params["session_id"], account),
        "reports.xlsx": lambda: reports.session_xlsx(params["session_id"], account),
        "reports.admin_xlsx": lambda: reports.admin_xlsx(account),
    }
    action = actions.get(method)
    if action is None:
        raise ValueError(f"Неизвестный Desktop-метод: {method}")
    return action()
