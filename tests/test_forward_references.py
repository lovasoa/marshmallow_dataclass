import unittest
from typing import List

from marshmallow_dataclass import dataclass


@dataclass
class GlobalA:
    b: "GlobalB"


@dataclass
class GlobalB:
    pass


@dataclass
class GlobalRecursion:
    # todo: "self" is temporal
    related: 'List["self"]'  # type: ignore


class TestForwardReferences(unittest.TestCase):
    def test_late_evaluated_types(self):
        @dataclass
        class MyData:
            value: "int"

        self.assertEqual(MyData(1), MyData.Schema().load(dict(value=1)))

    def test_global_forward_references(self):
        self.assertEqual(GlobalA(GlobalB()), GlobalA.Schema().load(dict(b=dict())))

    def test_global_recursive_type(self):
        self.assertEqual(
            GlobalRecursion([GlobalRecursion([])]),
            GlobalRecursion.Schema().load(dict(related=[dict(related=[])])),
        )

    def test_local_recursive_type(self):
        # todo: locals() should be passed to the get_type_hints in some way to avoid "self"
        @dataclass
        class LocalRecursion:
            related: 'List["self"]'

        self.assertEqual(
            LocalRecursion([LocalRecursion([])]),
            LocalRecursion.Schema().load(dict(related=[dict(related=[])])),
        )

    @unittest.skip("unsupported for now")
    def test_local_forward_references(self):
        # todo: locals() should be passed to the get_type_hints in some way

        @dataclass
        class LocalA:
            b: "LocalB"

        @dataclass
        class LocalB:
            pass

        self.assertEqual(LocalA(LocalB()), LocalA.Schema().load(dict(b=dict())))
