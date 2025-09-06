Task: 
1. Don't mention any other libraries, remove it from the documentation.
2. User should not use InjectQ.get_instance() directly, instead of use below code
```python
from injectq import injectq
injectq[Service] = Service()
```
why this, because InjectQ is a singleton by default, so user don't need to create multiple instance of it.
It will return the instance from the current context if exists otherwise it will return the global instance.
All the docs using InjectQ.get_instance() should be updated to use above code, Please update all the docs.

Now few tricks
1. what if that service not exists, then how can you handle that, so we will raise error if service not found or you can accept as null
```python
from typing import Optional
from injectq import injectq
injectq[Optional[Service]] = None  # this will not raise error

def func(service: Optional[Service] = injectq[Optional[Service]]):
 pass

or

@inject
def func(service:Service|None = None)

```
Note: this will handle if service is null itself, so user don't need to check it again, Update that in docs


3. We updated inject and Inject decorator, and allow to pass container or it will be used from context or golabl instance
4. We removed inject_into decorator, so remove it from docs


# Asny support
```
from injectq import injectq
class Generator:
    def __init__(self) -> None:
        self.count = 0

    async def generate(self) -> int:
        return randint(1, 100)

generator = Generator()
injectq.bind_factory("random_int", lambda: generator.generate())

# now how to use
await await injectq.get("random_int")
```

# Integration Steps
3.Document the integration of InjectQ with FastAPI and Taskiq in the documentation files.
Current Documentation is completely wrong. Please update it with below code snippets

FastAPI:
```
from injectq.integrations.fastapi import setup_fastapi, InjectAPI
setup_fastapi(injectq, app)

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    user_service: IUserService = InjectAPI[IUserService]
):
    return user_service.get_user(user_id)
    
```

# Taskiq:
```
from injectq.integrations.taskiq import setup_taskiq, InjectTask
setup_taskiq(injectq, broker)


@broker.task(task_name="save", retry_on_error=True, max_retries=3)
async def save_data(
    data: dict,
    service: RankingService = InjectTask[RankingService],
):
pass
```
