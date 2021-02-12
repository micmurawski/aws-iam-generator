import re
import typing
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4

from marshmallow import Schema, fields, missing, post_load, pre_load, validate
from marshmallow.exceptions import ValidationError
from troposphere import Export, GetAtt, Ref, Sub, Template

from .account import Account, AccountSerializer, Region, RegionSerializer, Variable, VariableSerializer
from .aws import ManagedPolicy, Output
from .aws import Role as AWSRole
from .aws import ServiceLinkedRole as AWSServiceLinkedRole
from .policy import Policy, PolicySerializer
from .role import Role, RoleSerializer, ServiceLinkedRole, ServiceLinkedRoleSerializer
from .utils import AWSIAMRoleARNField, aws_resource_name_validator, parse_account_id, patch_dict
from .validators import AWSIAMRolesSpecificationValidator, VariablesTypes, validate_accounts

REF_PATTERN = "(.*)"
VAR_PATTERN = "(?<={{)([^x}}]+)(?=}})"
SUB_PATTERN = "(?<={)([^x}]+)(?=})"


class IAMRolesTypes(Enum):
    GENERIC = 'GENERIC'
    SERVICE_LINKED_ROLES = 'SERVICE_LINKED_ROLES'


class AccountIdSerializer(Schema):
    Id = fields.String(required=True, validate=validate.Regexp(r'\d{12}'))
    AccessRoleArn = AWSIAMRoleARNField(required=False, missing=None)
    S3BucketKey = fields.String(required=False, missing=None)
    RegionName = fields.String(required=False, missing='us-east-1')
    AccessRoleName = fields.String(required=False, missing=None)

    @post_load
    def load2obj(self, data, *args, **kwargs):
        if not self.context.get('RequireAccessRole', False):
            pass
        else:
            if not (data['AccessRoleArn'] or data['AccessRoleName']):
                raise ValidationError(message={
                    "Error": ["Account was not provided with AccessRoleName or AccessRoleArn."]
                })
            elif data.get('AccessRoleName'):
                data['AccessRoleArn'] = f'arn:aws:iam::{data["Id"]}:role/' \
                                        f'{data.pop("AccessRoleName")}'

        data.pop('AccessRoleName', None)
        data['Id'] = parse_account_id(data['Id'])
        return Account(**data)


class VariableValueSerializer(Schema):
    @classmethod
    def get_value_serializer_class(cls, variable: Variable):
        class GeneratedSchema(Schema):
            Value = VariablesTypes.get_schema(variable.Type)

            @post_load
            def load2obj(self, data, *args, **kwargs):
                return Variable(**data)

        return GeneratedSchema


class RegionIdSerializer(Schema):
    Id = fields.String(required=True)

    @post_load
    def load2obj(self, data, *args, **kwargs):
        return Region(**data)


