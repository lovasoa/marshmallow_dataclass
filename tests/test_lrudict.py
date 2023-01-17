from marshmallow_dataclass import _LRUDict


def test_LRUDict_getitem_moves_to_end() -> None:
    d = _LRUDict[str, str]()
    d["a"] = "aval"
    d["b"] = "bval"
    assert list(d.items()) == [("a", "aval"), ("b", "bval")]
    assert d["a"] == "aval"
    assert list(d.items()) == [("b", "bval"), ("a", "aval")]


def test_LRUDict_get_moves_to_end() -> None:
    d = _LRUDict[str, str]()
    d["a"] = "aval"
    d["b"] = "bval"
    assert list(d.items()) == [("a", "aval"), ("b", "bval")]
    assert d.get("a") == "aval"
    assert list(d.items()) == [("b", "bval"), ("a", "aval")]


def test_LRUDict_setitem_moves_to_end() -> None:
    d = _LRUDict[str, str]()
    d["a"] = "aval"
    d["b"] = "bval"
    assert list(d.items()) == [("a", "aval"), ("b", "bval")]
    d["a"] = "newval"
    assert list(d.items()) == [("b", "bval"), ("a", "newval")]


def test_LRUDict_discards_oldest() -> None:
    d = _LRUDict[str, str](maxsize=1)
    d["a"] = "aval"
    d["b"] = "bval"
    assert list(d.items()) == [("b", "bval")]
