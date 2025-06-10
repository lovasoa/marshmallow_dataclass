import dataclasses
import inspect
import sys
import typing
import unittest
from typing_inspect import is_generic_type

import marshmallow.fields
import pytest
from marshmallow import ValidationError

from marshmallow_dataclass import (
    UnboundTypeVarError,
    add_schema,
    class_schema,
    dataclass,
    is_generic_alias_of_dataclass,
)

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated


def get_orig_class(obj):
    """
    Allows you got get the runtime origin class inside __init__

    Near duplicate of https://github.com/Stewori/pytypes/blob/master/pytypes/type_util.py#L182
    """
    try:
        # See https://github.com/Stewori/pytypes/pull/53:
        # Returns  `obj.__orig_class__` protecting from infinite recursion in `__getattr[ibute]__`
        # wrapped in a `checker_tp`.
        # (See `checker_tp` in `typechecker._typeinspect_func for context)
        # Necessary if:
        # - we're wrapping a method (`obj` is `self`/`cls`) and either
        #     - the object's class defines __getattribute__
        # or
        #     - the object doesn't have an `__orig_class__` attribute
        #       and the object's class defines __getattr__.
        # In such a situation, `parent_class = obj.__orig_class__`
        # would call `__getattr[ibute]__`. But that method is wrapped in a `checker_tp` too,
        # so then we'd go into the wrapped `__getattr[ibute]__` and do
        # `parent_class = obj.__orig_class__`, which would call `__getattr[ibute]__`
        # again, and so on. So to bypass `__getattr[ibute]__` we do this:
        return object.__getattribute__(obj, "__orig_class__")
    except AttributeError:
        cls = object.__getattribute__(obj, "__class__")
        if is_generic_type(cls):
            # Searching from index 1 is sufficient: At 0 is get_orig_class, at 1 is the caller.
            frame = inspect.currentframe().f_back
            try:
                while frame:
                    try:
                        res = frame.f_locals["self"]
                        if res.__origin__ is cls:
                            return res
                    except (KeyError, AttributeError):
                        frame = frame.f_back
            finally:
                del frame

        raise


