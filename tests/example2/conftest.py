import json
import os

import pytest

from aws_iam_generator.serializers import AWSIAMRolesSpecificationSerializer


@pytest.fixture(scope='session')
def example_2_roles_specification():
    BASE_DIR = os.path.dirname(os.path.realpath(__file__))
    return json.load(open(os.path.join(BASE_DIR, 'input.json')))


@pytest.fixture(scope='session')
def serialized_example_2_roles_specification(example_2_roles_specification):
    obj = AWSIAMRolesSpecificationSerializer().load(data=example_2_roles_specification)
    obj.set_parameters(
        Accounts={
            'AppsAccount': {
                "Id": '123456789012',
                "AccessRoleName": "DefaultAccessRole"
            },
            'PipelineAccount': {
                "Id": '456789012345',
                "AccessRoleName": "DefaultAccessRole"
            },
            'WorkloadUserAccount': {
                "Id": '789012345678',
                "AccessRoleName": "DefaultAccessRole"
            }
        },
        Regions={}
    )
    return obj


@pytest.fixture(scope='session')
def templates(serialized_example_2_roles_specification):
    serialized_example_2_roles_specification.Reference = ""
    return serialized_example_2_roles_specification.generate_cloudformation_templates()


@pytest.fixture(scope='session')
def workload_user_account_cf_template(templates):
    for template in templates:
        if template['Name'] == 'WorkloadUserAccount-':
            return template


@pytest.fixture(scope='session')
def apps_account_slr_cf_template(templates):
    for template in templates:
        if template['Name'] == 'AppsAccount--Service-Linked-Roles':
            return template
