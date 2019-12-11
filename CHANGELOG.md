# marshmallow_dataclass change log

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
