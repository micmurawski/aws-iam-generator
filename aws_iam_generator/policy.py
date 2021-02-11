import typing
from dataclasses import dataclass

from marshmallow import fields, post_load

from aws_iam_generator.utils import ListOrValueField

from .validators import PolicyDocumentStatementValidator, PolicyDocumentValidator, PolicyValidator


@dataclass
class PolicyDocumentStatement:
    Action: typing.List
    Effect: typing.AnyStr
    Resource: typing.List

    def asdict(self):
        return {
            "Action": self.Action,
            "Effect": self.Effect,
            "Resource": self.Resource
        }


class PolicyDocumentStatementSerializer(PolicyDocumentStatementValidator):

    @post_load
    def load2obj(self, data, *args, **kwargs):
        return PolicyDocumentStatement(**data)


@dataclass
class PolicyDocument:
    Version: typing.AnyStr
    Statement: typing.List[PolicyDocumentStatement]

    def asdict(self):
        return {
            "Version": self.Version,
            "Statement": [i.asdict() for i in self.Statement]
        }


class PolicyDocumentSerializer(PolicyDocumentValidator):
    Statement = ListOrValueField(fields.Nested(PolicyDocumentStatementSerializer), missing=[])

    @post_load
    def load2obj(self, data, *args, **kwargs):
        return PolicyDocument(**data)


@dataclass
class Policy:
    Description: typing.AnyStr
    PolicyDocument: PolicyDocument


class PolicySerializer(PolicyValidator):
    PolicyDocument = fields.Nested(PolicyDocumentSerializer, missing=[])

    @post_load
    def load2obj(self, data, *args, **kwargs):
        return Policy(**data)