class TestGenerics(unittest.TestCase):
    def test_generic_dataclass(self):
        T = typing.TypeVar("T")

        @dataclasses.dataclass
        class SimpleGeneric(typing.Generic[T]):
            data: T

        @dataclasses.dataclass
        class NestedFixed:
            data: SimpleGeneric[int]

        @dataclasses.dataclass
        class NestedGeneric(typing.Generic[T]):
            data: SimpleGeneric[T]

        self.assertTrue(is_generic_alias_of_dataclass(SimpleGeneric[int]))
        self.assertFalse(is_generic_alias_of_dataclass(SimpleGeneric))

        schema_s = class_schema(SimpleGeneric[str])()
        self.assertEqual(SimpleGeneric(data="a"), schema_s.load({"data": "a"}))
        self.assertEqual(schema_s.dump(SimpleGeneric(data="a")), {"data": "a"})
        with self.assertRaises(ValidationError):
            schema_s.load({"data": 2})

        schema_nested = class_schema(NestedFixed)()
        self.assertEqual(
            NestedFixed(data=SimpleGeneric(1)),
            schema_nested.load({"data": {"data": 1}}),
        )
        self.assertEqual(
            schema_nested.dump(NestedFixed(data=SimpleGeneric(data=1))),
            {"data": {"data": 1}},
        )
        with self.assertRaises(ValidationError):
            schema_nested.load({"data": {"data": "str"}})

        schema_nested_generic = class_schema(NestedGeneric[int])()
        self.assertEqual(
            NestedGeneric(data=SimpleGeneric(1)),
            schema_nested_generic.load({"data": {"data": 1}}),
        )
        self.assertEqual(
            schema_nested_generic.dump(NestedGeneric(data=SimpleGeneric(data=1))),
            {"data": {"data": 1}},
        )
        with self.assertRaises(ValidationError):
            schema_nested_generic.load({"data": {"data": "str"}})

    def test_generic_dataclass_cached(self):
        T = typing.TypeVar("T")

        @dataclass
        class SimpleGeneric(typing.Generic[T]):
            data1: T

        @dataclass
        class NestedFixed:
            data2: SimpleGeneric[int]

        @dataclass
        class NestedGeneric(typing.Generic[T]):
            data3: SimpleGeneric[T]

        self.assertTrue(is_generic_alias_of_dataclass(SimpleGeneric[int]))
        self.assertFalse(is_generic_alias_of_dataclass(SimpleGeneric))

        schema_s = class_schema(SimpleGeneric[str])()
        self.assertEqual(SimpleGeneric(data1="a"), schema_s.load({"data1": "a"}))
        self.assertEqual(schema_s.dump(SimpleGeneric(data1="a")), {"data1": "a"})
        with self.assertRaises(ValidationError):
            schema_s.load({"data1": 2})

        schema_nested = class_schema(NestedFixed)()
        self.assertEqual(
            NestedFixed(data2=SimpleGeneric(1)),
            schema_nested.load({"data2": {"data1": 1}}),
        )
        self.assertEqual(
            schema_nested.dump(NestedFixed(data2=SimpleGeneric(data1=1))),
            {"data2": {"data1": 1}},
        )
        with self.assertRaises(ValidationError):
            schema_nested.load({"data2": {"data1": "str"}})

        schema_nested = NestedFixed.Schema()
        self.assertEqual(
            NestedFixed(data2=SimpleGeneric(1)),
            schema_nested.load({"data2": {"data1": 1}}),
        )
        self.assertEqual(
            schema_nested.dump(NestedFixed(data2=SimpleGeneric(data1=1))),
            {"data2": {"data1": 1}},
        )
        with self.assertRaises(ValidationError):
            schema_nested.load({"data2": {"data1": "str"}})

        schema_nested_generic = class_schema(NestedGeneric[int])()
        self.assertEqual(
            NestedGeneric(data3=SimpleGeneric(1)),
            schema_nested_generic.load({"data3": {"data1": 1}}),
        )
        self.assertEqual(
            schema_nested_generic.dump(NestedGeneric(data3=SimpleGeneric(data1=1))),
            {"data3": {"data1": 1}},
        )
        with self.assertRaises(ValidationError):
            schema_nested_generic.load({"data3": {"data1": "str"}})

        # Copy test again so that we trigger a cache hit
        schema_nested_generic = class_schema(NestedGeneric[int])()
        self.assertEqual(
            NestedGeneric(data3=SimpleGeneric(1)),
            schema_nested_generic.load({"data3": {"data1": 1}}),
        )
        self.assertEqual(
            schema_nested_generic.dump(NestedGeneric(data3=SimpleGeneric(data1=1))),
            {"data3": {"data1": 1}},
        )
        with self.assertRaises(ValidationError):
            schema_nested_generic.load({"data3": {"data1": "str"}})

        with self.assertRaisesRegex(TypeError, "generic"):
            NestedGeneric.Schema()

    def test_generic_dataclass_repeated_fields(self):
        T = typing.TypeVar("T")

        @dataclasses.dataclass
        class AA:
            a: int

        @dataclasses.dataclass
        class BB(typing.Generic[T]):
            b: T

        @dataclasses.dataclass
        class Nested:
            x: BB[float]
            z: BB[float]
            # if y is the first field in this class, deserialisation will fail.
            # see https://github.com/lovasoa/marshmallow_dataclass/pull/172#issuecomment-1334024027
            y: BB[AA]

        schema_nested = class_schema(Nested)()
        self.assertEqual(
            Nested(x=BB(b=1), z=BB(b=1), y=BB(b=AA(1))),
            schema_nested.load({"x": {"b": 1}, "z": {"b": 1}, "y": {"b": {"a": 1}}}),
        )

    def test_marshmallow_dataclass_decorator_raises_on_generic_alias(self):
        """
        We can't support `GenClass[int].Schema` because the class function was created on `GenClass`
        Therefore the function does not know about the `int` type.
        This is a Python limitation, not a marshmallow_dataclass limitation.
        """
        import marshmallow_dataclass

        T = typing.TypeVar("T")

        class GenClass(typing.Generic[T]):
            pass

        with self.assertRaisesRegex(TypeError, "generic"):
            marshmallow_dataclass.dataclass(GenClass[int])

    def test_add_schema_raises_on_generic_alias(self):
        """
        We can't support `GenClass[int].Schema` because the class function was created on `GenClass`
        Therefore the function does not know about the `int` type.
        This is a Python limitation, not a marshmallow_dataclass limitation.
        """
        T = typing.TypeVar("T")

        class GenClass(typing.Generic[T]):
            pass

        with self.assertRaisesRegex(TypeError, "generic"):
            add_schema(GenClass[int])

    def test_schema_raises_on_generic(self):
        """
        We can't support `GenClass[int].Schema` because the class function was created on `GenClass`
        Therefore the function does not know about the `int` type.
        This is a Python limitation, not a marshmallow_dataclass limitation.
        """
        import marshmallow_dataclass

        T = typing.TypeVar("T")

        @marshmallow_dataclass.dataclass
        class GenClass(typing.Generic[T]):
            pass

        with self.assertRaisesRegex(TypeError, "generic"):
            GenClass.Schema()

        with self.assertRaisesRegex(TypeError, "generic"):
            GenClass[int].Schema()

    def test_deep_generic(self):
        T = typing.TypeVar("T")
        U = typing.TypeVar("U")

        @dataclasses.dataclass
        class TestClass(typing.Generic[T, U]):
            pairs: typing.List[typing.Tuple[T, U]]

        test_schema = class_schema(TestClass[str, int])()

        self.assertEqual(
            test_schema.load({"pairs": [("first", "1")]}), TestClass([("first", 1)])
        )

    @pytest.mark.skipif(
        sys.version_info < (3, 9), reason="requires python 3.9 or higher"
    )
    def test_deep_generic_native(self):
        T = typing.TypeVar("T")
        U = typing.TypeVar("U")

        @dataclasses.dataclass
        class TestClass(typing.Generic[T, U]):
            pairs: list[tuple[T, U]]

        test_schema = class_schema(TestClass[str, int])()

        self.assertEqual(
            test_schema.load({"pairs": [("first", "1")]}), TestClass([("first", 1)])
        )

    def test_deep_generic_with_union(self):
        T = typing.TypeVar("T")
        U = typing.TypeVar("U")

        @dataclasses.dataclass
        class TestClass(typing.Generic[T, U]):
            either: typing.List[typing.Union[T, U]]

        test_schema = class_schema(TestClass[str, int])()

        self.assertEqual(
            test_schema.load({"either": ["first", 1]}), TestClass(["first", 1])
        )

    def test_deep_generic_with_overrides(self):
        T = typing.TypeVar("T")
        U = typing.TypeVar("U")
        V = typing.TypeVar("V")
        W = typing.TypeVar("W")

        @dataclasses.dataclass
        class TestClass(typing.Generic[T, U, V]):
            pairs: typing.List[typing.Tuple[T, U]]
            gen: V
            override: int

        # Don't only override typevar, but switch order to further confuse things
        # Ignoring 'override' Because I want to test that it works, even if incompatible types
        @dataclasses.dataclass
        class TestClass2(TestClass[str, W, U]):  # type: ignore[override]
            override: str  # type: ignore[override, assignment]

        TestAlias = TestClass2[int, T]  # type: ignore[override]

        # inherit from alias
        @dataclasses.dataclass
        class TestClass3(TestAlias[typing.List[int]]):  # type: ignore[override]
            pass

        test_schema = class_schema(TestClass3)()

        self.assertEqual(
            test_schema.load(
                {"pairs": [("first", "1")], "gen": ["1", 2], "override": "overridden"}
            ),
            TestClass3([("first", 1)], [1, 2], "overridden"),
        )

    def test_generic_bases(self) -> None:
        T = typing.TypeVar("T")

        @dataclasses.dataclass
        class Base1(typing.Generic[T]):
            answer: T

        @dataclasses.dataclass
        class TestClass(Base1[T]):
            pass

        test_schema = class_schema(TestClass[int])()

        self.assertEqual(test_schema.load({"answer": "1"}), TestClass(1))

    def test_bound_generic_base(self) -> None:
        T = typing.TypeVar("T")

        @dataclasses.dataclass
        class Base1(typing.Generic[T]):
            answer: T

        @dataclasses.dataclass
        class TestClass(Base1[int]):
            pass

        with self.assertRaisesRegex(
            UnboundTypeVarError, "Base1 has unbound fields: answer"
        ):
            class_schema(Base1)

        test_schema = class_schema(TestClass)()
        self.assertEqual(test_schema.load({"answer": "1"}), TestClass(1))

    def test_unbound_type_var(self) -> None:
        T = typing.TypeVar("T")

        @dataclasses.dataclass
        class Base:
            answer: T  # type: ignore[valid-type]

        with self.assertRaises(UnboundTypeVarError):
            class_schema(Base)

        with self.assertRaises(TypeError):
            class_schema(Base)

    def test_marshmallow_dataclass_unbound_type_var(self) -> None:
        T = typing.TypeVar("T")

        @dataclass
        class Base:
            answer: T  # type: ignore[valid-type]

        with self.assertRaises(UnboundTypeVarError):
            class_schema(Base)

        with self.assertRaises(TypeError):
            class_schema(Base)

    def test_annotated_generic_mf_field(self) -> None:
        T = typing.TypeVar("T")

        class GenericList(marshmallow.fields.List, typing.Generic[T]):
            """
            Generic Marshmallow List Field that can be used in Annotated and still get all kwargs
            from marshmallow_dataclass.
            """

            def __init__(
                self,
                **kwargs,
            ):
                cls_or_instance = get_orig_class(self).__args__[0]

                super().__init__(cls_or_instance, **kwargs)

        @dataclass
        class AnnotatedValue:
            emails: Annotated[
                typing.List[str], GenericList[marshmallow.fields.Email]
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

    def test_generic_dataclass_with_forwardref(self):
        T = typing.TypeVar("T")

        @dataclasses.dataclass
        class ForwardGeneric(typing.Generic[T]):
            data: T

        schema_s = class_schema(ForwardGeneric["str"])()
        self.assertEqual(ForwardGeneric(data="a"), schema_s.load({"data": "a"}))
        self.assertEqual(schema_s.dump(ForwardGeneric(data="a")), {"data": "a"})
        with self.assertRaises(ValidationError):
            schema_s.load({"data": 2})

    def test_generic_dataclass_with_optional(self):
        T = typing.TypeVar("T")

        @dataclasses.dataclass
        class OptionalGeneric(typing.Generic[T]):
            data: typing.Optional[T]

        schema_s = class_schema(OptionalGeneric["str"])()
        self.assertEqual(OptionalGeneric(data="a"), schema_s.load({"data": "a"}))
        self.assertEqual(schema_s.dump(OptionalGeneric(data="a")), {"data": "a"})

        self.assertEqual(OptionalGeneric(data=None), schema_s.load({}))
        self.assertEqual(schema_s.dump(OptionalGeneric(data=None)), {"data": None})

        with self.assertRaises(ValidationError):
            schema_s.load({"data": 2})

    @pytest.mark.skipif(
        sys.version_info < (3, 13), reason="requires python 3.13 or higher"
    )
    def test_generic_default(self):
        T = typing.TypeVar("T", default=str)

        @dataclasses.dataclass
        class SimpleGeneric(typing.Generic[T]):
            data: T

        @dataclasses.dataclass
        class NestedFixed:
            data: SimpleGeneric[int]

        @dataclasses.dataclass
        class NestedGeneric(typing.Generic[T]):
            data: SimpleGeneric[T]

        self.assertTrue(is_generic_alias_of_dataclass(SimpleGeneric[int]))
        self.assertFalse(is_generic_alias_of_dataclass(SimpleGeneric))

        schema_s = class_schema(SimpleGeneric)()
        self.assertEqual(SimpleGeneric(data="a"), schema_s.load({"data": "a"}))
        self.assertEqual(schema_s.dump(SimpleGeneric(data="a")), {"data": "a"})
        with self.assertRaises(ValidationError):
            schema_s.load({"data": 2})

        schema_nested = class_schema(NestedFixed)()
        self.assertEqual(
            NestedFixed(data=SimpleGeneric(1)),
            schema_nested.load({"data": {"data": 1}}),
        )
        self.assertEqual(
            schema_nested.dump(NestedFixed(data=SimpleGeneric(data=1))),
            {"data": {"data": 1}},
        )
        with self.assertRaises(ValidationError):
            schema_nested.load({"data": {"data": "str"}})

        schema_nested_generic = class_schema(NestedGeneric[int])()
        self.assertEqual(
            NestedGeneric(data=SimpleGeneric(1)),
            schema_nested_generic.load({"data": {"data": 1}}),
        )
        self.assertEqual(
            schema_nested_generic.dump(NestedGeneric(data=SimpleGeneric(data=1))),
            {"data": {"data": 1}},
        )
        with self.assertRaises(ValidationError):
            schema_nested_generic.load({"data": {"data": "str"}})

    @pytest.mark.skipif(
        sys.version_info < (3, 13), reason="requires python 3.13 or higher"
    )
    def test_deep_generic_with_default_overrides(self):
        T = typing.TypeVar("T", default=bool)
        U = typing.TypeVar("U", default=int)
        V = typing.TypeVar("V", default=str)
        W = typing.TypeVar("W", default=float)

        @dataclasses.dataclass
        class TestClass(typing.Generic[T, U, V]):
            pairs: typing.List[typing.Tuple[T, U]]
            gen: V
            override: int

        test_schema = class_schema(TestClass)()
        assert list(test_schema.fields) == ["pairs", "gen", "override"]
        assert isinstance(test_schema.fields["pairs"], marshmallow.fields.List)
        assert isinstance(test_schema.fields["pairs"].inner, marshmallow.fields.Tuple)
        assert isinstance(
            test_schema.fields["pairs"].inner.tuple_fields[0],
            marshmallow.fields.Boolean,
        )
        assert isinstance(
            test_schema.fields["pairs"].inner.tuple_fields[1],
            marshmallow.fields.Integer,
        )

        assert isinstance(test_schema.fields["gen"], marshmallow.fields.String)
        assert isinstance(test_schema.fields["override"], marshmallow.fields.Integer)

        # Don't only override typevar, but switch order to further confuse things
        @dataclasses.dataclass
        class TestClass2(TestClass[str, W, U]):  # type: ignore[override]
            # Want to test that it works, even if incompatible types
            override: str  # type: ignore[override, assignment]

        TestAlias = TestClass2[int, T]  # type: ignore[override]
        test_schema2 = class_schema(TestClass2)()
        assert list(test_schema2.fields) == ["pairs", "gen", "override"]
        assert isinstance(test_schema2.fields["pairs"], marshmallow.fields.List)
        assert isinstance(test_schema2.fields["pairs"].inner, marshmallow.fields.Tuple)
        assert isinstance(
            test_schema2.fields["pairs"].inner.tuple_fields[0],
            marshmallow.fields.String,
        )
        assert isinstance(
            test_schema2.fields["pairs"].inner.tuple_fields[1],
            marshmallow.fields.Float,
        )

        assert isinstance(test_schema2.fields["gen"], marshmallow.fields.Integer)
        assert isinstance(test_schema2.fields["override"], marshmallow.fields.String)

        # inherit from alias
        @dataclasses.dataclass
        class TestClass3(TestAlias[typing.List[int]]):  # type: ignore[override]
            pass

        test_schema3 = class_schema(TestClass3)()
        assert list(test_schema3.fields) == ["pairs", "gen", "override"]
        assert isinstance(test_schema3.fields["pairs"], marshmallow.fields.List)
        assert isinstance(test_schema3.fields["pairs"].inner, marshmallow.fields.Tuple)
        assert isinstance(
            test_schema3.fields["pairs"].inner.tuple_fields[0],
            marshmallow.fields.String,
        )
        assert isinstance(
            test_schema3.fields["pairs"].inner.tuple_fields[1],
            marshmallow.fields.Integer,
        )

        assert isinstance(test_schema3.fields["gen"], marshmallow.fields.List)
        assert isinstance(test_schema3.fields["gen"].inner, marshmallow.fields.Integer)
        assert isinstance(test_schema3.fields["override"], marshmallow.fields.String)

        self.assertEqual(
            test_schema3.load(
                {"pairs": [("first", "1")], "gen": ["1", 2], "override": "overridden"}
            ),
            TestClass3([("first", 1)], [1, 2], "overridden"),
        )

    @pytest.mark.skipif(
        sys.version_info < (3, 13), reason="requires python 3.13 or higher"
    )
    def test_generic_default_recursion(self):
        T = typing.TypeVar("T", default=str)
        U = typing.TypeVar("U", default=T)
        V = typing.TypeVar("V", default=U)

        @dataclasses.dataclass
        class DefaultGenerics(typing.Generic[T, U, V]):
            a: T
            b: U
            c: V

        test_schema = class_schema(DefaultGenerics)()
        assert list(test_schema.fields) == ["a", "b", "c"]
        assert isinstance(test_schema.fields["a"], marshmallow.fields.String)
        assert isinstance(test_schema.fields["b"], marshmallow.fields.String)
        assert isinstance(test_schema.fields["c"], marshmallow.fields.String)

        test_schema2 = class_schema(DefaultGenerics[int])()
        assert list(test_schema2.fields) == ["a", "b", "c"]
        assert isinstance(test_schema2.fields["a"], marshmallow.fields.Integer)
        assert isinstance(test_schema2.fields["b"], marshmallow.fields.Integer)
        assert isinstance(test_schema2.fields["c"], marshmallow.fields.Integer)


if __name__ == "__main__":
    unittest.main()
