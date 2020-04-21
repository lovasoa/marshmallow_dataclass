import unittest

import marshmallow

import marshmallow_dataclass


class MyBaseSchema(marshmallow.Schema):
    pass


class A:
    a: int


# Top-level so that this is checked by mypy
schema_with_base: MyBaseSchema = marshmallow_dataclass.class_schema(
    A, base_schema=MyBaseSchema
)()

schema_without_base: marshmallow.Schema = marshmallow_dataclass.class_schema(A)()


# Regression test for https://github.com/lovasoa/marshmallow_dataclass/pull/77
class TestSchemaType(unittest.TestCase):
    def test_custom_basechema_type(self):
        self.assertIsInstance(schema_with_base, MyBaseSchema)

    def test_no_basechema_type(self):
        self.assertIsInstance(schema_without_base, marshmallow.Schema)
