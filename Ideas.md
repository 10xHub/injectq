Our plan is to generate a new dependency injection framework that is lightweight, easy to use, and integrates seamlessly with existing applications. We aim to provide a solution that simplifies the process of managing dependencies and promotes best practices in software development.

Library name injectq


Some idea from existing library:
1. https://github.com/kodemore/kink -> this library shared a default `Container` implementation that is easy to extend and customize, so I dont need to use same instance for every request, it by default available
. We need to do like this also allow user if they want to create the container by themselves

2. https://github.com/python-injector/injector -> this library provides a more advanced and feature-rich dependency injection system, with support for scopes, providers, and more complex use cases.

Some code way we want to achieve this:
```python
from injectq import InjectQ, singleton, inject, Injectable

class A:
    pass

class B:
    pass

class C:
    pass

class D:
    pass

@singleton
class E:
    pass



ins = InjectQ.get_instance()
ins.bind(A, A)
ins.bind("B", B)
ins.bind("C", None)
ins.bind("D", D())

# binding gone

# Now lets use in function
@inject
def test(name:str, b:B):
    pass

def test2(name:str, b:B=Inject(B)): # both allowed
    pass

test("hello") # b will auto inject

# Now lets use in class
@singleton
class MyClass:
    @inject
    def __init__(self, b:B):
        self.b = b

