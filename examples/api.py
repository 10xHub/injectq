from typing import Annotated

from fastapi import FastAPI, HTTPException

from injectq import InjectQ, inject, singleton
from injectq.integrations import InjectAPI, setup_fastapi


@singleton
class UserRepo:
    def __init__(self) -> None:
        self.users = {}

    def add_user(self, user_id, user_data):
        self.users[user_id] = user_data

    def get_user(self, user_id):
        return self.users.get(user_id)

    def delete_user(self, user_id):
        if user_id in self.users:
            del self.users[user_id]


@singleton
class UserService:
    @inject
    def __init__(self, user_repo: UserRepo) -> None:
        self.user_repo = user_repo

    def create_user(self, user_id, user_data):
        self.user_repo.add_user(user_id, user_data)

    def retrieve_user(self, user_id):
        return self.user_repo.get_user(user_id)

    def remove_user(self, user_id):
        self.user_repo.delete_user(user_id)


app = FastAPI()
container = InjectQ.get_instance()
setup_fastapi(container, app)

# Create dependency injection variables at module level


@app.post("/users/{user_id}")
def create_user(
    user_id: str, user_service: Annotated[UserService, InjectAPI(UserService)]
):
    user_service.create_user(user_id, {"name": "John Doe"})
    return {"message": "User created successfully"}


@app.get("/users/{user_id}")
def get_user(user_id: str, user_service: UserService = InjectAPI[UserService]):
    user = user_service.retrieve_user(user_id)
    if user:
        return user
    raise HTTPException(status_code=404, detail="User not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
