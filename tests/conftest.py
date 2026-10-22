import pytest

from coldroom import create_app

BASE = "http://127.0.0.1:5000"
TOKEN = "test-operator-token-0123456789abcdefghij"
WRONG_TOKEN = "wrong-secret-xyz-9876543210"
JSON = "application/json"


class FakeClock:
    def __init__(self, start: float = 1000.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class Api:
    """Test client that always talks to the legitimate local address."""

    def __init__(self, app):
        self.app = app
        self.ctx = app.extensions["coldroom"]
        self._client = app.test_client()

    def get(self, path, **kw):
        kw.setdefault("base_url", BASE)
        return self._client.get(path, **kw)

    def post(self, path, **kw):
        kw.setdefault("base_url", BASE)
        return self._client.post(path, **kw)

    def options(self, path, **kw):
        kw.setdefault("base_url", BASE)
        return self._client.options(path, **kw)

    def set(self, body, token=None, content_type=JSON, headers=None, **kw):
        h = dict(headers or {})
        if token:
            h["Authorization"] = f"Bearer {token}"
        if content_type:
            kw["content_type"] = content_type
        return self.post("/api/setpoint", data=body, headers=h, **kw)

    def status(self):
        return self.get("/api/status").get_json()

    def setpoint(self):
        return self.status()["simulation"]["setpoint_c"]


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def protected(clock):
    return Api(create_app(insecure=False, operator_token=TOKEN, clock=clock))


@pytest.fixture
def insecure(clock):
    return Api(create_app(insecure=True, clock=clock))


@pytest.fixture(params=["protected", "insecure"])
def either(request, clock):
    """(api, token) for both modes, so shared validation is tested in each."""
    if request.param == "protected":
        return Api(create_app(insecure=False, operator_token=TOKEN, clock=clock)), TOKEN
    return Api(create_app(insecure=True, clock=clock)), None
