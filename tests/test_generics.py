import dataclasses
import typing
import unittest

from marshmallow import ValidationError

from marshmallow_dataclass import _is_generic_alias_of_dataclass, class_schema


class TestGenerics(unittest.TestCase):
    def test_generic_dataclass(self):
        T = typing.TypeVar("T")

        @dataclasses.dataclass
        class SimpleGeneric(typing.Generic[T]):
            data: T

        @dataclasses.dataclass
        class NestedFixed:
            data: SimpleGeneric[int]

        @dataclasses.dataclass
        class NestedGeneric(typing.Generic[T]):
            data: SimpleGeneric[T]

        self.assertTrue(_is_generic_alias_of_dataclass(SimpleGeneric[int]))
        self.assertFalse(_is_generic_alias_of_dataclass(SimpleGeneric))

        schema_s = class_schema(SimpleGeneric[str])()
        self.assertEqual(SimpleGeneric(data="a"), schema_s.load({"data": "a"}))
        self.assertEqual(schema_s.dump(SimpleGeneric(data="a")), {"data": "a"})
        with self.assertRaises(ValidationError):
            schema_s.load({"data": 2})

        schema_nested = class_schema(NestedFixed)()
        self.assertEqual(
            NestedFixed(data=SimpleGeneric(1)),
            schema_nested.load({"data": {"data": 1}}),
        )
        self.assertEqual(
            schema_nested.dump(NestedFixed(data=SimpleGeneric(data=1))),
            {"data": {"data": 1}},
        )
        with self.assertRaises(ValidationError):
            schema_nested.load({"data": {"data": "str"}})

        schema_nested_generic = class_schema(NestedGeneric[int])()
        self.assertEqual(
            NestedGeneric(data=SimpleGeneric(1)),
            schema_nested_generic.load({"data": {"data": 1}}),
        )
        self.assertEqual(
            schema_nested_generic.dump(NestedGeneric(data=SimpleGeneric(data=1))),
            {"data": {"data": 1}},
        )
        with self.assertRaises(ValidationError):
            schema_nested_generic.load({"data": {"data": "str"}})

    def test_generic_dataclass_repeated_fields(self):
        T = typing.TypeVar("T")

        @dataclasses.dataclass
        class AA:
            a: int

        @dataclasses.dataclass
        class BB(typing.Generic[T]):
            b: T

        @dataclasses.dataclass
        class Nested:
            x: BB[float]
            z: BB[float]
            # if y is the first field in this class, deserialisation will fail.
            # see https://github.com/lovasoa/marshmallow_dataclass/pull/172#issuecomment-1334024027
            y: BB[AA]

        schema_nested = class_schema(Nested)()
        self.assertEqual(
            Nested(x=BB(b=1), z=BB(b=1), y=BB(b=AA(1))),
            schema_nested.load({"x": {"b": 1}, "z": {"b": 1}, "y": {"b": {"a": 1}}}),
        )


if __name__ == "__main__":
    unittest.main()
