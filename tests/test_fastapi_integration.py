# from typing import Annotated

# from fastapi import FastAPI
# from fastapi.testclient import TestClient

# from injectq import InjectQ, singleton
# from injectq.integrations.fastapi import InjectAPI, setup_fastapi


# @singleton
# class UserService:
#     def get_users(self):
#         return {"users": ["alice", "bob"]}


# def create_app():
#     container = InjectQ()
#     container.bind(UserService, UserService())
#     app = FastAPI()

#     @app.get("/users")
#     async def get_users(service: Annotated[UserService, InjectAPI(UserService)]):
#         print("Getting called")
#         return service.get_users()

#     setup_fastapi(container, app)
#     return app


# def test_fastapi_integration():
#     app = create_app()
#     client = TestClient(app)
#     response = client.get("/users")
#     print(response.json())
#     assert response.status_code == 200
#     assert response.json() == {"users": ["alice", "bob"]}
