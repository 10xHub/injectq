from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from injectq import InjectQ, inject, singleton
from injectq.integrations.fastapi import InjectFastAPI, setup_fastapi


@singleton
class UserRepo:
    def __init__(self) -> None:
        self.users = {}

    def add_user(self, user_id: str, user_data: dict) -> None:
        self.users[user_id] = user_data

    def get_user(self, user_id: str) -> dict | None:
        return self.users.get(user_id)

    def delete_user(self, user_id: str) -> None:
        if user_id in self.users:
            del self.users[user_id]


@singleton
class UserService:
    @inject
    def __init__(self, user_repo: UserRepo) -> None:
        self.user_repo = user_repo

    def create_user(self, user_id: str, user_data: dict) -> None:
        self.user_repo.add_user(user_id, user_data)

    def retrieve_user(self, user_id: str) -> dict | None:
        return self.user_repo.get_user(user_id)

    def remove_user(self, user_id: str) -> None:
        self.user_repo.delete_user(user_id)


app = FastAPI()
container = InjectQ.get_instance()
setup_fastapi(container, app)


@app.post("/users/{user_id}")
def create_user(
    user_id: str,
    user_service: Annotated[UserService, InjectFastAPI(UserService)],
) -> dict:
    user_service.create_user(user_id, {"name": "John Doe"})
    return {"message": "User created successfully"}


@app.get("/users/{user_id}")
def get_user(
    user_id: str,
    user_service: Annotated[UserService, InjectFastAPI(UserService)],
) -> dict:
    user = user_service.retrieve_user(user_id)
    if user:
        return user
    raise HTTPException(status_code=404, detail="User not found")


def test_create_user():
    client = TestClient(app)
    response = client.post("/users/123")
    assert response.status_code == 200
    assert response.json() == {"message": "User created successfully"}


def test_get_user():
    client = TestClient(app)
    client.post("/users/123")  # Ensure user exists
    response = client.get("/users/123")
    assert response.status_code == 200
    assert response.json() == {"name": "John Doe"}


def test_get_user_not_found():
    client = TestClient(app)
    response = client.get("/users/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
