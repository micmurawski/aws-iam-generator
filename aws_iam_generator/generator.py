import json
from datetime import datetime
from uuid import uuid4

import boto3

from .serializers import AWSIAMRolesSpecificationSerializer


class AWSIAMGeneratorException(Exception):
    pass


class AWSIAMGenerator:

    def __init__(self, session=None, role_session_name=None, reference_name=None, unique_id=False):
        self.spec = None
        self.output = None
        self.unique_id = unique_id
        self.reference_name = uuid4().hex if reference_name is None else reference_name
        self.role_session_name = f'aws-iam-generator-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}' \
            if role_session_name is None else role_session_name
        self.session = session if session else boto3.Session()

    def load_spec(self, spec):
        self.spec = AWSIAMRolesSpecificationSerializer().load(data=spec)
        self.spec.UniqueID = self.unique_id
        self.spec.Reference = self.reference_name

    def set_parameters(self, **kwargs):
        self.output = self.spec.set_parameters(**kwargs)

    def deploy(self):

        if self.output is None:
            raise AWSIAMGeneratorException('Specification wasn\'t loaded yet. Please execute load_spec method before.')

        result = {}
        for obj in self.output:
            sts_client = self.session.client('sts')
            sts_response = sts_client.assume_role(
                RoleArn=obj['AccessRoleArn'],
                RoleSessionName=self.role_session_name
            )
            cf_client = self.session.client(
                'cloudformation',
                aws_access_key_id=sts_response["Credentials"]["AccessKeyId"],
                aws_secret_access_key=sts_response["Credentials"]["SecretAccessKey"],
                aws_session_token=sts_response["Credentials"]["SessionToken"],
                region_name=obj['RegionName']
            )

            cf_request_body = {
                "StackName": obj['Name'],
                "Parameters": (),
                "DisableRollback": True,
                "OnFailure": 'DO_NOTHING',
                "TimeoutInMinutes": 2,
                "Capabilities": [
                    'CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM', 'CAPABILITY_AUTO_EXPAND',
                ]
            }

            if obj['S3BucketKey']:
                bucket, key = obj['S3BucketKey'].replace('s3://', '').split('/', 1)
                s3_client = self.session.client('s3')
                s3_client.put_object(
                    Bucket=bucket,
                    Key=f'{key}/{obj["Name"]}.json',
                    Body=json.dumps(obj['Body'])
                )
                cf_request_body['TemplateURL'] = f'https://{bucket}.s3.amazonaws.com/{key}'
            else:
                cf_request_body['TemplateBody'] = json.dumps(obj['Body'])

            cf_response = cf_client.create_stack(
                **cf_request_body
            )
            result[obj['Name']] = cf_response

            return result
