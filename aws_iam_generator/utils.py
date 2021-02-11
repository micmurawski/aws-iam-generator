import re
import typing

from marshmallow import Schema, ValidationError, fields, validate

VALID_AWS_RESOURCE_NAMES = re.compile(r'^[a-zA-Z0-9]+$')

aws_resource_name_validator = validate.Regexp(VALID_AWS_RESOURCE_NAMES, error='{input} does not match {regex}')


def parse_account_id(account_id):
    if len(str(account_id)) < 12:
        return ('0' * (len(str(account_id)) - 12)) + str(account_id)
    return account_id


class ListOrValueField(fields.List):
    def __init__(self, cls_or_instance: typing.Union[fields.Field, type], **kwargs) -> None:
        super().__init__(cls_or_instance, **kwargs)

    def _serialize(self, value, attr, obj, **kwargs) -> typing.Optional[typing.List[typing.Any]]:
        if isinstance(value, str):
            return super()._serialize([value], attr, obj, **kwargs)
        return super()._serialize(value, attr, obj, **kwargs)

    def _deserialize(self, value, attr, data, **kwargs) -> typing.List[typing.Any]:
        if isinstance(value, str):
            return super()._deserialize([value], attr, data, **kwargs)
        return super()._deserialize(value, attr, data, **kwargs)

    def _validated(self, value):
        if isinstance(value, str):
            return self._validate([value])
        else:
            return self._validate(value)


class IntOrString(fields.String):

    def _serialize(self, value, attr, obj, **kwargs) -> typing.Optional[typing.List[typing.Any]]:
        if isinstance(value, int):
            return super()._serialize(str(value), attr, obj, **kwargs)
        return super()._serialize(value, attr, obj, **kwargs)

    def _deserialize(self, value, attr, data, **kwargs) -> typing.List[typing.Any]:
        if isinstance(value, int):
            return super()._deserialize(str(value), attr, data, **kwargs)
        return super()._deserialize(value, attr, data, **kwargs)

    def _validated(self, value):
        if isinstance(value, int):
            return self._validate(str(value))
        else:
            return self._validate(value)


class OneOfSchema(Schema):
    type_field = "type"
    type_field_remove = True
    type_schemas = {}

    def get_obj_type(self, obj):
        """Returns name of object schema"""
        return obj.__class__.__name__

    def dump(self, obj, *, many=None, **kwargs):
        errors = {}
        result_data = []
        result_errors = {}
        many = self.many if many is None else bool(many)
        if not many:
            result = result_data = self._dump(obj, **kwargs)
        else:
            for idx, o in enumerate(obj):
                try:
                    result = self._dump(o, **kwargs)
                    result_data.append(result)
                except ValidationError as error:
                    result_errors[idx] = error.normalized_messages()
                    result_data.append(error.valid_data)

        result = result_data
        errors = result_errors

        if not errors:
            return result
        else:
            exc = ValidationError(errors, data=obj, valid_data=result)
            raise exc

    def _dump(self, obj, *, update_fields=True, **kwargs):
        obj_type = self.get_obj_type(obj)
        if not obj_type:
            return (
                None,
                {"_schema": "Unknown object class: %s" % obj.__class__.__name__},
            )

        type_schema = self.type_schemas.get(obj_type)
        if not type_schema:
            return None, {"_schema": "Unsupported object type: %s" % obj_type}

        schema = type_schema if isinstance(type_schema, Schema) else type_schema()

        schema.context.update(getattr(self, "context", {}))

        result = schema.dump(obj, many=False, **kwargs)
        if result is not None:
            result[self.type_field] = obj_type
        return result

    def load(self, data, *, many=None, partial=None, unknown=None, **kwargs):
        errors = {}
        result_data = []
        result_errors = {}
        many = self.many if many is None else bool(many)
        if partial is None:
            partial = self.partial
        if not many:
            try:
                result = result_data = self._load(
                    data, partial=partial, unknown=unknown, **kwargs
                )
                #  result_data.append(result)
            except ValidationError as error:
                result_errors = error.normalized_messages()
                result_data.append(error.valid_data)
        else:
            for idx, item in enumerate(data):
                try:
                    result = self._load(item, partial=partial, **kwargs)
                    result_data.append(result)
                except ValidationError as error:
                    result_errors[idx] = error.normalized_messages()
                    result_data.append(error.valid_data)

        result = result_data
        errors = result_errors

        if not errors:
            return result
        else:
            exc = ValidationError(errors, data=data, valid_data=result)
            raise exc

    def _load(self, data, *, partial=None, unknown=None, **kwargs):
        if not isinstance(data, dict):
            raise ValidationError({"_schema": "Invalid data type: %s" % data})

        data = dict(data)
        unknown = unknown or self.unknown

        data_type = data.get(self.type_field)
        if self.type_field in data and self.type_field_remove:
            data.pop(self.type_field)

        if not data_type:
            raise ValidationError(
                {self.type_field: ["Missing data for required field."]}
            )

        try:
            type_schema = self.type_schemas.get(data_type)
        except TypeError:
            # data_type could be unhashable
            raise ValidationError({self.type_field: ["Invalid value: %s" % data_type]})
        if not type_schema:
            raise ValidationError(
                {self.type_field: ["Unsupported value: %s" % data_type]}
            )

        schema = type_schema if isinstance(type_schema, Schema) else type_schema()

        schema.context.update(getattr(self, "context", {}))

        return schema.load(data, many=False, partial=partial, unknown=unknown, **kwargs)

    def validate(self, data, *, many=None, partial=None):
        try:
            self.load(data, many=many, partial=partial)
        except ValidationError as ve:
            return ve.messages
        return {}


class AWSIAMRoleARNField(fields.String):
    def __init__(self, *args, **kwargs):
        pattern = 'arn:aws:iam::\\d{12}:role/.+'
        arn_validator = validate.Regexp(pattern, error='{input} does not match ARN format {regex}')
        super().__init__(*args, validate=arn_validator, example='arn:aws:iam::123456789012:role/ExampleRoleName',
                         description='AWS IAM Role ARN', **kwargs)


def patch_dict(a: dict, b: dict):
    for k1, v1 in b.items():
        for k2, v2 in v1.asdict().items():
            if k1 not in a:
                a[k1] = {}
            if v2 and k2 not in ("Description", "AccessRoleArn", "Type"):
                a[k1][k2] = v2
