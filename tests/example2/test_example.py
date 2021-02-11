import json
import os


def test_valid_workload_user_account_cf_template(workload_user_account_cf_template):
    BASE_DIR = os.path.dirname(os.path.realpath(__file__))
    expected = json.load(open(os.path.join(BASE_DIR, 'WorkloadUserAccount.json')))
    assert workload_user_account_cf_template['Body'] == expected


def test_valid_apps_account_slr_cf_template(apps_account_slr_cf_template):
    BASE_DIR = os.path.dirname(os.path.realpath(__file__))
    expected = json.load(open(os.path.join(BASE_DIR, 'AppsAccount-Service-Linked-Roles.json')))
    assert apps_account_slr_cf_template['Body'] == expected
