import json
import time
from datetime import datetime
from uuid import uuid4

import boto3

from .serializers import AWSIAMRolesSpecificationSerializer

cf_stack_status_complete = (
    'CREATE_COMPLETE',
    'ROLLBACK_COMPLETE',
    'DELETE_COMPLETE',
    'UPDATE_COMPLETE',
    'UPDATE_ROLLBACK_COMPLETE',
    'IMPORT_COMPLETE',
    'IMPORT_ROLLBACK_COMPLETE'
)

cf_stack_in_progress = (
    'IMPORT_ROLLBACK_IN_PROGRESS',
    'CREATE_IN_PROGRESS',
    'ROLLBACK_IN_PROGRESS',
    'DELETE_IN_PROGRESS',
    'UPDATE_IN_PROGRESS',
    'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS',
    'UPDATE_ROLLBACK_IN_PROGRESS',
    'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS',
    'REVIEW_IN_PROGRESS',
    'IMPORT_IN_PROGRESS'
)


cf_stack_status_failed = (
    'ROLLBACK_FAILED',
    'DELETE_FAILED',
    'UPDATE_ROLLBACK_FAILED',
    'IMPORT_ROLLBACK_FAILED',
    'CREATE_FAILED'
)


class AWSIAMGeneratorException(Exception):
    pass


class AWSIAMGenerator:

    def __init__(self, session=None, role_session_name=None, reference_name=None):
        self.spec = None
        self.parameters = {}
        self.reference_name = uuid4().hex if reference_name is None else reference_name
        self.role_session_name = f'aws-iam-generator-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}' \
            if role_session_name is None else role_session_name
        self.session = session if session else boto3.Session()
        self._clients = {}

    def load_spec(self, spec):
        self.spec = AWSIAMRolesSpecificationSerializer().load(data=spec)
        self.spec.Reference = self.reference_name

    def set_parameters(self, **kwargs):
        self.parameters = kwargs

    def _get_client(self, role_arn, role_session_name, region_name):
        key = f'{role_arn}:{role_session_name}'
        if key in self._clients:
            return self._clients[key]
        else:
            sts_client = self.session.client('sts')
            sts_response = sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName=role_session_name
            )
            cf_client = self.session.client(
                'cloudformation',
                aws_access_key_id=sts_response["Credentials"]["AccessKeyId"],
                aws_secret_access_key=sts_response["Credentials"]["SecretAccessKey"],
                aws_session_token=sts_response["Credentials"]["SessionToken"],
                region_name=region_name
            )
            self._clients[key] = cf_client

            return self._clients[key]

    def deploy(self):

        if self.spec is None:
            raise AWSIAMGeneratorException('Specification wasn\'t loaded yet. Please execute load_spec method before.')

        if self.parameters is None:
            raise AWSIAMGeneratorException('Parameters wasn\'t set yet. Please execute set_parameters method before.')

        result = {}

        output_1 = self.spec.set_parameters(with_trusts=False, **self.parameters)
        for obj in output_1:
            cf_client = self._get_client(
                role_arn=obj['AccessRoleArn'],
                role_session_name=self.role_session_name,
                region_name=obj['RegionName']
            )

            create_stack_request_body = {
                "StackName": obj['Name'],
                "Parameters": (),
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
                create_stack_request_body['TemplateURL'] = f'https://{bucket}.s3.amazonaws.com/{key}'
            else:
                create_stack_request_body['TemplateBody'] = json.dumps(obj['Body'])

            cf_response = cf_client.create_stack(
                **create_stack_request_body
            )
            result[obj['Name']] = cf_response

        running = [True] * len(output_1)

        while all(running):
            time.sleep(5)

            for i in range(len(output_1)):
                cf_client = self._get_client(
                    role_arn=output_1[i]['AccessRoleArn'],
                    role_session_name=self.role_session_name,
                    region_name=output_1[i]['RegionName']
                )
                response = cf_client.describe_stacks(StackName=output_1[i]['Name'])
                if response['Stacks'][0]['StackStatus'] in cf_stack_in_progress:
                    running[i] = True
                else:
                    running[i] = False

        output_2 = self.spec.generate_cloudformation_templates(with_trusts=True)

        update_stack_request_body = {
            "Parameters": (),
            "Capabilities": [
                'CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM', 'CAPABILITY_AUTO_EXPAND',
            ]
        }

        for obj in output_2:
            cf_client = self._get_client(
                role_arn=obj['AccessRoleArn'],
                role_session_name=self.role_session_name,
                region_name=obj['RegionName']
            )

            if obj['S3BucketKey']:
                bucket, key = obj['S3BucketKey'].replace('s3://', '').split('/', 1)
                s3_client = self.session.client('s3')
                s3_client.put_object(
                    Bucket=bucket,
                    Key=f'{key}/{obj["Name"]}.json',
                    Body=json.dumps(obj['Body'])
                )
                update_stack_request_body['TemplateURL'] = f'https://{bucket}.s3.amazonaws.com/{key}'
            else:
                update_stack_request_body['TemplateBody'] = json.dumps(obj['Body'])

            update_stack_request_body["StackName"] = obj['Name']
            cf_response = cf_client.update_stack(
                **update_stack_request_body
            )
            result[obj['Name']] = cf_response

        return result
