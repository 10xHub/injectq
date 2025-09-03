from injectq import injectq, Inject


class A:
    def bark(self):
        print("Woof!")


class B:
    def meow(self):
        print("Meow!")


# save few data
injectq.bind(str, "Hello, InjectQ!")
injectq.bind(str, "Hello, InjectQ!22")
injectq.bind("name", "InjectQ User")
injectq.bind_instance("name", "InjectQ User")

injectq.bind(A, A())
injectq.bind_instance(B, B)


print(injectq.get(str))  # should print "Hello, InjectQ!"
print(injectq.get("name"))  # should print "InjectQ User"

print(injectq.get(A).bark())  # should print "Woof!"
print(injectq.get(B).meow())  # should print "Meow!"


def test(aa: A = Inject[A]):  # type: ignore
    print(aa)
    print(aa.bark())


test()
