from server.models import CreateReq
from server.room import Room


class FakeWS:
    def __init__(self):
        self.sent = []

    async def send_text(self, data):
        self.sent.append(data)


class BadWS:
    async def send_text(self, data):
        raise RuntimeError("closed")


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


def problem(i, n_tests=3):
    return {
        "id": f"p{i}",
        "title": f"Prob{i}",
        "difficulty": "easy",
        "tags": ["array"],
        "tests": [{}] * n_tests,
    }


def make_room(clock, n_players=2, **cfg):
    room = Room([problem(i) for i in range(5)], CreateReq(**cfg), clock=clock)
    for i in range(n_players):
        room.players[f"p{i}"] = {"name": f"P{i}", "ws": FakeWS(), "prog": {}}
    room.host = "p0"
    return room
