from injectq import InjectQ
from injectq.decorators import inject


c1 = InjectQ()
c2 = InjectQ()

# save few data
c1.bind(str, "Hello, InjectQ!")
c1.bind("name", "InjectQ User")
c1.bind_instance("name", "InjectQ User")

c2.bind(int, 42)
c2.bind("name", "InjectQ User from c2")
c2.bind_instance("name", "InjectQ User from c2")


@inject
def test1(s: str, name: str):
    print(s)
    print(name)


@inject
def test2(i: int, name: str):
    print(i)
    print(name)


# @inject uses the current container. Make one current for a block:
with c1.context():
    test1()  # type: ignore # uses c1

with c2.context():
    test2()  # type: ignore # uses c2
