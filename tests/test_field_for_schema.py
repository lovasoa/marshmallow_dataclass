import inspect
import typing
import unittest
from enum import Enum
from typing import Dict, Optional, Union, Any, List, Tuple

from marshmallow import fields, Schema

from marshmallow_dataclass import field_for_schema, dataclass, union_field


class TestFieldForSchema(unittest.TestCase):
    def assertFieldsEqual(self, a: fields.Field, b: fields.Field):
        self.assertEqual(a.__class__, b.__class__, "field class")

        def attrs(x):
            return {
                k: f"{v!r} ({v.__mro__!r})" if inspect.isclass(v) else repr(v)
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
        self.assertFieldsEqual(
            field_for_schema(Any), fields.Raw(required=True, allow_none=True)
        )

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
                keys=fields.Raw(required=True, allow_none=True),
                values=fields.Raw(required=True, allow_none=True),
                required=True,
            ),
        )

    def test_builtin_list(self):
        self.assertFieldsEqual(
            field_for_schema(list, metadata=dict(required=False)),
            fields.List(fields.Raw(required=True, allow_none=True), required=False),
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
        self.assertFieldsEqual(
            field_for_schema(Union[int, str]),
            union_field.Union(
                [
                    (int, fields.Integer(required=True)),
                    (str, fields.String(required=True)),
                ],
                required=True,
            ),
        )

    def test_union_multiple_types_with_none(self):
        self.assertFieldsEqual(
            field_for_schema(Union[int, str, None]),
            union_field.Union(
                [
                    (
                        int,
                        fields.Integer(
                            allow_none=True, required=False, default=None, missing=None
                        ),
                    ),
                    (
                        str,
                        fields.String(
                            allow_none=True, required=False, default=None, missing=None
                        ),
                    ),
                ],
                required=False,
                default=None,
                missing=None,
            ),
        )

    def test_optional_multiple_types(self):
        self.assertFieldsEqual(
            field_for_schema(Optional[Union[int, str]]),
            union_field.Union(
                [
                    (
                        int,
                        fields.Integer(
                            allow_none=True, required=False, default=None, missing=None
                        ),
                    ),
                    (
                        str,
                        fields.String(
                            allow_none=True, required=False, default=None, missing=None
                        ),
                    ),
                ],
                required=False,
                default=None,
                missing=None,
            ),
        )

    def test_newtype(self):
        self.assertFieldsEqual(
            field_for_schema(typing.NewType("UserId", int), default=0),
            fields.Integer(required=False, description="UserId", default=0, missing=0),
        )

    def test_marshmallow_dataclass(self):
        class NewSchema(Schema):
            pass

        @dataclass(base_schema=NewSchema)
        class NewDataclass:
            pass

        self.assertFieldsEqual(
            field_for_schema(NewDataclass, metadata=dict(required=False)),
            fields.Nested(NewDataclass.Schema),
        )

    def test_override_container_type_with_type_mapping(self):
        type_mapping = [
            (List, fields.List, List[int]),
            (Dict, fields.Dict, Dict[str, int]),
            (Tuple, fields.Tuple, Tuple[int, str, bytes]),
        ]
        for base_type, marshmallow_field, schema in type_mapping:

            class MyType(marshmallow_field):
                ...

            self.assertIsInstance(field_for_schema(schema), marshmallow_field)

            class BaseSchema(Schema):
                TYPE_MAPPING = {base_type: MyType}

            self.assertIsInstance(
                field_for_schema(schema, base_schema=BaseSchema), MyType
            )


if __name__ == "__main__":
    unittest.main()
