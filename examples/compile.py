from injectq import injectq


class Model:
    def hello(self) -> None:
        print("Hello, World!")


class Model2:
    def hello(self) -> None:
        print("Hello, World from Model2!")


if __name__ == "__main__":
    injectq[Model] = Model()
    injectq.compile()

    model = injectq[Model]
    model.hello()

    # now save into a compiled container
    injectq[Model2] = Model2()
    model2 = injectq[Model2]
    model2.hello()
