import dataclasses
import unittest

from marshmallow_dataclass import class_schema


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


if __name__ == "__main__":
    unittest.main()
