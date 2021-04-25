from marshmallow_dataclass.union_field import FallbackSerializationStrategy, NamedTypeSerializationStrategy, SERIALIZATION_STRATEGY_KEY
import unittest
from typing import List, Optional, Union, Dict

import marshmallow

from marshmallow_dataclass import dataclass
from dataclasses import field


class TestClassSchema(unittest.TestCase):
    def test_simple_union(self):
        @dataclass
        class IntOrStr:
            value: Union[int, str]

        schema = IntOrStr.Schema()
        data_in = {"value": "hello"}
        loaded = schema.load(data_in)
        self.assertEqual(loaded, IntOrStr(value="hello"))
        self.assertEqual(schema.dump(loaded), data_in)

        data_in = {"value": 42}
        self.assertEqual(schema.dump(schema.load(data_in)), data_in)

    def test_simple_union_named_serialization_strategy(self):
        @dataclass
        class IntOrStr:
            value: Union[int, str] = field(metadata={
                SERIALIZATION_STRATEGY_KEY: NamedTypeSerializationStrategy()
            })

        schema = IntOrStr.Schema()
        data_in = {'value': {'__value__': 'hello', '__type__': 'str'}}
        loaded = schema.load(data_in)
        self.assertEqual(loaded, IntOrStr(value="hello"))
        self.assertEqual(schema.dump(loaded), data_in)

        data_in = {'value': {'__value__': 42, '__type__': 'int'}}
        self.assertEqual(schema.dump(schema.load(data_in)), data_in)

    def test_structured_union_named_serialization_strategy(self):

        @dataclass
        class Class1:
            value: str
            name: str

        @dataclass
        class Class2:
            value: float
            name: str

        @dataclass
        class Class3:
            value: int
            name: str

        @dataclass
        class ListOfClasses:
            list: List[Union[Class1, Class2, Class3]] = field(metadata={
                SERIALIZATION_STRATEGY_KEY: NamedTypeSerializationStrategy()
            })

        ic()
        schema = ListOfClasses.Schema()
        data_in = {"list": [
            {
                "value": "hello",
                "name": "world",
                "__type__": "Class1"
            },
            {
                "value": 42,
                "name": "float!",
                "__type__": "Class2"
            },
            {
                "value": 42,
                "name": "int!",
                "__type__": "Class3"
            }
        ]}
        loaded = schema.load(data_in)
        self.assertEqual(loaded, ListOfClasses(
            list=[Class1("hello", "world"), Class2(42, "float!"), Class3(42, "int!")]))
        self.assertEqual(schema.dump(loaded), data_in)

    def test_structured_union_named_serialization_strategy_different_names(self):

        @dataclass
        class Class1:
            value: str
            name: str

        @dataclass
        class Class2:
            value: float
            name: str

        @dataclass
        class Class3:
            value: int
            name: str

        @dataclass
        class ListOfClasses:
            list: List[Union[Class1, Class2, Class3]] = field(metadata={
                SERIALIZATION_STRATEGY_KEY: NamedTypeSerializationStrategy(
                    type_to_name_map={
                        Class1: "c1",
                        Class2: "c2",
                        Class3: "c3"
                    },
                    type_key="I_am_the_type"
                )
            })

        ic()
        schema = ListOfClasses.Schema()
        data_in = {"list": [
            {
                "value": "hello",
                "name": "world",
                "I_am_the_type": "c1"
            },
            {
                "value": 42,
                "name": "float!",
                "I_am_the_type": "c2"
            },
            {
                "value": 42,
                "name": "int!",
                "I_am_the_type": "c3"
            }
        ]}
        loaded = schema.load(data_in)
        self.assertEqual(loaded, ListOfClasses(
            list=[Class1("hello", "world"), Class2(42, "float!"), Class3(42, "int!")]))
        self.assertEqual(schema.dump(loaded), data_in)

    def test_list_union_builtin(self):
        @dataclass
        class Dclass2:
            value: List[Union[int, str]]

        schema = Dclass2.Schema()
        data_in = {"value": ["hello", 42]}
        self.assertEqual(schema.dump(schema.load(data_in)), data_in)

    def test_list_union_object(self):
        @dataclass
        class Elm1:
            elm1: str

        @dataclass
        class Elm2:
            elm2: str

        @dataclass
        class Dclass:
            value: List[Union[Elm1, Elm2]]

        schema = Dclass.Schema()
        data_in = {"value": [{"elm1": "foo"}, {"elm2": "bar"}]}
        load = schema.load(data_in)
        self.assertEqual(load, Dclass(value=[Elm1(elm1="foo"), Elm2(elm2="bar")]))
        self.assertEqual(schema.dump(load), data_in)

    def test_union_list(self):
        @dataclass
        class Elm1:
            elm1: int

        @dataclass
        class Elm2:
            elm2: int

        @dataclass
        class TestDataClass:
            value: Union[List[Elm1], List[Elm2]]

        schema = TestDataClass.Schema()

        data_in = {"value": [{"elm1": 10}, {"elm1": 11}]}
        load = schema.load(data_in)
        self.assertEqual(load, TestDataClass(value=[Elm1(elm1=10), Elm1(elm1=11)]))
        self.assertEqual(schema.dump(load), data_in)

        data_in = {"value": [{"elm2": 10}, {"elm2": 11}]}
        load = schema.load(data_in)
        self.assertEqual(load, TestDataClass(value=[Elm2(elm2=10), Elm2(elm2=11)]))
        self.assertEqual(schema.dump(load), data_in)

        dictwrong_in = {"value": [{"elm1": 10}, {"elm2": 11}]}
        with self.assertRaises(marshmallow.exceptions.ValidationError):
            schema.load(dictwrong_in)

    def test_many_nested_union(self):
        @dataclass
        class Elm1:
            elm1: str

        @dataclass
        class Dclass:
            value: List[Union[List[Union[int, str, Elm1]], int]]

        schema = Dclass.Schema()
        data_in = {"value": [42, ["hello", 13, {"elm1": "foo"}]]}

        self.assertEqual(schema.dump(schema.load(data_in)), data_in)
        with self.assertRaises(marshmallow.exceptions.ValidationError):
            schema.load({"value": [42, ["hello", 13, {"elm2": "foo"}]]})

    def test_union_dict(self):
        @dataclass
        class Dclass:
            value: List[Union[Dict[int, Union[int, str]], Union[int, str]]]

        schema = Dclass.Schema()
        data_in = {"value": [42, {12: 13, 13: "hello"}, "foo"]}

        self.assertEqual(schema.dump(schema.load(data_in)), data_in)

        with self.assertRaises(marshmallow.exceptions.ValidationError):
            schema.load({"value": [(42,), {12: 13, 13: "hello"}, "foo"]})

    def test_union_list_dict(self):
        @dataclass
        class Elm:
            elm: int

        @dataclass
        class Dclass:
            value: Union[List[int], Dict[str, Elm]]

        schema = Dclass.Schema()

        data_in = {"value": {"a": {"elm": 10}, "b": {"elm": 10}}}
        self.assertEqual(schema.dump(schema.load(data_in)), data_in)

        data_in = {"value": [1, 2, 3, 4]}
        self.assertEqual(schema.dump(schema.load(data_in)), data_in)

    def test_union_noschema(self):
        @dataclass
        class Dclass:
            value: Union[int, str]

        schema = Dclass.Schema()
        data_in = {"value": [1.4, 4.2]}
        with self.assertRaises(marshmallow.exceptions.ValidationError):
            self.assertEqual(schema.dump(schema.load(data_in)), data_in)

    def test_union_optional_object(self):
        @dataclass
        class Elm1:
            elm1: str

        @dataclass
        class Elm2:
            elm2: str

        @dataclass
        class Dclass:
            value: Optional[Union[Elm1, Elm2]]

        schema = Dclass.Schema()

        for data_in in [{"value": {"elm1": "hello"}}, {"value": {"elm2": "hello"}}]:
            self.assertEqual(schema.dump(schema.load(data_in)), data_in)

        for data_in in [{"value": None}, {}]:
            self.assertEqual(schema.dump(schema.load(data_in)), {"value": None})
