import asyncio

import httpx

from apps.service.prisma_service.main import create_app


def request(method: str, path: str, **kwargs) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def test_health_reports_analytics_version() -> None:
    response = request("GET", "/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["analytics_version"].startswith("prisma-analytics/")


def test_demo_runs_both_analysis_modes() -> None:
    response = request("GET", "/api/v1/analysis/demo")
    assert response.status_code == 200
    payload = response.json()
    assert payload["choice_only"]["status"] == "calculated"
    assert payload["choice_and_time"]["status"] == "calculated"
    assert len(payload["source_responses"]) == 30


def test_invalid_payload_returns_validation_error() -> None:
    response = request(
        "POST",
        "/api/v1/analysis/compare",
        json={
            "collection": {
                "collection_id": "bad",
                "depth": 4,
                "types": [],
                "items": [],
            },
            "responses": [],
        },
    )
    assert response.status_code == 422