@dataclass(frozen=False)
class AWSIAMRolesSpecification:
    Accounts: typing.Dict[str, Account]
    Policies: typing.Dict[str, Policy]
    Roles: typing.Dict[str, Role]
    Variables: typing.Dict[str, Variable] = field(default_factory=dict)
    Regions: typing.Dict[str, Region] = field(default_factory=dict)
    ServiceLinkedRoles: typing.Dict[str, ServiceLinkedRole] = field(default_factory=dict)
    Reference: typing.AnyStr = field(default=uuid4().hex)

    @property
    def build_version(self):
        return datetime.utcnow().strftime("%Y-%m-%dZ%H:%M:%S")

    def parse(self):
        for key, policy in self.Policies.items():
            for statement in policy.PolicyDocument.Statement:
                for i in range(len(statement.Resource)):
                    _vars = re.compile(VAR_PATTERN).findall(statement.Resource[i])
                    sub = statement.Resource[i]
                    for var in _vars:
                        _id = self.get_variable(var)
                        sub = sub.replace("{{" + var + "}}", str(_id))
                    statement.Resource[i] = Sub(sub) if re.compile(SUB_PATTERN).findall(statement.Resource[i]) else sub

        for role in self.Roles.values():
            role._InAccounts = [self.get_variable(i) for i in role.InAccounts]

        for role in self.Roles.values():
            parsed_trusts = []

            for i in range(len(role.Trusts)):
                if 'Accounts.' in role.Trusts[i]:
                    parsed_trusts.append(self.get_variable(role.Trusts[i]))
                elif 'Roles.' in role.Trusts[i]:
                    parsed_trusts += self.get_variable(role.Trusts[i])
                elif 'Variables.' in role.Trusts[i]:
                    value = self.get_variable(role.Trusts[i])
                    if type(value) == list:
                        parsed_trusts += value
                    else:
                        parsed_trusts.append(value)
                elif re.compile(VAR_PATTERN).findall(role.Trusts[i]):
                    _id = self.get_variable(role.Trusts[i])
                    if type(_id) == list:
                        parsed_trusts += _id
                    else:
                        parsed_trusts.append(_id)
                else:
                    parsed_trusts.append(role.Trusts[i])

            role.Trusts = parsed_trusts

            for i in range(len(role.ManagedPolicies)):
                if '.' in role.ManagedPolicies[i]:
                    ref = role.ManagedPolicies[i].split('.')[-1]
                    role.ManagedPolicies[i] = Ref(ref)

    def get_variable(self, path):
        try:
            _path = path.replace('{{', '').replace('}}', '').split('.')
            value = getattr(getattr(self, _path[0])[_path[1]], _path[2])
        except Exception as e:
            raise ValidationError(message=f'Could not find variable with path: {path}') from e
        return value

    def set_parameters(self, Accounts={}, Regions={}, Variables={}):
        accounts_fields_map = {
            k: fields.Nested(
                AccountIdSerializer(
                    context={'RequireAccessRole': v.RequireAccessRole, "Name": k}
                ),
                required=False if v.Id else True,
                missing=v if v.Id else missing,
            ) for k, v
            in self.Accounts.items()
        }
        regions_fields_map = {
            k: fields.Nested(
                RegionIdSerializer,
                required=False if v.Id else True,
                missing=v if v.Id else missing,
            ) for k, v in self.Regions.items()
        }

        variables_fields_map = {
            k: fields.Nested(
                VariableValueSerializer.get_value_serializer_class(self.Variables[k]),
                required=True
            ) for k in self.Variables.keys()
        }

        accounts_schema = Schema.from_dict(accounts_fields_map)
        regions_schema = Schema.from_dict(regions_fields_map)
        variables_schema = Schema.from_dict(variables_fields_map)

        validator = Schema.from_dict({
            'Accounts': fields.Nested(accounts_schema),
            'Regions': fields.Nested(regions_schema),
            'Variables': fields.Nested(variables_schema)
        })
        patch_dict(Accounts, self.Accounts)
        patch_dict(Regions, self.Regions)
        patch_dict(Variables, self.Variables)

        result = validator().load(data={
            'Accounts': Accounts,
            'Regions': Regions,
            'Variables': Variables
        })
        self.Accounts = result['Accounts']
        self.Regions = result['Regions']
        self.Variables = result['Variables']
        self.parse()
        return self.generate_cloudformation_templates()

    def generate_cloudformation_templates(self):
        templates = {k: Template() for k, v in self.Accounts.items()}
        slr_templates = {k: Template() for k, v in self.Accounts.items()}
        templates_names = {}
        slr_templates_names = {}

        for k, v in self.Accounts.items():
            templates_names[k] = v.asdict()
            templates_names[k].update({
                "Name": f'{k}-{self.Reference}'
            })

        for k, v in self.Accounts.items():
            slr_templates_names[k] = v.asdict()
            slr_templates_names[k].update({
                "Name": f'{k}-{self.Reference}-Service-Linked-Roles'
            })

        for role_name, role in self.Roles.items():
            service = []
            aws = []
            for i in role.Trusts:
                if isinstance(i, str) and "amazonaws" in i:
                    if i not in service:
                        service.append(i)
                elif isinstance(i, list):
                    for j in i:
                        if isinstance(j, str) and "amazonaws" in i:
                            if i not in service:
                                service.append(j)
                        else:
                            if re.match("\\d{12}", j) or j == "*":
                                aws.append(f"arn:aws:iam::{j}:root")
                            else:
                                aws.append(j)
                else:
                    if isinstance(i, str) and "amazonaws" in i:
                        service.append(i)
                    else:
                        try:
                            if re.match("\\d{12}", i) or i == "*":
                                aws.append(f"arn:aws:iam::{i}:root")
                            else:
                                aws.append(i)
                        except TypeError:
                            raise ValidationError(f'Value {i} does not match AWSAccountId or IAM Role Arn format.')

            assume_role_policy_document = {
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {}
                    }
                ],
                "Version": "2012-10-17"
            }
            if service:
                assume_role_policy_document["Statement"][0]["Principal"]['Service'] = service
            if aws:
                assume_role_policy_document["Statement"][0]["Principal"]['AWS'] = aws
            for managed_policy_ref in role.ManagedPolicies:
                if isinstance(managed_policy_ref, Ref):
                    managed_policy_name = managed_policy_ref.to_dict()['Ref']
                    try:
                        policy = self.Policies[managed_policy_name]
                    except KeyError:
                        raise ValidationError(
                            {
                                'Roles': [f'Cloud not find policy template: {managed_policy_name}']
                            }
                        )
                    for i in role.InAccounts:
                        account_name = i.split('.')[1]
                        if managed_policy_name not in templates[account_name].resources:
                            templates[account_name].add_resource(ManagedPolicy(
                                managed_policy_name,
                                Description=policy.Description,
                                Groups=[],
                                ManagedPolicyName=managed_policy_name,
                                PolicyDocument=policy.PolicyDocument.asdict()
                            ))

            for i in role.InAccounts:
                account_name = i.split('.')[1]
                name = role_name
                templates[account_name].add_resource(AWSRole(
                    role_name,
                    AssumeRolePolicyDocument=assume_role_policy_document,
                    ManagedPolicyArns=role.ManagedPolicies,
                    RoleName=name
                ))
                templates[account_name].add_output([
                    Output(
                        role_name + "Arn",
                        Description=role.Description or '',
                        Value=GetAtt(role_name, 'Arn'),
                        Export=Export(Sub("${AWS::StackName}-" + role_name + "Arn"))
                    )
                ])

        for role_name, role in self.ServiceLinkedRoles.items():
            for i in role.InAccounts:
                account_name = i.split('.')[1]
                role_name = role_name.replace('_', '')
                slr_templates[account_name].add_resource(AWSServiceLinkedRole(
                    role_name,
                    Description=role.Description or '',
                    AWSServiceName=role.ServiceName
                ))
                slr_templates[account_name].add_output([
                    Output(
                        role_name + "Ref",
                        Description=role.Description or '',
                        Value=Ref(role_name),
                        Export=Export(Sub("${AWS::StackName}-" + role_name + "Ref"))
                    )
                ])

        result = []
        for account_name, template in templates.items():
            if template.resources:
                result.append(
                    {
                        'AWSAccountID': templates_names[account_name]["Id"],
                        'AccessRoleArn': templates_names[account_name]["AccessRoleArn"],
                        'RegionName': templates_names[account_name]["RegionName"],
                        'S3BucketKey': templates_names[account_name]["S3BucketKey"],
                        'Name': templates_names[account_name]["Name"],
                        'Body': template.to_dict(),
                        "Type": IAMRolesTypes.GENERIC.value
                    }
                )

        for account_name, template in slr_templates.items():
            if template.resources:
                result.append(
                    {
                        'AWSAccountID': slr_templates_names[account_name]["Id"],
                        'AccessRoleArn': slr_templates_names[account_name]["AccessRoleArn"],
                        'RegionName': slr_templates_names[account_name]["RegionName"],
                        'S3BucketKey': slr_templates_names[account_name]["S3BucketKey"],
                        'Name': slr_templates_names[account_name]["Name"],
                        'Body': template.to_dict(),
                        "Type": IAMRolesTypes.SERVICE_LINKED_ROLES.value
                    }
                )

        return result


