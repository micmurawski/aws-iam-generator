from troposphere import Output as AWSOutput
from troposphere.iam import ManagedPolicy as AWSManagedPolicy
from troposphere.iam import Role as AWSRole
from troposphere.iam import ServiceLinkedRole as AWSServiceLinkedRole

from .utils import VALID_AWS_RESOURCE_NAMES


class Output(AWSOutput):
    def validate_title(self):
        if not VALID_AWS_RESOURCE_NAMES.match(self.title):
            raise ValueError(f'Name {self.title} not not match {VALID_AWS_RESOURCE_NAMES}')


class ManagedPolicy(AWSManagedPolicy):
    def validate_title(self):
        if not VALID_AWS_RESOURCE_NAMES.match(self.title):
            raise ValueError(f'Name {self.title} not not match {VALID_AWS_RESOURCE_NAMES}')


class Role(AWSRole):
    def validate_title(self):
        if not VALID_AWS_RESOURCE_NAMES.match(self.title):
            raise ValueError(f'Name {self.title} not not match {VALID_AWS_RESOURCE_NAMES}')


class ServiceLinkedRole(AWSServiceLinkedRole):
    def validate_title(self):
        if not VALID_AWS_RESOURCE_NAMES.match(self.title):
            raise ValueError(f'Name {self.title} not not match {VALID_AWS_RESOURCE_NAMES}')
