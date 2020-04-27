import marshmallow
from . import dataclass


# extends Schema for instance check by polyfield
class SchemaPolyfieldProxy(marshmallow.Schema):
    """ Proxy class that implement Schema interface to proxify call to a
    dataclass. It is used in order to disambiguate Union subtype.
    By convention, we assume the dataclass has one field called "field"
    """

    def __init__(self, dataclass):
        self.schema = dataclass.Schema()
        self.dataclass = dataclass

    @property
    def context(self):
        return self.schema.context

    def dump(self, value):
        return self.schema.dump(self.dataclass(value))["field"]

    def load(self, value):
        return self.schema.load({"field": value}).field

    def check_deserialization(self, obj_dict):
        load = self.schema.load({"field": obj_dict})
        dump = self.schema.dump(load)["field"]
        if type(dump) != type(obj_dict):
            raise TypeError(
                "types do not match ({} is not {})".format(type(dump), type(obj_dict))
            )

    def check_serialization(self, obj):
        dump = self.schema.dump(self.dataclass(obj))
        load = self.schema.load(dump)
        if type(load.field) != type(obj):
            raise TypeError(
                "types do not match ({} is not {})".format(type(load.field), type(obj))
            )


def field_for_union(arguments, **metadata):
    def deserialization_disambiguation(obj_dict, base_dict):
        for subtype in arguments:

            @dataclass
            class dclass:
                field: subtype

            try:
                candidate = SchemaPolyfieldProxy(dclass)
                candidate.check_deserialization(obj_dict)
                return candidate
            except Exception:
                pass
        else:
            raise marshmallow.exceptions.ValidationError(
                "cannot deserialize union %s" % " ".join([str(a) for a in arguments])
            )

    def serialization_disambiguation(obj, base_obj):
        for subtype in arguments:

            @dataclass
            class dclass:
                field: subtype

            try:
                candidate = SchemaPolyfieldProxy(dclass)
                candidate.check_serialization(obj)
                return candidate
            except Exception:
                pass
        else:
            raise marshmallow.exceptions.ValidationError(
                "cannot serialize union %s" % " ".join([str(a) for a in arguments])
            )

    import marshmallow_polyfield

    return marshmallow_polyfield.PolyField(
        deserialization_schema_selector=deserialization_disambiguation,
        serialization_schema_selector=serialization_disambiguation,
        **metadata,
    )
