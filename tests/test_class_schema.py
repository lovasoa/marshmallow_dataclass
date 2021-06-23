import typing
import unittest
from typing import Any, TYPE_CHECKING
from uuid import UUID

try:
    from typing import Final, Literal  # type: ignore[attr-defined]
except ImportError:
    from typing_extensions import Final, Literal  # type: ignore[misc]

import dataclasses
from marshmallow import Schema, ValidationError
from marshmallow.fields import Field, UUID as UUIDField, List as ListField, Integer
from marshmallow.validate import Validator

from marshmallow_dataclass import class_schema, NewType


class TestClassSchema(unittest.TestCase):
    def test_simple_unique_schemas(self):
        @dataclasses.dataclass
        class Simple:
            one: str = dataclasses.field()
            two: str = dataclasses.field()

        @dataclasses.dataclass
        class ComplexNested:
            three: int = dataclasses.field()
            four: Simple = dataclasses.field()

        self.assertIs(class_schema(ComplexNested), class_schema(ComplexNested))
        self.assertIs(class_schema(Simple), class_schema(Simple))
        self.assertIs(
            class_schema(Simple),
            class_schema(ComplexNested)._declared_fields["four"].nested,
        )

        complex_set = {
            class_schema(ComplexNested),
            class_schema(ComplexNested, base_schema=None),
            class_schema(ComplexNested, None),
        }
        simple_set = {
            class_schema(Simple),
            class_schema(Simple, base_schema=None),
            class_schema(Simple, None),
        }
        self.assertEqual(len(complex_set), 1)
        self.assertEqual(len(simple_set), 1)

    def test_use_type_mapping_from_base_schema(self):
        class CustomType:
            pass

        class CustomField(Field):
            pass

        class CustomListField(ListField):
            pass

        class BaseSchema(Schema):
            TYPE_MAPPING = {CustomType: CustomField, typing.List: CustomListField}

        @dataclasses.dataclass
        class WithCustomField:
            custom: CustomType
            custom_list: typing.List[float]
            uuid: UUID
            n: int

        schema = class_schema(WithCustomField, base_schema=BaseSchema)()
        self.assertIsInstance(schema.fields["custom"], CustomField)
        self.assertIsInstance(schema.fields["custom_list"], CustomListField)
        self.assertIsInstance(schema.fields["uuid"], UUIDField)
        self.assertIsInstance(schema.fields["n"], Integer)

    def test_filtering_list_schema(self):
        class FilteringListField(ListField):
            def __init__(
                self,
                cls_or_instance: typing.Union[Field, type],
                min: typing.Any,
                max: typing.Any,
                **kwargs,
            ):
                super().__init__(cls_or_instance, **kwargs)
                self.min = min
                self.max = max

            def _deserialize(
                self, value, attr, data, **kwargs
            ) -> typing.List[typing.Any]:
                loaded = super()._deserialize(value, attr, data, **kwargs)
                return [x for x in loaded if self.min <= x <= self.max]

        class BaseSchema(Schema):
            TYPE_MAPPING = {typing.List: FilteringListField}

        @dataclasses.dataclass
        class WithCustomField:
            constrained_floats: typing.List[float] = dataclasses.field(
                metadata={"max": 2.5, "min": 1}
            )
            constrained_strings: typing.List[str] = dataclasses.field(
                metadata={"max": "x", "min": "a"}
            )

        schema = class_schema(WithCustomField, base_schema=BaseSchema)()
        actual = schema.load(
            {
                "constrained_floats": [0, 1, 2, 3],
                "constrained_strings": ["z", "a", "b", "c", ""],
            }
        )
        self.assertEqual(
            actual,
            WithCustomField(
                constrained_floats=[1.0, 2.0], constrained_strings=["a", "b", "c"]
            ),
        )

    def test_any_none(self):
        # See: https://github.com/lovasoa/marshmallow_dataclass/issues/80
        @dataclasses.dataclass
        class A:
            data: Any

        schema = class_schema(A)()
        self.assertEqual(A(data=None), schema.load({"data": None}))
        self.assertEqual(schema.dump(A(data=None)), {"data": None})

    def test_any_none_disallowed(self):
        @dataclasses.dataclass
        class A:
            data: Any = dataclasses.field(metadata={"allow_none": False})

        schema = class_schema(A)()
        self.assertRaises(ValidationError, lambda: schema.load({"data": None}))

    def test_literal(self):
        @dataclasses.dataclass
        class A:
            data: Literal["a"]

        schema = class_schema(A)()
        self.assertEqual(A(data="a"), schema.load({"data": "a"}))
        self.assertEqual(schema.dump(A(data="a")), {"data": "a"})
        for data in ["b", 2, 2.34, False]:
            with self.assertRaises(ValidationError):
                schema.load({"data": data})

    def test_literal_multiple_types(self):
        @dataclasses.dataclass
        class A:
            data: Literal["a", 1, 1.23, True]

        schema = class_schema(A)()
        for data in ["a", 1, 1.23, True]:
            self.assertEqual(A(data=data), schema.load({"data": data}))
            self.assertEqual(schema.dump(A(data=data)), {"data": data})
        for data in ["b", 2, 2.34, False]:
            with self.assertRaises(ValidationError):
                schema.load({"data": data})

    def test_final(self):
        @dataclasses.dataclass
        class A:
            # Mypy currently considers read-only dataclass attributes without a
            # default value an error.
            # See: https://github.com/python/mypy/issues/10688.
            data: Final[str]  # type: ignore[misc]

        schema = class_schema(A)()
        self.assertEqual(A(data="a"), schema.load({"data": "a"}))
        self.assertEqual(schema.dump(A(data="a")), {"data": "a"})
        for data in [2, 2.34, False]:
            with self.assertRaises(ValidationError):
                schema.load({"data": data})

    def test_final_infers_type_from_default_not_implemented(self):
        # @dataclasses.dataclass
        class A:
            data: Final = "a"

        # NOTE: This workaround is needed to avoid a Mypy crash.
        # See: https://github.com/python/mypy/issues/10090#issuecomment-866686096
        if not TYPE_CHECKING:
            A = dataclasses.dataclass(A)

        with self.assertRaises(NotImplementedError):
            class_schema(A)

    def test_validator_stacking(self):
        # See: https://github.com/lovasoa/marshmallow_dataclass/issues/91
        class SimpleValidator(Validator):
            # Marshmallow checks for valid validators at construction time only using `callable`
            def __call__(self):
                pass

        validator_a = SimpleValidator()
        validator_b = SimpleValidator()
        validator_c = SimpleValidator()
        validator_d = SimpleValidator()

        CustomTypeOneValidator = NewType(
            "CustomTypeOneValidator", str, validate=validator_a
        )
        CustomTypeNoneValidator = NewType("CustomTypeNoneValidator", str, validate=None)
        CustomTypeMultiValidator = NewType(
            "CustomTypeNoneValidator", str, validate=[validator_a, validator_b]
        )

        @dataclasses.dataclass
        class A:
            data: CustomTypeNoneValidator = dataclasses.field()

        schema_a = class_schema(A)()
        self.assertListEqual(schema_a.fields["data"].validators, [])

        @dataclasses.dataclass
        class B:
            data: CustomTypeNoneValidator = dataclasses.field(
                metadata={"validate": validator_a}
            )

        schema_b = class_schema(B)()
        self.assertListEqual(schema_b.fields["data"].validators, [validator_a])

        @dataclasses.dataclass
        class C:
            data: CustomTypeNoneValidator = dataclasses.field(
                metadata={"validate": [validator_a, validator_b]}
            )

        schema_c = class_schema(C)()
        self.assertListEqual(
            schema_c.fields["data"].validators, [validator_a, validator_b]
        )

        @dataclasses.dataclass
        class D:
            data: CustomTypeOneValidator = dataclasses.field()

        schema_d = class_schema(D)()
        self.assertListEqual(schema_d.fields["data"].validators, [validator_a])

        @dataclasses.dataclass
        class E:
            data: CustomTypeOneValidator = dataclasses.field(
                metadata={"validate": validator_b}
            )

        schema_e = class_schema(E)()
        self.assertListEqual(
            schema_e.fields["data"].validators, [validator_a, validator_b]
        )

        @dataclasses.dataclass
        class F:
            data: CustomTypeOneValidator = dataclasses.field(
                metadata={"validate": [validator_b, validator_c]}
            )

        schema_f = class_schema(F)()
        self.assertListEqual(
            schema_f.fields["data"].validators, [validator_a, validator_b, validator_c]
        )

        @dataclasses.dataclass
        class G:
            data: CustomTypeMultiValidator = dataclasses.field()

        schema_g = class_schema(G)()
        self.assertListEqual(
            schema_g.fields["data"].validators, [validator_a, validator_b]
        )

        @dataclasses.dataclass
        class H:
            data: CustomTypeMultiValidator = dataclasses.field(
                metadata={"validate": validator_c}
            )

        schema_h = class_schema(H)()
        self.assertListEqual(
            schema_h.fields["data"].validators, [validator_a, validator_b, validator_c]
        )

        @dataclasses.dataclass
        class J:
            data: CustomTypeMultiValidator = dataclasses.field(
                metadata={"validate": [validator_c, validator_d]}
            )

        schema_j = class_schema(J)()
        self.assertListEqual(
            schema_j.fields["data"].validators,
            [validator_a, validator_b, validator_c, validator_d],
        )


if __name__ == "__main__":
    unittest.main()
