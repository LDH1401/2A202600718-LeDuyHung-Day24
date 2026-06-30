# tests/test_rbac.py
import pytest
from fastapi.testclient import TestClient

from src.access.rbac import enforcer
from src.api.main import app

client = TestClient(app)


def _h(token):
    return {"Authorization": f"Bearer {token}"} if token else {}


class TestEnforcer:
    @pytest.mark.parametrize("role,obj,act,expected", [
        ("admin", "patient_data", "read", True),
        ("admin", "patient_data", "delete", True),
        ("ml_engineer", "training_data", "read", True),
        ("ml_engineer", "patient_data", "read", False),
        ("ml_engineer", "production_data", "delete", False),
        ("data_analyst", "aggregated_metrics", "read", True),
        ("data_analyst", "patient_data", "read", False),
        ("intern", "sandbox_data", "write", True),
        ("intern", "patient_data", "read", False),
    ])
    def test_enforce(self, role, obj, act, expected):
        assert enforcer.enforce(role, obj, act) is expected


class TestApiRBAC:
    @pytest.mark.parametrize("method,path,token,expected", [
        ("GET", "/api/patients/raw", "token-alice", 200),
        ("GET", "/api/patients/raw", "token-bob", 403),
        ("GET", "/api/patients/raw", None, 401),
        ("GET", "/api/patients/raw", "token-invalid", 401),
        ("GET", "/api/patients/anonymized", "token-bob", 200),
        ("GET", "/api/patients/anonymized", "token-carol", 403),
        ("GET", "/api/metrics/aggregated", "token-carol", 200),
        ("GET", "/api/metrics/aggregated", "token-dave", 403),
        ("DELETE", "/api/patients/abc123", "token-alice", 200),
        ("DELETE", "/api/patients/abc123", "token-bob", 403),
    ])
    def test_endpoint(self, method, path, token, expected):
        r = client.request(method, path, headers=_h(token))
        assert r.status_code == expected

    def test_health(self):
        assert client.get("/health").status_code == 200
