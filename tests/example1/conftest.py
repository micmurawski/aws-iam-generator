import json
import os

import pytest

from aws_iam_generator.serializers import AWSIAMRolesSpecificationSerializer


@pytest.fixture(scope='session')
def example_1_roles_specification():
    BASE_DIR = os.path.dirname(os.path.realpath(__file__))
    return json.load(open(os.path.join(BASE_DIR, 'input.json')))


@pytest.fixture(scope='session')
def serialized_example_1_roles_specification(example_1_roles_specification):
    obj = AWSIAMRolesSpecificationSerializer().load(data=example_1_roles_specification)
    obj.set_parameters(
        Accounts={
            'AppsAccount': {
                "Id": '012345678901',
                "AccessRoleName": "DefaultAccessRole"
            },
            'PipelineAccount': {
                "Id": '045678901234',
                "AccessRoleName": "DefaultAccessRole"
            },
            'WorkloadUserAccount': {
                "Id": '078901234567',
                "AccessRoleName": "DefaultAccessRole"
            }
        },
        Regions={}
    )
    return obj


@pytest.fixture(scope='session')
def templates(serialized_example_1_roles_specification):
    serialized_example_1_roles_specification.Reference = ""
    return serialized_example_1_roles_specification.generate_cloudformation_templates()


@pytest.fixture(scope='session')
def apps_account_cf_template(templates):
    for template in templates:
        if template['Name'] == 'AppsAccount-':
            return template


@pytest.fixture(scope='session')
def pipeline_account_cf_template(templates):
    for template in templates:
        if template['Name'] == 'PipelineAccount-':
            return template


@pytest.fixture(scope='session')
def workload_user_account_cf_template(templates):
    for template in templates:
        if template['Name'] == 'WorkloadUserAccount-':
            return template


@pytest.fixture(scope='session')
def example_1_apps_account_expected_template():
    BASE_DIR = os.path.dirname(os.path.realpath(__file__))
    return json.load(open(os.path.join(BASE_DIR, 'AppsAccount.json')))


@pytest.fixture(scope='session')
def example_1_pipeline_account_expected_template():
    BASE_DIR = os.path.dirname(os.path.realpath(__file__))
    return json.load(open(os.path.join(BASE_DIR, 'PipelineAccount.json')))


@pytest.fixture(scope='session')
def example_1_workload_user_account_expected_template():
    BASE_DIR = os.path.dirname(os.path.realpath(__file__))
    return json.load(open(os.path.join(BASE_DIR, 'WorkloadUserAccount.json')))
