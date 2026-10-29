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

"""Seed data for cloud tool tests: one known, already existing AWS S3 bucket, Azure resource group, GCP bucket and Kubernetes service.

Pure logic only (no HTTP); AwsUtils, AzureUtils, GcpUtils and KubernetesUtils
perform the requests. The cloud tests used to assert on full listings of
shared live resources -- every S3 bucket of the AWS account, one long-lived
GCP bucket's generation/etag/timestamps, the whole ``argocd`` namespace with
its resourceVersions and UIDs, and a pinned Azure resource group's tags and
provisioning state -- so they broke whenever somebody else touched the
account, cluster or subscription. Nothing is created: the tests are narrowed
to one existing resource per cloud, and its attributes are read from the live
resource at session start instead of being hardcoded.
"""

import json
from dataclasses import asdict, dataclass
from typing import Optional

# Long-lived resources present in every listing the tests used to hardcode.
# Each can be overridden with the parameter of the same name.
AWS_SEED_BUCKET_NAME = "codemie-bucket"
GCP_SEED_BUCKET_NAME = "009fb622-4e29-42aa-bafd-584c61f5e1e1"
KUBERNETES_SEED_NAMESPACE = "argocd"
KUBERNETES_SEED_SERVICE = "argo-cd-argocd-server"
# Like the bucket/namespace/service names above, this is a plain constant: it
# identifies a long-lived resource in the shared sandbox, not a secret. The
# subscription it lives under *is* account-specific config, already exposed
# as "AZURE_SUBSCRIPTION_ID" for building Azure credentials, so AzureUtils
# reads that from config instead of a second constant duplicated here.
AZURE_SEED_RESOURCE_GROUP_NAME = "krci-codemie-azure-env-rg"

AWS_SEED = "aws_seed_bucket"
AZURE_SEED = "azure_seed_resource_group"
GCP_SEED = "gcp_seed_bucket"
KUBERNETES_SEED = "kubernetes_seed_service"


@dataclass(frozen=True)
class SeedAwsBucket:
    name: str
    creation_date: str
    # ``None`` for us-east-1, exactly as S3 GetBucketLocation reports it.
    location_constraint: Optional[str]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SeedAwsBucket":
        return cls(**data)


@dataclass(frozen=True)
class SeedAzureResourceGroup:
    subscription_id: str
    name: str
    type: str
    location: str
    tags: dict
    provisioning_state: str

    @property
    def resource_id(self) -> str:
        return f"/subscriptions/{self.subscription_id}/resourceGroups/{self.name}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SeedAzureResourceGroup":
        return cls(**data)


@dataclass(frozen=True)
class SeedGcpBucket:
    name: str
    project_number: str
    generation: str
    metageneration: str
    location: str
    location_type: str
    storage_class: str
    etag: str
    time_created: str
    updated: str
    rpo: str
    soft_delete_retention_seconds: str
    soft_delete_effective_time: str
    bucket_policy_only: bool
    uniform_bucket_level_access: bool
    public_access_prevention: str

    @property
    def self_link(self) -> str:
        return f"https://www.googleapis.com/storage/v1/b/{self.name}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SeedGcpBucket":
        return cls(**data)


@dataclass(frozen=True)
class SeedKubernetesService:
    namespace: str
    name: str
    service_type: str
    cluster_ip: str
    ports: list
    # The ``Service`` object as the API returned it; the direct tool returns it as-is.
    raw: dict

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SeedKubernetesService":
        return cls(**data)


def aws_bucket_from_api(
    bucket: dict, location_constraint: Optional[str]
) -> SeedAwsBucket:
    """Build the seed from a ListBuckets entry and the bucket's GetBucketLocation result."""
    return SeedAwsBucket(
        name=bucket["Name"],
        creation_date=bucket["CreationDate"].isoformat(),
        location_constraint=location_constraint,
    )


