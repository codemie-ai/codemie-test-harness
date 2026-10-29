# Copyright 2026 EPAM Systems, Inc. (“EPAM”)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest

from codemie_test_harness.tests.enums.tools import Toolkit, CloudTool
from codemie_sdk.models.integration import CredentialTypes
from codemie_test_harness.tests.utils.cloud_seed import (
    AWS_SEED,
    AZURE_SEED,
    GCP_SEED,
    KUBERNETES_SEED,
    render_azure_resource_group_tags,
    render_kubernetes_service_ports,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.env_resolver import (
    EnvironmentResolver,
    get_environment,
)
from codemie_test_harness.tests.enums.environment import Environment
from codemie_test_harness.tests.utils.jira_seed import Seeded

cloud_test_data = [
    pytest.param(
        Toolkit.CLOUD,
        CloudTool.AWS,
        CredentialTypes.AWS,
        CredentialsManager.aws_credentials(),
        # The account is shared and its bucket list changes, so the tool is
        # asked for all buckets but the answer is narrowed to the seed bucket.
        Seeded(
            AWS_SEED,
            lambda seed: f"""
            Run list_buckets tool to print S3 buckets and show only the bucket with Name {seed.name}. Return its name and creation date only.
            Query example: {{'query': {{'service': 's3', 'method_name': 'list_buckets', 'method_arguments': {{}}}}}}
        """,
        ),
        Seeded(
            AWS_SEED,
            lambda seed: f"""
            Here is the S3 bucket:

            - **Name**: {seed.name}
            - **Creation Date**: {seed.creation_date}
        """,
        ),
        marks=pytest.mark.aws,
        id=CredentialTypes.AWS,
    ),
    pytest.param(
        Toolkit.CLOUD,
        CloudTool.AZURE,
        CredentialTypes.AZURE,
        CredentialsManager.azure_credentials(),
        # The subscription's resource groups can change, so the answer is
        # narrowed to the seed resource group and read from the live resource.
        Seeded(
            AZURE_SEED,
            lambda seed: f"""
            List info about {seed.name} resource group. Do not get information about resources in it
        """,
        ),
        Seeded(
            AZURE_SEED,
            lambda seed: f"""
            Here is the information about the resource group {seed.name}:

            ID: {seed.resource_id}
            Name: {seed.name}
            Type: {seed.type}
            Location: {seed.location}
            Tags:
            {render_azure_resource_group_tags(seed)}
            Provisioning State: {seed.provisioning_state}
        """,
        ),
        marks=pytest.mark.azure,
        id=CredentialTypes.AZURE,
    ),
    pytest.param(
        Toolkit.CLOUD,
        CloudTool.GCP,
        CredentialTypes.GCP,
        CredentialsManager.gcp_credentials(),
        Seeded(
            GCP_SEED,
            lambda seed: f"""
            Get information about bucket with Name {seed.name}

            Data is required: [
              "Kind",
              "Self Link",
              "ID",
              "Name",
              "Project Number",
              "Generation",
              "Metageneration",
              "Location",
              "Storage Class",
              "ETag",
              "Time Created",
              "Updated",
              "Location Type",
              "RPO",
              "Soft Delete Policy Retention Duration Seconds",
              "Soft Delete Policy Effective Time",
              "IAM Configuration Bucket Policy Only",
              "IAM Configuration Uniform Bucket Level Access",
              "IAM Configuration Public Access Prevention"
            ]
        """,
        ),
        Seeded(
            GCP_SEED,
            lambda seed: f"""
            Here is the information about the bucket with Name `{seed.name}`:

            - **Kind**: `storage#bucket`
            - **Self Link**: [Bucket Link]({seed.self_link})
            - **ID**: `{seed.name}`
            - **Name**: `{seed.name}`
            - **Project Number**: `{seed.project_number}`
            - **Generation**: `{seed.generation}`
            - **Metageneration**: `{seed.metageneration}`
            - **Location**: `{seed.location}`
            - **Storage Class**: `{seed.storage_class}`
            - **ETag**: `{seed.etag}`
            - **Time Created**: `{seed.time_created}`
            - **Updated**: `{seed.updated}`
            - **Location Type**: `{seed.location_type}`
            - **RPO**: `{seed.rpo}`

            **Soft Delete Policy**:
            - **Retention Duration Seconds**: `{seed.soft_delete_retention_seconds}`
            - **Effective Time**: `{seed.soft_delete_effective_time}`

            **IAM Configuration**:
            - **Bucket Policy Only**: `{seed.bucket_policy_only}`
            - **Uniform Bucket Level Access**: `{seed.uniform_bucket_level_access}`
            - **Public Access Prevention**: `{seed.public_access_prevention}`
        """,
        ),
        marks=[
            pytest.mark.gcp,
            pytest.mark.skipif(
                get_environment() in [Environment.AZURE, Environment.GCP],
                reason="Still have an issue with encoding long strings",
            ),
        ],
        id=CredentialTypes.GCP,
    ),
    pytest.param(
        Toolkit.CLOUD,
        CloudTool.KUBERNETES,
        CredentialTypes.KUBERNETES,
        CredentialsManager.kubernetes_credentials(),
        # The namespace's services change, so the answer is narrowed to the seed service.
        Seeded(
            KUBERNETES_SEED,
            lambda seed: f"""
            List services in the {seed.namespace} namespace and show only the service with name {seed.name}.
            Return its name, type, cluster IP and ports only, no need to return other data
        """,
        ),
        Seeded(
            KUBERNETES_SEED,
            lambda seed: f"""
            Here is the service `{seed.name}` in the `{seed.namespace}` namespace:

            - **Name**: {seed.name}
            - **Type**: {seed.service_type}
            - **Cluster IP**: {seed.cluster_ip}
            - **Ports**: {render_kubernetes_service_ports(seed)}
        """,
        ),
        marks=[
            pytest.mark.kubernetes,
            pytest.mark.skipif(
                EnvironmentResolver.is_azure(),
                reason="Still have an issue with encoding long strings",
            ),
        ],
        id=CredentialTypes.KUBERNETES,
    ),
]
