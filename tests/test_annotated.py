import unittest
from typing import Annotated, Optional

import marshmallow
import marshmallow.fields

from marshmallow_dataclass import dataclass


class TestAnnotatedField(unittest.TestCase):
    def test_annotated_field(self):
        @dataclass
        class AnnotatedValue:
            value: Annotated[str, marshmallow.fields.Email]
            default_string: Annotated[
                Optional[str], marshmallow.fields.String(load_default="Default String")
            ] = None

        schema = AnnotatedValue.Schema()

        self.assertEqual(
            schema.load({"value": "test@test.com"}),
            AnnotatedValue(value="test@test.com", default_string="Default String"),
        )
        self.assertEqual(
            schema.load({"value": "test@test.com", "default_string": "override"}),
            AnnotatedValue(value="test@test.com", default_string="override"),
        )

        with self.assertRaises(marshmallow.exceptions.ValidationError):
            schema.load({"value": "notavalidemail"})
