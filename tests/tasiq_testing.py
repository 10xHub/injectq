from typing import Annotated

import pytest
from taskiq import InMemoryBroker

from injectq import InjectQ, singleton
from injectq.integrations.taskiq import InjectTaskiq, setup_taskiq


@singleton
class DBRepo:
    def __init__(self) -> None:
        pass

    def get_users(self, number: int) -> list[int]:
        return list(range(number))


broker = InMemoryBroker()
injectq_container = InjectQ.get_instance()
setup_taskiq(broker=broker, container=injectq_container)


@broker.task
async def parse_int(
    val: str,
    repo: Annotated[DBRepo, InjectTaskiq(DBRepo)],
) -> list[int]:
    return repo.get_users(int(val))


@pytest.mark.asyncio
async def test_parse_int():
    await broker.startup()
    result = await parse_int.kiq("123")  # type: ignore  # noqa: PGH003
    actual = await result.wait_result()
    assert actual.return_value == list(range(123))
    await broker.shutdown()