def azure_resource_group_from_api(
    resource_group: dict, subscription_id: str
) -> SeedAzureResourceGroup:
    """Build the seed from an ARM ``resourceGroups`` GET response.

    ``subscription_id`` is passed in rather than parsed out of the response's
    ``id`` field, mirroring how ``aws_bucket_from_api`` takes its
    ``location_constraint`` as a separate argument: AzureUtils already knows
    it from config (it used it to build the request URL).
    """
    properties = resource_group.get("properties", {})
    return SeedAzureResourceGroup(
        subscription_id=subscription_id,
        name=resource_group["name"],
        type=resource_group.get("type", "Microsoft.Resources/resourceGroups"),
        location=resource_group["location"],
        tags=resource_group.get("tags") or {},
        provisioning_state=properties.get("provisioningState", ""),
    )


def gcp_bucket_from_api(bucket: dict) -> SeedGcpBucket:
    """Build the seed from a Cloud Storage ``buckets`` resource, as the live API reports it."""
    soft_delete = bucket.get("softDeletePolicy", {})
    iam = bucket.get("iamConfiguration", {})
    return SeedGcpBucket(
        name=bucket["name"],
        project_number=str(bucket["projectNumber"]),
        generation=str(bucket["generation"]),
        metageneration=str(bucket["metageneration"]),
        location=bucket["location"],
        location_type=bucket.get("locationType", ""),
        storage_class=bucket["storageClass"],
        etag=bucket["etag"],
        time_created=bucket["timeCreated"],
        updated=bucket["updated"],
        rpo=bucket.get("rpo", ""),
        soft_delete_retention_seconds=str(
            soft_delete.get("retentionDurationSeconds", "")
        ),
        soft_delete_effective_time=soft_delete.get("effectiveTime", ""),
        bucket_policy_only=iam.get("bucketPolicyOnly", {}).get("enabled", False),
        uniform_bucket_level_access=iam.get("uniformBucketLevelAccess", {}).get(
            "enabled", False
        ),
        public_access_prevention=iam.get("publicAccessPrevention", ""),
    )


def kubernetes_service_from_api(service: dict) -> SeedKubernetesService:
    """Build the seed from a live ``Service`` object."""
    metadata = service["metadata"]
    spec = service["spec"]
    return SeedKubernetesService(
        namespace=metadata["namespace"],
        name=metadata["name"],
        service_type=spec.get("type", "ClusterIP"),
        cluster_ip=spec.get("clusterIP", ""),
        ports=spec.get("ports", []),
        raw=service,
    )


def render_aws_bucket_location_json(seed: SeedAwsBucket) -> str:
    """Expected raw tool output for ``s3.get_bucket_location`` on the seed bucket."""
    return json.dumps(
        {
            "ResponseMetadata": {"HTTPStatusCode": 200, "RetryAttempts": 0},
            "LocationConstraint": seed.location_constraint,
        },
        indent=4,
    )


def render_azure_resource_group_tags(seed: SeedAzureResourceGroup) -> str:
    """Tag lines for the "list resource group info" prompt's expected answer."""
    if not seed.tags:
        return " - (none)"
    return "\n".join(f" - {key}: {value}" for key, value in seed.tags.items())


def render_azure_resource_group_json(seed: SeedAzureResourceGroup) -> str:
    """Expected raw tool output for ``GET /subscriptions/<sub>/resourceGroups/<name>``."""
    return json.dumps(
        {
            "id": seed.resource_id,
            "name": seed.name,
            "type": seed.type,
            "location": seed.location,
            "tags": seed.tags,
            "properties": {"provisioningState": seed.provisioning_state},
        },
        indent=2,
    )


def render_kubernetes_service_ports(seed: SeedKubernetesService) -> str:
    return ", ".join(
        f"{port.get('name', '')} {port['port']}/{port.get('protocol', 'TCP')}".strip()
        for port in seed.ports
    )


def render_kubernetes_service_json(seed: SeedKubernetesService) -> str:
    """Expected raw tool output for ``GET /api/v1/namespaces/<ns>/services/<name>``."""
    return json.dumps(seed.raw, indent=2)
