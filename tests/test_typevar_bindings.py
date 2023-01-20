""" Tests for _TypeVarBindings """
from dataclasses import dataclass
from typing import Generic
from typing import TypeVar

import pytest

from marshmallow_dataclass import _is_generic_alias_of_dataclass
from marshmallow_dataclass import _TypeVarBindings


T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")
W = TypeVar("W")


def test_default_init() -> None:
    bindings = _TypeVarBindings()
    assert len(bindings) == 0
    assert list(bindings) == []


def test_init_raises_on_mismatched_args():
    with pytest.raises(ValueError):
        _TypeVarBindings((T, U), (int, str, bool))


def test_from_generic_alias() -> None:
    @dataclass
    class Gen(Generic[T, U]):
        a: T
        b: U

    generic_alias = Gen[str, int]
    assert _is_generic_alias_of_dataclass(generic_alias)
    bindings = _TypeVarBindings.from_generic_alias(generic_alias)
    assert dict(bindings) == {T: str, U: int}


def test_getitem():
    bindings = _TypeVarBindings((T, U), (int, str))
    assert bindings[U] is str

    with pytest.raises(KeyError):
        bindings[V]
    with pytest.raises(KeyError):
        bindings[str]
    with pytest.raises(KeyError):
        bindings[0]


def test_compose():
    b1 = _TypeVarBindings((T, U), (int, V))
    b2 = _TypeVarBindings((V, W), (U, T))

    assert dict(b1.compose(b2)) == {V: V, W: int}
    assert dict(b2.compose(b1)) == {T: int, U: U}
    assert dict(b1.compose(b1)) == {T: int, U: V}
    assert dict(b2.compose(b2)) == {V: U, W: T}
