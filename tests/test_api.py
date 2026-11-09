import pytest
from fastapi.testclient import TestClient

from server.main import app
from server.registry import rooms


@pytest.fixture
def client():
    rooms.clear()
    return TestClient(app)


def test_topics_not_empty(client):
    assert client.get("/api/topics").json()


def test_create_room(client):
    r = client.post("/api/rooms", json={"difficulties": ["easy"], "minutes": 5})
    assert r.status_code == 200
    assert len(r.json()["code"]) == 6


def test_unknown_topic_is_400(client):
    r = client.post(
        "/api/rooms", json={"difficulties": ["easy"], "topics": ["no-such-topic"]}
    )
    assert r.status_code == 400


def test_two_players_join_and_start(client):
    body = {"difficulties": ["easy", "medium", "hard"]}
    code = client.post("/api/rooms", json=body).json()["code"]
    with (
        client.websocket_connect(f"/ws?room={code}&pid=a&name=A") as a,
        client.websocket_connect(f"/ws?room={code}&pid=b&name=B") as b,
    ):
        assert a.receive_json()["state"] == "lobby"
        a.receive_json()  # update sent when B joins
        assert b.receive_json()["state"] == "lobby"
        a.send_json({"type": "start"})
        assert a.receive_json()["state"] == "running"
        assert b.receive_json()["state"] == "running"


def test_unknown_room(client):
    with client.websocket_connect("/ws?room=nope&pid=a&name=A") as ws:
        assert ws.receive_json()["type"] == "gone"
