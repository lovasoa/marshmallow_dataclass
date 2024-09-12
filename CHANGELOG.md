# marshmallow\_dataclass change log

## v8.7.1 (2024-09-12)

 - Relax dependency pins for `typeguard` and `typing-inspect`. ([#273], [#272])

[#272]: https://github.com/lovasoa/marshmallow_dataclass/issues/272
[#273]: https://github.com/lovasoa/marshmallow_dataclass/pull/273

## v8.7.0 (2024-06-23)

 - Drop support for python 3.6 and 3.7. Test under python 3.12. ([#263])
 - Add support for using `Annotated` (rather than our now deprecated
   custom `NewType`) to associate marshmallow configuration with
   particular types. ([#257])
 - Update pin to allow typeguard 4.*. This fixes issues with `Union`s
   of generic types. ([#260], [#261], [#250])

[#250]: https://github.com/lovasoa/marshmallow_dataclass/issues/250
[#257]: https://github.com/lovasoa/marshmallow_dataclass/pull/257
[#260]: https://github.com/lovasoa/marshmallow_dataclass/pull/260
[#261]: https://github.com/lovasoa/marshmallow_dataclass/pull/261
[#263]: https://github.com/lovasoa/marshmallow_dataclass/pull/263

## v8.6.1 (2024-03-20)

 - (Mostly) fix [memory leak][#198] when using
   `marshamallow_dataclass.dataclass` decorator. ([#258], thank you @mvanderlee!)
 - Fix docstring formatting for `class_schema`. ([#249])
 - Do not ignore `Union` argument ordering in tests. Note that a
   [bug][#247] remains: semantically, `Union`s do not respect argument
   order, yet order matters for de/serialization. ([#248])

[#198]: https://github.com/lovasoa/marshmallow_dataclass/issues/198
[#247]: https://github.com/lovasoa/marshmallow_dataclass/issues/247
[#248]: https://github.com/lovasoa/marshmallow_dataclass/pull/248
[#249]: https://github.com/lovasoa/marshmallow_dataclass/pull/249
[#258]: https://github.com/lovasoa/marshmallow_dataclass/pull/258

## v8.6.0 (2023-09-16)
 - New field in associated Meta classes: `include_non_init`:
  - This adds the ability to include non init-ed fields into the schema

## v8.5.14 (2023-04-27)

 - Pin `typing-extensions>=2.4.0` to ensure support for the
   `field_specifiers` paramter of the `dataclass_transform` decorator.
   ([#240])

 - Tighten pin on `typing-inspect` in an attempt to prevent
   breakage from a hypothetical major version bump.

 - Tighten pin on `typeguard` to exclude older versions
   for which our tests fail.

[#240]: https://github.com/lovasoa/marshmallow_dataclass/issues/240

## v8.5.13 (2023-04-20)

 - Fix to allow type-checkers to properly handle fields initialized
   by a `dataclasses.Field` instance. ([#239])

[#239]: https://github.com/lovasoa/marshmallow_dataclass/pull/239

## v8.5.12 (2023-03-15)

 - Fixes to work with typeguard 3.x. ([#235], [#234])
 - Add the @dataclass_transform decorator ([PEP 681]) to
   `marshmallow_dataclass.dataclass`. This fixes our mypy plugin for
   mypy>=1.1.1.

[#234]: https://github.com/lovasoa/marshmallow_dataclass/issues/234
[#235]: https://github.com/lovasoa/marshmallow_dataclass/pull/235
[PEP 681]: https://peps.python.org/pep-0681/

## v8.5.11 (2023-01-08)

 - Replace the use of `marshmallow-enum` with the native
   `marshmallow.field.Enum` (when using a sufficiently recent version
   of `marshmallow`). ([#227][], [#225][])

[#225]: https://github.com/lovasoa/marshmallow_dataclass/issues/225
[#227]: https://github.com/lovasoa/marshmallow_dataclass/pull/227

## v8.5.10 (2022-11-09)

 - We now test under python version 3.11 (as well as 3.6 through 3.10). ([#220][])

 - Recognize the variable-length, homogeneous tuple types `Tuple[T,
   ...]` (and `tuple[T, ...]` under python >= 3.8).  These are
   equivalent to the previously recognized `Sequence[T]`. ([#221][])

 - Recognize PEP 604, `T | U`, union notation (requires python >=
   3.10). Fixes [#194][]. ([#219][])

[#181]: https://github.com/lovasoa/marshmallow_dataclass/issues/181
[#194]: https://github.com/lovasoa/marshmallow_dataclass/issues/194
[#219]: https://github.com/lovasoa/marshmallow_dataclass/pull/219
[#220]: https://github.com/lovasoa/marshmallow_dataclass/pull/220
[#221]: https://github.com/lovasoa/marshmallow_dataclass/pull/221

## v8.5.9 (2022-10-04)

 - Fix [#206][]: NewType breakage with `typing-inspect>=0.8.0`
   ([#207][], [#211][])
 - Fix tests for python 3.11 ([#212][])
 
[#206]: https://github.com/lovasoa/marshmallow_dataclass/issues/206
[#207]: https://github.com/lovasoa/marshmallow_dataclass/pull/207
[#211]: https://github.com/lovasoa/marshmallow_dataclass/pull/211
[#212]: https://github.com/lovasoa/marshmallow_dataclass/pull/212

## v8.5.7, v8.5.8

 - Fix https://github.com/lovasoa/marshmallow_dataclass/issues/190

## v8.5.6

 - Fix bug introduced in previous release. See https://github.com/lovasoa/marshmallow_dataclass/pull/189

## v8.5.5

- Fix slowdown introduced in v8.5.4. See https://github.com/lovasoa/marshmallow_dataclass/pull/187

## v8.5.4

- Add support for the Final type. See [#150](https://github.com/lovasoa/marshmallow_dataclass/pull/150) and [#151](https://github.com/lovasoa/marshmallow_dataclass/pull/151)
- Add support for [forward references](https://peps.python.org/pep-0484/#forward-references) and [ Postponed Evaluation of Annotations](https://peps.python.org/pep-0563/). (See [#13](https://github.com/lovasoa/marshmallow_dataclass/issues/13))
- update dependencies

## v8.5.3

- Fix spurious `ValueError` when defining a Union field with explicit default value
  ([#161](https://github.com/lovasoa/marshmallow_dataclass/pull/161))

## v8.5.2

- Fix spurious `TypeError` when serializing `Optional` union types with `required=True`
  ([#160](https://github.com/lovasoa/marshmallow_dataclass/pull/160))

## v8.5.1

- Allow setting required=True on fields of type Optional
  ([#159](https://github.com/lovasoa/marshmallow_dataclass/pull/159))

## v8.5.0
- Fix `default` warning coming from marshmallow. Bump minimal marshmallow version requirement to 3.13. [See #157](https://github.com/lovasoa/marshmallow_dataclass/issues/157).
- Add support for the Final type. See [#150](https://github.com/lovasoa/marshmallow_dataclass/pull/150)

## v8.4.2

- Compatibility with python3.9 lowercase type annotations. [See #136](https://github.com/lovasoa/marshmallow_dataclass/issues/136)

## v8.4.1

 - Fix compatibility with older python versions.
   

## v8.4.0

- Add support for multiple [`collections.abc`](https://docs.python.org/3/library/collections.abc.html) containers :
   - Mapping
   - Sequence
   - Set 
   - FrozenSet
  - (see [#131](https://github.com/lovasoa/marshmallow_dataclass/issues/131))

You can now write :

```python3
from marshmallow_dataclass import dataclass
from collections.abc import Sequence, Mapping, Set

@dataclass
class FrozenData:
   seq: Sequence[int] # like List[int], but immutable 
   map: Mapping[str, int] # like Dict[str, int], but immutable 
   set: Set[int] # like List[int], but unordered

f: FrozenData = FrozenData.Schema().load({"seq":[1], "map":{"x":2}, "set":[2]})
print(f.seq[0]) # -> 1
print(f.map["x"]) # -> 2
print(2 in f.set) # -> True
```

## v8.3.2

 - Fix package license field

## v8.3.1

 - Allow `None` in Optional fields. See [#108](https://github.com/lovasoa/marshmallow_dataclass/issues/108) 

## v8.3.0

 - Export pre-built Email and Url types. See [#115](https://github.com/lovasoa/marshmallow_dataclass/pull/115)

## v8.2.0

 - Add support for the Literal type. See [#110](https://github.com/lovasoa/marshmallow_dataclass/pull/110)

## v8.1.0

 - Improved support for Optional types

## v8.0.0
 - Better support for unions (See [#93](https://github.com/lovasoa/marshmallow_dataclass/pull/93)).
 - Added support for validator stacking. This breaks backwards compatability. See https://github.com/lovasoa/marshmallow_dataclass/issues/91.
    ### What this means:
    ```python
    CustomType = NewType("CustomType", str, validate=marshmallow.validate.Length(min=3))


    @dataclass
    class CustomObject:
        some_field: CustomType = field(metadata={"validate": marshmallow.validate.URL()})
    ```
    The following code will produce a field with the following list of validators: `[marshmallow.validate.Length(min=3), marshmallow.validate.URL()]` instead of the previous: `[marshmallow.validate.URL()]`.

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
