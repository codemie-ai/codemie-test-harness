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
    render_aws_bucket_location_json,
    render_azure_resource_group_json,
    render_kubernetes_service_json,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.jira_seed import Seeded

cloud_test_data = [
    pytest.param(
        Toolkit.CLOUD,
        CloudTool.AWS,
        CredentialTypes.AWS,
        CredentialsManager.aws_credentials(),
        # Query the seed bucket directly; the account's other buckets are irrelevant.
        Seeded(
            AWS_SEED,
            lambda seed: {
                "query": {
                    "service": "s3",
                    "method_name": "get_bucket_location",
                    "method_arguments": {"Bucket": seed.name},
                }
            },
        ),
        Seeded(AWS_SEED, render_aws_bucket_location_json),
        marks=pytest.mark.aws,
        id=CredentialTypes.AWS,
    ),
    pytest.param(
        Toolkit.CLOUD,
        CloudTool.AZURE,
        CredentialTypes.AZURE,
        CredentialsManager.azure_credentials(),
        Seeded(
            AZURE_SEED,
            lambda seed: {
                "method": "GET",
                "url": (
                    f"https://management.azure.com/subscriptions/{seed.subscription_id}"
                    f"/resourceGroups/{seed.name}?api-version=2021-04-01"
                ),
            },
        ),
        Seeded(AZURE_SEED, render_azure_resource_group_json),
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
            lambda seed: {
                "method": "GET",
                "scopes": ["https://www.googleapis.com/auth/cloud-platform"],
                "url": seed.self_link,
            },
        ),
        Seeded(
            GCP_SEED,
            lambda seed: f"""
            {{
               "kind":"storage#bucket",
               "selfLink":"{seed.self_link}",
               "id":"{seed.name}",
               "name":"{seed.name}",
               "projectNumber":"{seed.project_number}",
               "generation":"{seed.generation}",
               "metageneration":"{seed.metageneration}",
               "location":"{seed.location}",
               "storageClass":"{seed.storage_class}",
               "etag":"{seed.etag}",
               "timeCreated":"{seed.time_created}",
               "updated":"{seed.updated}",
               "softDeletePolicy":{{
                  "retentionDurationSeconds":"{seed.soft_delete_retention_seconds}",
                  "effectiveTime":"{seed.soft_delete_effective_time}"
               }},
               "iamConfiguration":{{
                  "bucketPolicyOnly":{{
                     "enabled":{str(seed.bucket_policy_only).lower()}
                  }},
                  "uniformBucketLevelAccess":{{
                     "enabled":{str(seed.uniform_bucket_level_access).lower()}
                  }},
                  "publicAccessPrevention":"{seed.public_access_prevention}"
               }},
               "locationType":"{seed.location_type}",
               "rpo":"{seed.rpo}"
            }}
        """,
        ),
        marks=[
            pytest.mark.gcp,
            pytest.mark.skipif(
                EnvironmentResolver.is_azure(),
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
        # Get the seed service directly instead of listing the whole namespace.
        Seeded(
            KUBERNETES_SEED,
            lambda seed: {
                "method": "GET",
                "suburl": f"/api/v1/namespaces/{seed.namespace}/services/{seed.name}",
            },
        ),
        Seeded(KUBERNETES_SEED, render_kubernetes_service_json),
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
