import copy
from typing import List, Tuple, Any

import typeguard
from marshmallow import fields, Schema, ValidationError


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

    def __init__(self, union_fields: List[Tuple[type, fields.Field]], **kwargs):
        super().__init__(**kwargs)
        self.union_fields = union_fields

    def _bind_to_schema(self, field_name: str, schema: Schema) -> None:
        super()._bind_to_schema(field_name, schema)
        new_union_fields = []
        for typ, field in self.union_fields:
            field = copy.deepcopy(field)
            field._bind_to_schema(field_name, self)
            new_union_fields.append((typ, field))

        self.union_fields = new_union_fields

    def _serialize(self, value: Any, attr: str, obj, **kwargs) -> Any:
        errors = []
        if value is None and not self.required:
            return value
        for typ, field in self.union_fields:
            try:
                typeguard.check_type(attr, value, typ)
                return field._serialize(value, attr, obj, **kwargs)
            except TypeError as e:
                errors.append(e)
        raise TypeError(
            f"Unable to serialize value with any of the fields in the union: {errors}"
        )

    def _deserialize(self, value: Any, attr: str, data, **kwargs) -> Any:
        errors = []
        for typ, field in self.union_fields:
            try:
                result = field.deserialize(value, **kwargs)
                typeguard.check_type(attr, result, typ)
                return result
            except (TypeError, ValidationError) as e:
                errors.append(e)

        raise ValidationError(errors)
