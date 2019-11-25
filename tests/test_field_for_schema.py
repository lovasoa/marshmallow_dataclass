import inspect
import typing
import unittest
from enum import Enum
from typing import Dict, Optional, Union, Any

from marshmallow import fields, Schema

from marshmallow_dataclass import field_for_schema, dataclass


class TestFieldForSchema(unittest.TestCase):
    def assertFieldsEqual(self, a: fields.Field, b: fields.Field):
        self.assertEqual(a.__class__, b.__class__, "field class")

        def attrs(x):
            return {
                k: f'{repr(v)} ({repr(v.__mro__)})' if inspect.isclass(v) else repr(v)
                for k, v in x.__dict__.items()
                if not k.startswith("_")
            }

        self.assertEqual(attrs(a), attrs(b))

    def test_int(self):
        self.assertFieldsEqual(
            field_for_schema(int, default=9, metadata=dict(required=False)),
            fields.Integer(default=9, missing=9, required=False),
        )

    def test_any(self):
        self.assertFieldsEqual(field_for_schema(Any), fields.Raw(required=True))

    def test_dict_from_typing(self):
        self.assertFieldsEqual(
            field_for_schema(Dict[str, float]),
            fields.Dict(
                keys=fields.String(required=True),
                values=fields.Float(required=True),
                required=True,
            ),
        )

    def test_builtin_dict(self):
        self.assertFieldsEqual(
            field_for_schema(dict),
            fields.Dict(
                keys=fields.Raw(required=True),
                values=fields.Raw(required=True),
                required=True,
            ),
        )

    def test_builtin_list(self):
        self.assertFieldsEqual(
            field_for_schema(list, metadata=dict(required=False)),
            fields.List(fields.Raw(required=True), required=False),
        )

    def test_explicit_field(self):
        explicit_field = fields.Url(required=True)
        self.assertFieldsEqual(
            field_for_schema(str, metadata={"marshmallow_field": explicit_field}),
            explicit_field,
        )

    def test_str(self):
        self.assertFieldsEqual(field_for_schema(str), fields.String(required=True))

    def test_optional_str(self):
        self.assertFieldsEqual(
            field_for_schema(Optional[str]),
            fields.String(allow_none=True, required=False, default=None, missing=None),
        )

    def test_enum(self):
        import marshmallow_enum

        class Color(Enum):
            RED: 1
            GREEN: 2
            BLUE: 3

        self.assertFieldsEqual(
            field_for_schema(Color),
            marshmallow_enum.EnumField(enum=Color, required=True),
        )

    def test_union(self):
        import marshmallow_union

        self.assertFieldsEqual(
            field_for_schema(Union[int, str]),
            marshmallow_union.Union(
                fields=[fields.Integer(), fields.String()], required=True
            ),
        )

    def test_newtype(self):
        self.assertFieldsEqual(
            field_for_schema(typing.NewType("UserId", int), default=0),
            fields.Integer(required=False, description="UserId", default=0, missing=0),
        )

    def test_marshmellow_dataclass(self):
        class NewSchema(Schema):
            pass

        @dataclass(base_schema=NewSchema)
        class NewDataclass:
            pass

        self.assertFieldsEqual(
            field_for_schema(NewDataclass, metadata=dict(required=False)),
            fields.Nested(NewDataclass.Schema),
        )


if __name__ == "__main__":
    unittest.main()
