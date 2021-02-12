import json
import os

import pytest

from aws_iam_generator.serializers import AWSIAMRolesSpecificationSerializer


@pytest.fixture(scope='session')
def example_4_roles_specification():
    BASE_DIR = os.path.dirname(os.path.realpath(__file__))
    return json.load(open(os.path.join(BASE_DIR, 'input.json')))


@pytest.fixture(scope='session')
def serialized_example_4_roles_specification(example_4_roles_specification):
    obj = AWSIAMRolesSpecificationSerializer().load(data=example_4_roles_specification)
    obj.set_parameters(
        Accounts={
            "SharedServicesAccount": {
                "Id": "098765432109",
                "AccessRoleName": "DefaultAccessRole"
            }
        },
        Regions={},
        Variables={
            'HostedZoneID': {
                "Value": "1234567890"
            },
            'TrustAccountsIds': {
                "Value": ["123456789012"]
            },
            'TrustRolesArns': {
                "Value": ["arn:aws:iam::123456789012:role/ExampleRole"]
            }
        }
    )
    return obj


@pytest.fixture(scope='session')
def templates(serialized_example_4_roles_specification):
    serialized_example_4_roles_specification.Reference = ""

    return serialized_example_4_roles_specification.generate_cloudformation_templates()


@pytest.fixture(scope='session')
def shared_services_account_cf_template(templates):
    for template in templates:
        if template['Name'] == 'SharedServicesAccount-':
            return template


@pytest.fixture(scope='session')
def example_4_shared_services_account_template():
    BASE_DIR = os.path.dirname(os.path.realpath(__file__))
    return json.load(open(os.path.join(BASE_DIR, 'SharedServicesAccount.json')))
