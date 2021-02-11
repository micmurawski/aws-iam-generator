import json
import os


def test_valid_shared_services_account_cf_template(shared_services_account_cf_template):
    BASE_DIR = os.path.dirname(os.path.realpath(__file__))
    expected = json.load(open(os.path.join(BASE_DIR, 'SharedServicesAccount.json')))
    assert shared_services_account_cf_template['Body'] == expected
