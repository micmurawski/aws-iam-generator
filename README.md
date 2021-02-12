# AWS IAM Generator
#### Cross-account IAM resources made easier
## Introduction
During my work as a cloud engineer, I often needed to deploy some IAM resources tangled
together with some parameters. I had to do it so often I decided to wrap it all in a feasible and easy to use the library.

Generates AWS IAM Managed Policies and Roles for multiple accounts using the easy templating language. Example cross-account template and deployment execution shown below.
## Installation
 1. Run ``pip install pynamodb-utils`` or execute ``python setup.py install`` in the source directory
 2. Add ``aws_iam_generator`` to your ``INSTALLED_APPS``

## Example
```python
from iam_aws_generator import AWSIAMGenerator


example_roles_specification = {
    'Regions': {
        'PipelineRegion': {},
        'AppsRegion': {}
    },
    'Accounts': {
        'PipelineAccount': {
            'Description': 'Account where deployment pipeline will be created',
            'AccessRoleName': 'DefaultAccessRole'
        },
        'AppsAccount': {
            'Description': 'Account where apps will be deployed',
            'AccessRoleName': 'DefaultAccessRole'
        },
        'MaintenanceAccount': {
            'Id': '123456789002',
            'Description': 'Remote account owned by Workload Provider that will be performing maintenance tasks'
        }
    },
    'Variables': {
        'HostedZoneID': {
            'Type': 'string',
            'Description': 'Hosted Zone ID of workload domain'
        },
        'TrustRolesArns': {
            'Type': 'list(string)',
            'Description': 'Operations Account of Workload Provider and customer.'
        }
    },
    'Policies': {
        'Route53Policy': {
            'Description': 'Policy that enables a user to perform actions on Route53',
            'PolicyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Action': ['route53:*'],
                        'Resource': [
                            'arn:aws:route53:::hostedzone/{{Variables.HostedZoneID.Value}}',
                            'arn:aws:route53:::healthcheck/{{Variables.HostedZoneID.Value}}'
                        ],
                        'Effect': 'Allow'
                    }
                ]
            }
        },
        'DeployPipelinePolicy': {
            'Description': 'Policy that enables to deploy pipeline',
            'PolicyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Action': [
                            'cloudformation:CreateStack',
                            'cloudformation:DescribeStackEvents',
                            'cloudformation:DescribeStacks',
                            'cloudformation:UpdateStack'
                        ],
                        'Effect': 'Allow',
                        'Resource': [
                            'arn:aws:cloudformation:{{Regions.PipelineRegion.Id}}:{{Accounts.PipelineAccount.Id}}:stack/deployment-pipeline/*'
                        ]
                    },
                    {
                        'Action': [
                            's3:CreateBucket',
                            's3:GetObject',
                            's3:ListBucket',
                            's3:PutObject'
                        ],
                        'Effect': 'Allow',
                        'Resource': 'arn:aws:s3:::{{Regions.PipelineRegion.Id}}-pipeline-bucket'
                    }
                ]
            }
        },
        'DeployAppPolicy': {
            'Description': 'Policy that enables to deploy pipeline',
            'PolicyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Action': [
                            's3:CreateBucket',
                            's3:GetObject',
                            's3:ListBucket',
                            's3:PutObject'
                        ],
                        'Effect': 'Allow',
                        'Resource': 'arn:aws:s3:::{{Accounts.AppsAccount.Id}}-{{Regions.AppsRegion.Id}}-app-bucket'
                    }
                ]
            }
        }
    },
    'Roles': {
        'DNSRole': {
            'Trusts': [
                'Variables.TrustRolesArns.Value',
                'Accounts.MaintenanceAccount.Id',
                'Roles.DeployAppRole.Arn'
            ],
            'ManagedPolicies': ['Policies.Route53Policy'],
            'InAccounts': ['Accounts.AppsAccount.Id']
        },
        'DeployPipelineRole': {
            'Trusts': ['Accounts.MaintenanceAccount.Id'],
            'ManagedPolicies': ['Policies.DeployPipelinePolicy'],
            'InAccounts': ['Accounts.PipelineAccount.Id']},
        'DeployAppRole': {
            'Trusts': ['Accounts.PipelineAccount.Id'],
            'ManagedPolicies': ['Policies.DeployAppPolicy'],
            'InAccounts': ['Accounts.AppsAccount.Id']
        },
        'APIGatewayCloudWatchLogRole': {
            'Trusts': ['apigateway.amazonaws.com'],
            'ManagedPolicies': ['arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs'],
            'InAccounts': ['Accounts.AppsAccount.Id']
        }
    },
    'ServiceLinkedRoles': {
        'AWSServiceRoleForECS': {
            'ServiceName': 'ecs.amazonaws.com',
            'InAccounts': [
                'Accounts.PipelineAccount.Id',
                'Accounts.AppsAccount.Id'
            ]
        }
    }
}

generator = AWSIAMGenerator(reference_name='test')
generator.load_spec(spec=example_roles_specification)
generator.set_parameters(
    Accounts={
        'AppsAccount': {
            "Id": '112345678901'
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
generator.deploy()

```
## Links

* https://pypi.org/project/aws-iam-generator/