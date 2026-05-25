import io


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["price_provider"] in {"synthetic", "yfinance"}


def test_login_required(client):
    assert client.get("/api/portfolios").status_code == 401


def test_manager_sees_only_own_portfolios(client, manager1_headers):
    resp = client.get("/api/portfolios", headers=manager1_headers)
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()}
    assert names == {"Alpha Fund"}  # not Beta Fund


def test_admin_sees_all_portfolios(client, admin_headers):
    resp = client.get("/api/portfolios", headers=admin_headers)
    names = {p["name"] for p in resp.json()}
    assert {"Alpha Fund", "Beta Fund"} <= names


def test_portfolio_isolation_blocks_cross_access(client, manager1_headers, admin_headers):
    beta = next(
        p for p in client.get("/api/portfolios", headers=admin_headers).json()
        if p["name"] == "Beta Fund"
    )
    resp = client.get(f"/api/portfolios/{beta['id']}/signals", headers=manager1_headers)
    assert resp.status_code == 404  # existence not leaked


def test_signals_have_bsh_and_drivers(client, manager1_headers):
    pid = client.get("/api/portfolios", headers=manager1_headers).json()[0]["id"]
    rows = client.get(f"/api/portfolios/{pid}/signals", headers=manager1_headers).json()
    assert len(rows) > 0
    for row in rows:
        assert row["signal"] in {"BUY", "SELL", "HOLD"}
        assert len(row["drivers"]) >= 2  # Phase 1 exit criterion
        assert len(row["signal_trace"]) >= 1


def test_rules_update_is_audited(client, manager1_headers):
    pid = client.get("/api/portfolios", headers=manager1_headers).json()[0]["id"]
    client.put(
        f"/api/portfolios/{pid}/rules",
        headers=manager1_headers,
        json={"confidence_floor": 65.0},
    )
    audit = client.get(
        f"/api/portfolios/{pid}/rules/audit", headers=manager1_headers
    ).json()
    assert any(a["parameter"] == "confidence_floor" for a in audit)


def test_data_quality_admin_only(client, manager1_headers, admin_headers):
    assert client.get("/api/ingestion/quality", headers=manager1_headers).status_code == 403
    resp = client.get("/api/ingestion/quality", headers=admin_headers)
    assert resp.status_code == 200
    assert "success_rate" in resp.json()


def test_upload_quarantines_bad_file(client, manager1_headers):
    pid = client.get("/api/portfolios", headers=manager1_headers).json()[0]["id"]
    bad = io.BytesIO(b"foo,bar\n1,2\n")
    resp = client.post(
        f"/api/ingestion/{pid}/upload",
        headers=manager1_headers,
        files={"file": ("bad.csv", bad, "text/csv")},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "QUARANTINED"
