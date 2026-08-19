"""End-to-end check of login, schedule, autosave, analysis, and exports."""

import asyncio
from collections.abc import Generator

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from apps.service.prisma_service.main import create_app
from apps.service.prisma_service.seed import seed_database
from prisma.persistence.database import Base, get_database_session
from prisma.persistence.models import AnalysisResult, ComparisonResponse, TestSession as StoredTestSession


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from apps.service.prisma_service import seed, storage
    monkeypatch.setattr(seed, "COLLECTION_STORAGE_ROOT", tmp_path)
    monkeypatch.setattr(storage, "COLLECTION_STORAGE_ROOT", tmp_path)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as database:
        seed_database(database)

    def dependency() -> Generator[Session, None, None]:
        with factory() as database:
            yield database

    app = create_app()
    app.dependency_overrides[get_database_session] = dependency

    async def request(method: str, path: str, **kwargs):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http:
            return await http.request(method, path, **kwargs)

    login = asyncio.run(request("POST", "/api/v1/auth/login", json={"login": "user", "password": "user1234"}))
    token = login.json()["access_token"]

    def send(method: str, path: str, **kwargs):
        headers = {"Authorization": f"Bearer {token}"}
        headers.update(kwargs.pop("headers", {}))
        return asyncio.run(request(method, path, headers=headers, **kwargs))

    yield send, factory
    engine.dispose()


def test_complete_desktop_experiment(client) -> None:
    api, factory = client
    tests = api("GET", "/api/v1/tests").json()
    created = api("POST", "/api/v1/sessions", json={
        "collection_id": tests[0]["id"], "random_seed": "reproducible-test"
    })
    assert created.status_code == 201
    session = created.json()
    assert session["training_total"] == 3
    assert session["main_total"] == 30

    seen_main_pairs = set()
    while session["status"] == "training":
        session = api("POST", f'/api/v1/sessions/{session["id"]}/present').json()
        pair = session["next_comparison"]
        session = api("POST", f'/api/v1/sessions/{session["id"]}/responses/{pair["presentation_index"]}',
                      json={"selected_item_id": pair["left_item_id"], "reaction_time_ms": 125.25}).json()
    assert session["status"] == "ready"
    session = api("POST", f'/api/v1/sessions/{session["id"]}/start').json()

    while session["status"] == "in_progress":
        session = api("POST", f'/api/v1/sessions/{session["id"]}/present').json()
        pair = session["next_comparison"]
        unordered = (pair["level_index"], *sorted((pair["left_type_id"], pair["right_type_id"])))
        assert unordered not in seen_main_pairs
        seen_main_pairs.add(unordered)
        session = api("POST", f'/api/v1/sessions/{session["id"]}/responses/{pair["presentation_index"]}',
                      json={"selected_item_id": pair["left_item_id"],
                            "reaction_time_ms": 100 + pair["presentation_index"]}).json()

    assert session["status"] == "completed"
    assert session["analysis"]["algorithm_version"].startswith("prisma-analytics/")
    assert len(seen_main_pairs) == 30
    detail = api("GET", f'/api/v1/sessions/{session["id"]}?trace=true').json()
    assert len(detail["comparisons"]) == 33
    assert api("GET", f'/api/v1/sessions/{session["id"]}/report.pdf').content.startswith(b"%PDF")
    assert api("GET", f'/api/v1/sessions/{session["id"]}/report.xlsx').content.startswith(b"PK")

    with factory() as database:
        assert database.query(StoredTestSession).count() == 1
        assert database.query(ComparisonResponse).count() == 33
        assert database.query(AnalysisResult).count() == 1
