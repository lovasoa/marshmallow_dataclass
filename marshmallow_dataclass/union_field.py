import copy
from typing import List, Tuple, Any, Optional

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

    # def _serialize(self, value: Any, attr: str, obj, **kwargs) -> Any:
        
    #     errors = []
    #     if value is None:
    #         return value
    #     for typ, field in self.union_fields:
    #         if typ.__dict__.get("__supertype__") and typ.__dict__.get(
    #             "_marshmallow_field"
    #         ):
    #             typ = typ.__supertype__
    #         try:
    #             typeguard.check_type(attr, value, typ)
    #             return field._serialize(value, attr, obj, **kwargs)
    #         except TypeError as e:
    #             errors.append(e)
    #     raise TypeError(
    #         f"Unable to serialize value with any of the fields in the union: {errors}"
    #     )

    def _serialize(self, value: Any, attr: str, obj, **kwargs) -> Any:
        print("value")
        print(value)
        asd
        errors = []
        serialized_outputs = {}
        num_successfully_serialized_outputs = 0
        num_expected_serialized_outputs = len(value.__annotations__.keys())
        if value is None:
            return value

        for param_key in value.__annotations__.keys():
            print("param_key")
            print(param_key)
            print(getattr(value, param_key))
            param_value = getattr(value, param_key)

            for typ, field in self.union_fields:                
                # print("typ")
                # print(typ)
                # print("field")
                # print(field)
                # print("param_value")
                # print(param_value)
                # print(value)
                # print("value dir")
                # print((dir(value)))
                # print("__supertype__")
                # print((typ.__supertype__))
                if typ.__dict__.get("__supertype__") and typ.__dict__.get(
                    "_marshmallow_field"
                ):
                    typ = typ.__supertype__
                    print(typ)
                try:
                    typeguard.check_type(attr, param_value, typ)
                    serialized_output = field._serialize(param_value, attr, obj, **kwargs)
                    print("serialized_output")
                    print(serialized_output)
                    serialized_outputs[param_key] = serialized_output
                    num_successfully_serialized_outputs += 1
                except TypeError as e:
                    errors.append(e)
        print(num_successfully_serialized_outputs)
        if num_successfully_serialized_outputs != num_expected_serialized_outputs:
            raise TypeError(
                f"Unable to serialize value with any of the fields in the union: {errors}"
            )
        else:
            return serialized_outputs


    def _deserialize(self, value: Any, attr: Optional[str], data, **kwargs) -> Any:
        errors = []
        for typ, field in self.union_fields:
            try:
                result = field.deserialize(value, **kwargs)
                typeguard.check_type(attr or "anonymous", result, typ)
                return result
            except (TypeError, ValidationError) as e:
                errors.append(e)

        raise ValidationError(errors)
