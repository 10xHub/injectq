from injectq import injectq


class A:
    pass


if __name__ == "__main__":
    ins = A

    if isinstance(ins, type):
        print("ins is a type")

    if isinstance(ins, A):
        print("ins is an instance of A")
    else:
        print("ins is NOT an instance of A")

    injectq.bind_instance(A, A)
    a1 = injectq.get(A)
    print(a1)
