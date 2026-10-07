import os
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp()
os.environ['SUROKKHA_DATABASE_URL'] = f"sqlite:///{Path(_tmp) / 'test.sqlite3'}"
os.environ['SUROKKHA_DEMO_MODE'] = 'true'

import pytest
from fastapi.testclient import TestClient
from app import seed
from app.main import app

seed.main()
PASSWORD, PIN = seed.CUSTOMER_PASSWORD, seed.CUSTOMER_PIN


def session(login, password, device='pytest-device'):
    client = TestClient(app, headers={'X-Device-Id': device})
    r = client.post('/api/auth/login', json={'login': login, 'password': password})
    assert r.status_code == 200, r.text
    return client


@pytest.fixture
def customer():
    c = session('01700000002', PASSWORD)
    c.post('/api/devices/trust', json={'pin': PIN})
    return c


@pytest.fixture
def analyst():
    return session('analyst', 'Analyst#2026')
