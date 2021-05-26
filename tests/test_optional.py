import unittest
from dataclasses import field
from typing import Optional

import marshmallow

from marshmallow_dataclass import dataclass


class TestOptionalField(unittest.TestCase):
    def test_optional_field(self):
        @dataclass
        class OptionalValue:
            value: Optional[str] = "value"

        schema = OptionalValue.Schema()

        self.assertEqual(schema.load({"value": None}), OptionalValue(value=None))
        self.assertEqual(schema.load({"value": "hello"}), OptionalValue(value="hello"))
        self.assertEqual(schema.load({}), OptionalValue())

    def test_optional_field_not_none(self):
        @dataclass
        class OptionalValueNotNone:
            value: Optional[str] = field(
                default="value", metadata={"allow_none": False}
            )

        schema = OptionalValueNotNone.Schema()

        self.assertEqual(schema.load({}), OptionalValueNotNone())
        self.assertEqual(
            schema.load({"value": "hello"}), OptionalValueNotNone(value="hello")
        )
        with self.assertRaises(marshmallow.exceptions.ValidationError) as exc_cm:
            schema.load({"value": None})
        self.assertEqual(
            exc_cm.exception.messages, {"value": ["Field may not be null."]}
        )

    def test_that_key_is_missing_from_output_when_dumping_a_missing_value(self):
        @dataclass
        class OptionalValue:
            value: Optional[str]

        schema = OptionalValue.Schema()

        self.assertEqual(schema.dump(OptionalValue(value=marshmallow.missing)), {})
