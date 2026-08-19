"""HTTP facade for the complete Desktop test workflow."""

from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from prisma.persistence.database import get_database_session
from ..auth import account_role_names, current_account
from ..models.experiment import ResponseWrite, SessionCreate
from ..reports import build_admin_xlsx, build_session_pdf, build_session_xlsx
from ..services.experiment_service import (
    ExperimentError, create_test_session, get_test_session, list_available_collections,
    list_test_sessions, present_next, save_response, start_main_test,
)


router = APIRouter(tags=["experiments"])


def _translate(action):
    try:
        return action()
    except ExperimentError as error:
        raise HTTPException(422, str(error)) from error


@router.get("/tests")
def available_tests(database: Session = Depends(get_database_session), _=Depends(current_account)):
    return list_available_collections(database)


@router.post("/sessions", status_code=201)
def create_session(payload: SessionCreate, database: Session = Depends(get_database_session),
                   account=Depends(current_account)):
    return _translate(lambda: create_test_session(database, account.id, payload.collection_id, payload.random_seed))


@router.get("/sessions")
def sessions(database: Session = Depends(get_database_session), account=Depends(current_account)):
    return list_test_sessions(database, account.id, "ADMIN" in account_role_names(account))


@router.get("/sessions/{session_id}")
def session_detail(session_id: str, trace: bool = False,
                   database: Session = Depends(get_database_session), account=Depends(current_account)):
    return _translate(lambda: get_test_session(database, session_id, account.id,
                      "ADMIN" in account_role_names(account), trace))


@router.post("/sessions/{session_id}/present")
def present(session_id: str, database: Session = Depends(get_database_session), account=Depends(current_account)):
    return _translate(lambda: present_next(database, session_id, account.id))


@router.post("/sessions/{session_id}/start")
def start(session_id: str, database: Session = Depends(get_database_session), account=Depends(current_account)):
    return _translate(lambda: start_main_test(database, session_id, account.id))


@router.post("/sessions/{session_id}/responses/{presentation_index}")
def respond(session_id: str, presentation_index: int, payload: ResponseWrite,
            database: Session = Depends(get_database_session), account=Depends(current_account)):
    return _translate(lambda: save_response(database, session_id, presentation_index,
                      account.id, payload.selected_item_id, payload.reaction_time_ms, payload.timed_out))


def _download(content: bytes, media_type: str, filename: str) -> StreamingResponse:
    return StreamingResponse(BytesIO(content), media_type=media_type, headers={
        "Content-Disposition": f'attachment; filename="{filename}"'
    })


@router.get("/sessions/{session_id}/report.pdf")
def session_pdf(session_id: str, database: Session = Depends(get_database_session),
                account=Depends(current_account)):
    payload = _translate(lambda: get_test_session(database, session_id, account.id,
                         "ADMIN" in account_role_names(account), True))
    return _download(build_session_pdf(payload), "application/pdf", f"prisma-{session_id}.pdf")


@router.get("/sessions/{session_id}/report.xlsx")
def session_xlsx(session_id: str, database: Session = Depends(get_database_session),
                 account=Depends(current_account)):
    payload = _translate(lambda: get_test_session(database, session_id, account.id,
                         "ADMIN" in account_role_names(account), True))
    return _download(build_session_xlsx(payload),
                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     f"prisma-{session_id}.xlsx")


@router.get("/admin/sessions.xlsx")
def admin_xlsx(database: Session = Depends(get_database_session), account=Depends(current_account)):
    if "ADMIN" not in account_role_names(account):
        raise HTTPException(403, "Требуются права администратора.")
    summaries = list_test_sessions(database, account.id, True)
    sessions_with_trace = [get_test_session(database, item["id"], account.id, True, True)
                           for item in summaries]
    return _download(build_admin_xlsx(sessions_with_trace),
                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     "prisma-research-export.xlsx")
