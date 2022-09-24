import dataclasses
import unittest

from marshmallow_dataclass import class_schema


class Test_Schema_load_to_dict(unittest.TestCase):
    def test_simple(self):
        @dataclasses.dataclass
        class Simple:
            one: int = dataclasses.field()
            two: str = dataclasses.field()

        simple_schema = class_schema(Simple)()
        assert simple_schema.load_to_dict({"one": "1", "two": "b"}) == {
            "one": 1,
            "two": "b",
        }

    def test_partial(self):
        @dataclasses.dataclass
        class Simple:
            one: int = dataclasses.field()
            two: str = dataclasses.field()

        simple_schema = class_schema(Simple)()
        assert simple_schema.load_to_dict({"one": "1"}, partial=True) == {"one": 1}

    def test_nested(self):
        @dataclasses.dataclass
        class Simple:
            one: int = dataclasses.field()
            two: str = dataclasses.field()

        @dataclasses.dataclass
        class Nested:
            x: str = dataclasses.field()
            child: Simple = dataclasses.field()

        nested_schema = class_schema(Nested)()
        assert nested_schema.load_to_dict({"child": {"one": "1"}}, partial=True) == {
            "child": {"one": 1},
        }


if __name__ == "__main__":
    unittest.main()
