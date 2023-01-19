import threading
import time
from itertools import count

import pytest

from marshmallow_dataclass.lazy_class_attribute import lazy_class_attribute


def test_caching() -> None:
    counter = count()

    def fget() -> str:
        return f"value-{next(counter)}"

    class A:
        x = lazy_class_attribute(fget, "x")

    assert A.x == "value-0"
    assert A.x == "value-0"


def test_recursive_evaluation() -> None:
    def fget() -> str:
        return A.x

    class A:
        x: str = lazy_class_attribute(fget, "x")  # type: ignore[assignment]

    with pytest.raises(AttributeError, match="recursive evaluation of A.x"):
        A.x


def test_threading() -> None:
    counter = count()
    lock = threading.Lock()

    def fget() -> str:
        time.sleep(0.05)
        with lock:
            return f"value-{next(counter)}"

    class A:
        x = lazy_class_attribute(fget, "x")

    n_threads = 4
    barrier = threading.Barrier(n_threads)
    values = set()

    def run():
        barrier.wait()
        values.add(A.x)

    threads = [threading.Thread(target=run) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert values == {"value-0"}
