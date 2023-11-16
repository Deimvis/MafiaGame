from pydantic import BaseModel

class User(BaseModel):
    username: str
    avatar: bytes | None
    sex: str | None
    email: str | None
