import copy
from typing import Any, List, Mapping, Optional, Tuple

import typeguard
from marshmallow import fields, Schema, ValidationError

try:
    from typeguard import TypeCheckError  # type: ignore[attr-defined]
except ImportError:
    # typeguard < 3
    TypeCheckError = TypeError


class Union(fields.Field):
    """A union field, composed other `Field` classes or instances.
    This field serializes elements based on their type, with one of its child fields.

    Example: ::

        number_or_string = UnionField([
                    (float, fields.Float()),
                    (str, fields.Str())
                ])

    :param union_fields: A list of types and their associated field instance.
    :param kwargs: The same keyword arguments that :class:`Field` receives.
    """

    def __init__(self, union_fields: List[Tuple[type, fields.Field]], **kwargs: Any):
        super().__init__(**kwargs)
        self.union_fields = union_fields

    def _bind_to_schema(self, field_name: str, schema: Schema) -> None:
        super()._bind_to_schema(field_name, schema)  # type: ignore[no-untyped-call]
        new_union_fields = []
        for typ, field in self.union_fields:
            field = copy.deepcopy(field)
            field._bind_to_schema(field_name, self)  # type: ignore[no-untyped-call]
            new_union_fields.append((typ, field))

        self.union_fields = new_union_fields

    def _serialize(
        self, value: Any, attr: Optional[str], obj: Any, **kwargs: Any
    ) -> Any:
        errors = []
        if value is None:
            return value
        for typ, field in self.union_fields:
            try:
                typeguard.check_type(
                    value=value, expected_type=typ, argname=attr or "anonymous"
                )
                return field._serialize(value, attr, obj, **kwargs)
            except TypeCheckError as e:
                errors.append(e)
        raise TypeError(
            f"Unable to serialize value with any of the fields in the union: {errors}"
        )

    def _deserialize(
        self,
        value: Any,
        attr: Optional[str],
        data: Optional[Mapping[str, Any]],
        **kwargs: Any,
    ) -> Any:
        errors = []
        for typ, field in self.union_fields:
            try:
                result = field.deserialize(value, **kwargs)
                typeguard.check_type(
                    value=result, expected_type=typ, argname=attr or "anonymous"
                )
                return result
            except (TypeCheckError, ValidationError) as e:
                errors.append(e)

        raise ValidationError(errors)
