# marshmallow_dataclass change log

## v8.0.0
 - Added support for validator stacking. This breaks backwards compatability. See https://github.com/lovasoa/marshmallow_dataclass/issues/91.
    ### What this means:
    ```python
<<<<<<< HEAD
    CustomType = NewType("CustomType", str, validate=marshmallow.validate.Length(min=3))
=======
        CustomType = NewType("CustomType", str, validate=marshmallow.validate.Length(min=3))
>>>>>>> 55797124700e269c817c9ee56785c0b4d76b5a1d


    @dataclass
    class CustomObject:
        some_field: CustomType = field(metadata={"validate": marshmallow.validate.URL()})
    ```
    The following code will produce a field with the following list of validators: `[marshmallow.validate.bla(), marshmallow.validate.URL()]` instead of the previous: `[marshmallow.validate.URL()]`.

## v7.6.0
 - Allow setting a custom marshmallow field for collection types. This lets you write code such as :
    ```python
    class FilteringListField(ListField):
        def __init__(self, cls: Union[Field, type], min: typing.Any, **kwargs):
            super().__init__(cls, **kwargs)
            self.min = min

        def _deserialize(self, value, attr, data, **kwargs) -> typing.List[typing.Any]:
            loaded = super(FilteringListField, self)._deserialize(
                value, attr, data, **kwargs
            )
            return [x for x in loaded if self.min <= x]


    class BaseSchema(Schema):
        TYPE_MAPPING = {typing.List: FilteringListField}


    @dataclasses.dataclass
    class WithCustomField:
        constrained_floats: typing.List[float] = dataclasses.field(metadata={"min": 1})


    schema = class_schema(WithCustomField, base_schema=BaseSchema)()
    schema.load({"constrained_floats": [0, 1, 2, 3]})
    # -> WithCustomField(constrained_floats=[1.0, 2.0, 3.0])
    ```
    (See [#66](https://github.com/lovasoa/marshmallow_dataclass/issues/66))

## v7.5.2
 - Fix fields of type `Any` incorrectly always rejecting the value `None`.
   `None` can still be disallowed by explicitly setting the marshmallow attribute `allow_none=False`.
   ([#80](https://github.com/lovasoa/marshmallow_dataclass/issues/80))

## v7.5.1
 - Fix an inconsistency in the behavior of `marshmallow.post_load`.
   The input to [`post_load`](https://marshmallow.readthedocs.io/en/stable/extending.html)
   hooks was either a dict or a dataclass instance depending on the method name.
   It is now always a dict.
   ([#75](https://github.com/lovasoa/marshmallow_dataclass/issues/75))

## v7.5.0
 - Allow the use of BaseSchema to specify a custom mapping from python types to marshmallow fields
   ([#72](https://github.com/lovasoa/marshmallow_dataclass/pull/72))

## v7.4.0
 - Cache the generated schemas
   ([#70](https://github.com/lovasoa/marshmallow_dataclass/pull/70))

## v7.2.1
 - Exclude the `test` subdirectory from the published package.
   ([#59](https://github.com/lovasoa/marshmallow_dataclass/pull/59))

## v7.2.0
 - Add mypy plugin that handles `NewType`
   ([#50](https://github.com/lovasoa/marshmallow_dataclass/issues/50)).
   Thanks [@selimb](https://github.com/selimb).

## v7.1.1
 - Fix behavior when `base_schema` is passed to a nested dataclass/schema
   ([#52](https://github.com/lovasoa/marshmallow_dataclass/issues/52)).
   Thanks [@ADR-007-SoftServe](https://github.com/ADR-007-SoftServe)
   for the catch and patch.

## v7.1.0
 - Improved documentation
 - The library now has more unit tests
 - `dict` and `list` without type parameters are now supported

#### This is now supported
```python
from marshmallow_dataclass import dataclass


@dataclass
class Environment:
    env_variables: dict
```

However, we do still recommend you
to always use explicit type parameters, that is:

```python
from marshmallow_dataclass import dataclass
from typing import Dict


@dataclass
class Environment:
    env_variables: Dict[str, str]
```

## v7.0.0
 - Methods are not copied from the dataclass to the generated Schema anymore. (See [#47](https://github.com/lovasoa/marshmallow_dataclass/issues/47)).
   This breaks backward compatibility, but hopefully should not impact anyone since marshmallow-specific methods are still copied.
#### This does not work anymore:
```py
from marshmallow_dataclass import dataclass

@dataclass
class C:
    def say_hello():
       print("hello")

C.Schema.say_hello()
```

#### But this still works as expected:
```py
from marshmallow_dataclass import dataclass
from marshmallow import validates, ValidationError

@dataclass
class C:
    name: str
    @validates('name')
    def validates(self, value):
        if len(name) > 10: raise ValidationError("name too long")
```

## v6.1.0
 - [custom base schema](https://github.com/lovasoa/marshmallow_dataclass#customizing-the-base-schema)
 - [NewType declarations](https://github.com/lovasoa/marshmallow_dataclass#custom-newtype-declarations)
 
## v6.0.0
 - Dropped compatibility with marshmallow 2.

## v0.6.6
 - Added support for the `Any` type
