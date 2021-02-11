import typing
from dataclasses import dataclass, field

from marshmallow import post_load

from .validators import RoleValidator, ServiceLinkedRoleValidator


@dataclass
class Role:
    Trusts: typing.List[typing.AnyStr]
    ManagedPolicies: typing.List[typing.AnyStr]
    InAccounts: typing.List[typing.AnyStr]
    Category: typing.List[typing.AnyStr] = field(default_factory=list)
    Description: typing.AnyStr = field(default=None)


@dataclass
class ServiceLinkedRole:
    ServiceName: typing.AnyStr
    InAccounts: typing.List[typing.AnyStr]
    Description: typing.AnyStr = field(default=None)
    Category: typing.List[typing.AnyStr] = field(default_factory=list)


class RoleSerializer(RoleValidator):

    @post_load
    def load2obj(self, data, *args, **kwargs):
        return Role(**data)


class ServiceLinkedRoleSerializer(ServiceLinkedRoleValidator):
    @post_load
    def load2obj(self, data, *args, **kwargs):
        return ServiceLinkedRole(**data)
