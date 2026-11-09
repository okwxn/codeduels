from pydantic import BaseModel


class CreateReq(BaseModel):
    difficulties: list[str] = ["easy"]
    topics: list[str] = []
    minutes: int = 10
    max_players: int = 2
    n_problems: int = 1
    end_mode: str = "grace"  # first | grace | timer
    grace: int = 120
    scoring: str = "speed"  # speed | tests | steps | space
