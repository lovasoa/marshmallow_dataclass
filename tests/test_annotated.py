import dataclasses
import functools
import sys
import unittest
from typing import List, Optional

import marshmallow
import marshmallow.fields

from marshmallow_dataclass import dataclass

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated


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

    def test_annotated_partial_field(self) -> None:
        """
        NewType allowed us to specify a lambda or partial because there was no type inspection.
        But with Annotated we do type inspection. Partial still allows us to to type inspection.
        """

        @dataclass
        class AnnotatedValue:
            emails: Annotated[
                List[str],
                functools.partial(marshmallow.fields.List, marshmallow.fields.Email),
            ] = dataclasses.field(default_factory=lambda: ["default@email.com"])

        schema = AnnotatedValue.Schema()  # type: ignore[attr-defined]

        self.assertEqual(
            schema.load({}),
            AnnotatedValue(emails=["default@email.com"]),
        )
        self.assertEqual(
            schema.load({"emails": ["test@test.com"]}),
            AnnotatedValue(
                emails=["test@test.com"],
            ),
        )

        with self.assertRaises(marshmallow.exceptions.ValidationError):
            schema.load({"emails": "notavalidemail"})

    def test_annotated_callable_field(self) -> None:
        """
        NewType allowed us to specify a lambda or partial because there was no type inspection.
        But with Annotated we do type inspection. While we can't reliably do type inspection on a callable,
        i.e.: lambda, we can call it and check if it returns a Field.
        """

        @dataclass
        class AnnotatedValue:
            emails: Annotated[
                List[str],
                lambda *args, **kwargs: marshmallow.fields.List(
                    marshmallow.fields.Email, *args, **kwargs
                ),
            ] = dataclasses.field(default_factory=lambda: ["default@email.com"])

        schema = AnnotatedValue.Schema()  # type: ignore[attr-defined]

        self.assertEqual(
            schema.load({}),
            AnnotatedValue(emails=["default@email.com"]),
        )
        self.assertEqual(
            schema.load({"emails": ["test@test.com"]}),
            AnnotatedValue(
                emails=["test@test.com"],
            ),
        )

        with self.assertRaises(marshmallow.exceptions.ValidationError):
            schema.load({"emails": "notavalidemail"})
