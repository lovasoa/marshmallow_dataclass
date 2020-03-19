import dataclasses
import unittest
from uuid import UUID

from marshmallow_dataclass import class_schema
from marshmallow import Schema
from marshmallow.fields import Field, UUID as UUIDField


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

        class BaseSchema(Schema):
            TYPE_MAPPING = {CustomType: CustomField}

        @dataclasses.dataclass
        class WithCustomField:
            custom: CustomType
            uuid: UUID

        schema = class_schema(WithCustomField, base_schema=BaseSchema)()
        self.assertIsInstance(schema.fields["custom"], CustomField)
        self.assertIsInstance(schema.fields["uuid"], UUIDField)


if __name__ == "__main__":
    unittest.main()
