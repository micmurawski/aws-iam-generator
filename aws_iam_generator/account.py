import typing
from dataclasses import dataclass, field

from marshmallow import post_load

from .validators import AccountValidator, RegionValidator, VariableValidator


@dataclass
class Account:
    Description: typing.AnyStr = field(default=None)
    Id: typing.AnyStr = field(default=None)
    AccessRoleArn: typing.AnyStr = field(default=None)
    RegionName: typing.AnyStr = field(default='us-east-1')
    S3BucketKey: typing.AnyStr = field(default=None)
    RequireAccessRole: bool = field(default=True)

    def asdict(self):
        return {
            "Id": self.Id,
            "Description": self.Description,
            "S3BucketKey": self.S3BucketKey,
            "RegionName": self.RegionName,
            "AccessRoleArn": self.AccessRoleArn,
            "AccessRoleName": self.AccessRoleArn.rsplit('/')[-1] if self.AccessRoleArn else None
        }


@dataclass
class Region:
    Description: typing.AnyStr = field(default=None)
    Id: typing.AnyStr = field(default=None)

    def asdict(self):
        return {
            "Id": self.Id,
            "Description": self.Description,
        }


@dataclass
class Variable:
    Description: typing.AnyStr = field(default=None)
    Value: typing.AnyStr = field(default=None)
    Type: typing.AnyStr = field(default=None)

    def asdict(self):
        return {
            "Value": self.Value,
            "Description": self.Description,
            "Type": self.Type
        }


class AccountSerializer(AccountValidator):

    @post_load
    def load2obj(self, data, *args, **kwargs):
        if data["AccessRoleName"]:
            data['AccessRoleArn'] = f'arn:aws:iam::{data["Id"]}:role/' \
                                    f'{data["AccessRoleName"]}'
        data.pop("AccessRoleName")
        return Account(**data)


class RegionSerializer(RegionValidator):

    @post_load
    def load2obj(self, data, *args, **kwargs):
        return Region(**data)


class VariableSerializer(VariableValidator):

    @post_load
    def load2obj(self, data, *args, **kwargs):
        return Variable(**data)
