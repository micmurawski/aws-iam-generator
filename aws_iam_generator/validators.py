import re
from enum import Enum

from marshmallow import Schema, ValidationError, fields, validate

from aws_iam_generator.utils import ListOrValueField

from .utils import AWSIAMRoleARNField, aws_resource_name_validator

TYPES_REGEX = '(string|integer|list\\(string\\)|list\\(integer\\)|enum\\(\\d+(,\\d+)*\\)|enum\\(\\w+(,\\w+)*\\))'


class VariablesTypes(Enum):
    string = 'string'
    integer = 'integer'
    list_of_strings = 'list(string)'
    list_of_integers = 'list(integer)'
    enum_of_strings = 'enum\\(\\w+(,\\w+)*\\))'
    enum_of_integers = 'enum\\(\\d+(,\\d+)*\\)'

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

    @classmethod
    def get_schema(cls, value):
        _map = {
            'string': fields.String(required=True),
            'integer': fields.Integer(required=True),
            'list(string)': fields.List(fields.String, required=True),
            'list(integer)': fields.List(fields.Integer, required=True)
        }

        if value in cls.list():
            return _map[value]
        elif re.fullmatch(cls.enum_of_integers.value, value):
            values = value.replace('enum(', '').replace(')', '').split(',')
            values = [int(v) for v in values]
            return fields.List(fields.String, validate=validate.OneOf(values))
        elif re.fullmatch(cls.enum_of_strings.value, value):
            values = value.replace('enum(', '').replace(')', '').split(',')
            return fields.List(fields.String, validate=validate.OneOf(values))


class PolicyDocumentStatementValidator(Schema):
    Action = ListOrValueField(fields.String, missing=[])
    Effect = fields.String(required=True)
    Resource = ListOrValueField(fields.String, missing=[])


class RoleValidator(Schema):
    Tags = fields.Mapping(keys=fields.String, values=fields.String, allow_none=True)
    Name = fields.String(required=False, allow_none=True, validate=aws_resource_name_validator)
    Path = fields.String(required=False, allow_none=True, validate=aws_resource_name_validator)
    Trusts = ListOrValueField(fields.String, missing=[])
    ManagedPolicies = ListOrValueField(fields.String, missing=[])
    InAccounts = ListOrValueField(fields.String, missing=[])
    Description = fields.String(allow_none=True)


class ServiceLinkedRoleValidator(Schema):
    ServiceName = fields.String(required=True)
    InAccounts = ListOrValueField(fields.String, missing=[])
    Description = fields.String(allow_none=True)
    Tags = fields.Mapping(keys=fields.String, values=fields.String, allow_none=True)


class PolicyDocumentValidator(Schema):
    Version = fields.String(required=True)
    Statement = ListOrValueField(fields.Nested(PolicyDocumentStatementValidator), missing=[])


class AccountValidator(Schema):
    Description = fields.String(required=False, missing=None)
    AccessRoleArn = AWSIAMRoleARNField(required=False, missing=None)
    AccessRoleName = fields.String(required=False, missing=None)
    Id = fields.String(required=False, missing=None)
    S3BucketKey = fields.String(required=False, missing=None)
    RegionName = fields.String(required=False, missing='us-east-1')


class RegionValidator(Schema):
    Description = fields.String(required=False, missing=None)


class VariableValidator(Schema):
    Description = fields.String(required=False, missing=None)
    Type = fields.String(required=True, validate=validate.Regexp(TYPES_REGEX, error='{input} does not match {regex}'))


class PolicyValidator(Schema):
    Description = fields.String(required=True)
    PolicyDocument = fields.Nested(PolicyDocumentValidator, missing=[])


class AWSIAMRolesSpecificationValidator(Schema):
    Regions = fields.Mapping(keys=fields.String, values=fields.Nested(RegionValidator), default={})
    Accounts = fields.Mapping(keys=fields.String, values=fields.Nested(AccountValidator), default={})
    Variables = fields.Mapping(keys=fields.String, values=fields.Nested(VariableValidator), default={})
    Policies = fields.Mapping(keys=fields.String, values=fields.Nested(PolicyValidator), required=True)
    Roles = fields.Mapping(keys=fields.String(validate=aws_resource_name_validator),
                           values=fields.Nested(RoleValidator), required=True)
    ServiceLinkedRoles = fields.Mapping(keys=fields.String,
                                        values=fields.Nested(ServiceLinkedRoleValidator))


def validate_accounts(data):
    accounts = set(data['Accounts'].keys())  # mention deploy accounts here
    deploy_accounts = set()  # specify access for this

    for k, v in data.get('Roles', {}).items():
        deploy_accounts.update(set([i.split('.')[1] for i in v['InAccounts']]))

    for k, v in data.get('ServiceLinkedRoles', {}).items():
        deploy_accounts.update(set([i.split('.')[1] for i in v['InAccounts']]))

    if not accounts.intersection(deploy_accounts) == deploy_accounts:
        raise ValidationError(message={"Roles": [
            f'Following accounts were mentioned in Roles but not in Accounts '
            f'{", ".join(deploy_accounts.difference(accounts))}']})

    return data
