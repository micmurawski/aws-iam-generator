import json

import pytest


@pytest.fixture(scope='session')
def example_roles_specification():
    return json.load(open('./aws_iam_generator/input.json'))
