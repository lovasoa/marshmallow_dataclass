import unittest

import marshmallow

import marshmallow_dataclass


class TestFieldForSchema(unittest.TestCase):
    def test_postload_a(self):
        @marshmallow_dataclass.dataclass
        class Person:
            name: str

            @marshmallow.post_load
            def a(self, data, **_kwargs):
                data["name"] = data["name"].capitalize()
                return data

        actual = Person.Schema().load({"name": "matt"})
        expected = Person(name="Matt")
        self.assertEqual(actual, expected)

    def test_postload_z(self):
        @marshmallow_dataclass.dataclass
        class Person:
            name: str

            @marshmallow.post_load
            def z(self, data, **_kwargs):
                data["name"] = data["name"].capitalize()
                return data

        actual = Person.Schema().load({"name": "matt"})
        expected = Person(name="Matt")
        self.assertEqual(actual, expected)
