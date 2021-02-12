import typing
from dataclasses import dataclass, field
from os import path

from marshmallow import post_load

from .validators import RoleValidator, ServiceLinkedRoleValidator


class RoleException(Exception):
    pass


@dataclass
class Role:
    Trusts: typing.List[typing.AnyStr]
    Name: typing.AnyStr
    ManagedPolicies: typing.List[typing.AnyStr]
    InAccounts: typing.List[typing.AnyStr]
    Tags: typing.Dict[typing.AnyStr, typing.AnyStr] = field(default_factory=dict)
    _InAccounts: typing.List[typing.AnyStr] = field(default_factory=list)
    Description: typing.AnyStr = field(default=None)
    Path: typing.AnyStr = field(default='')

    @property
    def Arn(self):
        return [f'arn:aws:iam::{i}:role/{path.join(self.Path, self.Name)}' for i in self._InAccounts]


@dataclass
class ServiceLinkedRole:
    ServiceName: typing.AnyStr
    InAccounts: typing.List[typing.AnyStr]
    Description: typing.AnyStr = field(default=None)
    Tags: typing.Dict[typing.AnyStr, typing.AnyStr] = field(default_factory=dict)


class RoleSerializer(RoleValidator):

    @post_load
    def load2obj(self, data, *args, **kwargs):
        return Role(**data)


class ServiceLinkedRoleSerializer(ServiceLinkedRoleValidator):
    @post_load
    def load2obj(self, data, *args, **kwargs):
        return ServiceLinkedRole(**data)
