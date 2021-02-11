from moto import mock_cloudformation, mock_iam, mock_sts

from aws_iam_generator import AWSIAMGenerator


@mock_iam
@mock_cloudformation
@mock_sts
def test_serializer_roles_spec(example_roles_specification):
    generator = AWSIAMGenerator(reference_name='test')
    generator.load_spec(spec=example_roles_specification)
    generator.set_parameters(
        Accounts={
            'AppsAccount': {
                "Id": '112345678901',
                "AccessRoleName": "DefaultName"
            },
            'PipelineAccount': {
                "Id": '212345678901'
            }
        },
        Regions={
            'PipelineRegion': {
                "Id": "us-east-1"
            },
            'AppsRegion': {
                "Id": "us-east-1"
            }
        },
        Variables={
            "HostedZoneID": {
                "Value": "*"
            },
            "TrustRolesArns": {
                "Value": ["arn:aws:iam::123456789011:role/ExternalAccessRole"]
            }
        }
    )
