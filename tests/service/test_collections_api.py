import asyncio
import base64
from collections.abc import Generator

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from apps.service.prisma_service import storage
from apps.service.prisma_service.main import create_app
from apps.service.prisma_service.seed import seed_database
from prisma.persistence.database import Base, get_database_session
from prisma.persistence.models import Collection, CollectionItem


ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@pytest.fixture()
def api(tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    from apps.service.prisma_service import seed
    original_storage_root = storage.COLLECTION_STORAGE_ROOT
    original_seed_root = seed.COLLECTION_STORAGE_ROOT
    storage.COLLECTION_STORAGE_ROOT = tmp_path
    seed.COLLECTION_STORAGE_ROOT = tmp_path
    with session_factory() as session:
        seed_database(session)
    app = create_app()
    app.dependency_overrides[get_database_session] = override_session

    async def request(method: str, path: str, **kwargs) -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    login = asyncio.run(request("POST", "/api/v1/auth/login", json={"login": "admin", "password": "admin123"}))
    token = login.json()["access_token"]

    def authenticated_request(method: str, path: str, **kwargs):
        headers = {"Authorization": f"Bearer {token}"}
        headers.update(kwargs.pop("headers", {}))
        return asyncio.run(request(method, path, headers=headers, **kwargs))

    yield authenticated_request
    storage.COLLECTION_STORAGE_ROOT = original_storage_root
    seed.COLLECTION_STORAGE_ROOT = original_seed_root
    engine.dispose()


def draft_payload() -> dict:
    return {
        "name": "Тестовая коллекция",
        "width": 2,
        "depth": 5,
        "time_mode": "timeout_mark",
        "time_limit_ms": 5000,
        "rows": [
            {"row_index": 1, "type_name": "Врач"},
            {"row_index": 2, "type_name": "Инженер"},
        ],
    }


def test_even_depth_is_rejected_at_editor_boundary(api) -> None:
    payload = draft_payload()
    payload["depth"] = 4
    response = api("POST", "/api/v1/collections", json=payload)
    assert response.status_code == 422
    assert "нечётным" in response.text


def test_incomplete_draft_cannot_be_activated(api) -> None:
    created = api("POST", "/api/v1/collections", json=draft_payload())
    assert created.status_code == 201
    collection = created.json()
    assert not collection["activation"]["can_activate"]

    activated = api("POST", f"/api/v1/collections/{collection['id']}/activate")
    assert activated.status_code == 422
    assert "Не загружены изображения" in activated.text

    # Re-saving Cyrillic type names must reuse existing StimulusType records.
    updated = api("PUT", f"/api/v1/collections/{collection['id']}", json=draft_payload())
    assert updated.status_code == 200
    assert [row["type_name"] for row in updated.json()["rows"]] == ["Врач", "Инженер"]


def test_complete_grid_can_be_activated_and_is_persisted(api) -> None:
    collection = api("POST", "/api/v1/collections", json=draft_payload()).json()
    collection_id = collection["id"]

    for row_index in (1, 2):
        for level_index in range(1, 6):
            response = api(
                "POST",
                f"/api/v1/collections/{collection_id}/rows/{row_index}/levels/{level_index}/image",
                files={"image": ("test.png", ONE_PIXEL_PNG, "image/png")},
            )
            assert response.status_code == 200

    activated = api("POST", f"/api/v1/collections/{collection_id}/activate")
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True
    assert activated.json()["activation"]["can_activate"] is True

    listed = api("GET", "/api/v1/collections")
    assert listed.status_code == 200
    assert any(item["id"] == collection_id for item in listed.json())


def test_seed_is_idempotent_and_creates_complete_collection(tmp_path, monkeypatch) -> None:
    from apps.service.prisma_service import seed

    monkeypatch.setattr(seed, "COLLECTION_STORAGE_ROOT", tmp_path)
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_database(session)
        seed_database(session)
        assert session.query(Collection).count() == 1
        assert session.query(CollectionItem).count() == 20
        collection = session.get(Collection, "demo-professions")
        assert collection is not None and collection.is_active
    assert len(list(tmp_path.rglob("*.svg"))) == 20