class AWSIAMRolesSpecificationSerializer(AWSIAMRolesSpecificationValidator):
    Accounts = fields.Mapping(keys=fields.String, values=fields.Nested(AccountSerializer), default={})
    Regions = fields.Mapping(keys=fields.String, values=fields.Nested(RegionSerializer), default={})
    Variables = fields.Mapping(keys=fields.String, values=fields.Nested(VariableSerializer), default={})
    Policies = fields.Mapping(keys=fields.String, values=fields.Nested(PolicySerializer))
    Roles = fields.Mapping(keys=fields.String(validate=aws_resource_name_validator),
                           values=fields.Nested(RoleSerializer))
    ServiceLinkedRoles = fields.Mapping(keys=fields.String,
                                        values=fields.Nested(ServiceLinkedRoleSerializer), default={})

    @pre_load
    def pre_load_validate(self, data, *args, **kwargs):
        validate_accounts(data)

        for k, v in data['Roles'].items():
            if 'Name' not in v:
                v['Name'] = k

        return data

    @post_load
    def load2obj(self, data, *args, **kwargs):
        accounts = set(data['Accounts'].keys())
        deploy_accounts = set()

        for k, v in data.get('Roles', {}).items():
            deploy_accounts.update(set([i.split('.')[1] for i in v.InAccounts]))
        for k, v in data.get('Roles', {}).items():
            deploy_accounts.update(set([i.split('.')[1] for i in v.InAccounts]))
        for k, v in data.get('ServiceLinkedRoles', {}).items():
            deploy_accounts.update(set([i.split('.')[1] for i in v.InAccounts]))

        for acc in accounts.difference(deploy_accounts):
            data['Accounts'][acc].RequireAccessRole = False

        return AWSIAMRolesSpecification(**data)
