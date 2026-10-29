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

"""
Environment enumeration for CodeMie test harness.

This enum defines all supported environments for the CodeMie platform,
providing type safety and preventing typos in environment checks.
"""

from enum import Enum
from typing import List


class Environment(Enum):
    """
    Enumeration of supported CodeMie environments.

    Each environment corresponds to a specific deployment of the CodeMie platform
    with its own domain patterns and configuration requirements.
    """

    PRODUCTION = "prod"
    PREVIEW = "preview"
    OSS_PREVIEW = "oss_preview"
    LOCALHOST = "localhost"
    AZURE = "azure"
    GCP = "gcp"
    AWS = "aws"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        """Return the string value of the environment."""
        return self.value

    @property
    def is_production(self) -> bool:
        """Check if this is the production environment."""
        return self == Environment.PRODUCTION

    @property
    def is_preview(self) -> bool:
        """Check if this is any preview environment (preview or OSS preview)."""
        return self in (Environment.PREVIEW, Environment.OSS_PREVIEW)

    @property
    def is_localhost(self) -> bool:
        """Check if this is the localhost environment."""
        return self == Environment.LOCALHOST

    @property
    def is_sandbox(self) -> bool:
        """Check if this is any sandbox environment (azure, gcp, aws)."""
        return self in (Environment.AZURE, Environment.GCP, Environment.AWS)

    @property
    def is_azure(self) -> bool:
        """Check if this is the Azure sandbox environment."""
        return self == Environment.AZURE

    @property
    def is_gcp(self) -> bool:
        """Check if this is the GCP sandbox environment."""
        return self == Environment.GCP

    @property
    def is_aws(self) -> bool:
        """Check if this is the AWS sandbox environment."""
        return self == Environment.AWS

    @classmethod
    def get_all_sandbox_environments(cls) -> List["Environment"]:
        """Get all sandbox environments as enum values."""
        return [cls.AZURE, cls.GCP, cls.AWS]

    @classmethod
    def get_all_environments(cls) -> List["Environment"]:
        """Get all available environments."""
        return list(cls)

    @classmethod
    def get_azure_environments(cls) -> List["Environment"]:
        """Get environments where Azure services are available.

        Returns:
            List of Environment enums: [PREVIEW, OSS_PREVIEW, AZURE, LOCALHOST, PRODUCTION]
        """
        return [cls.PREVIEW, cls.OSS_PREVIEW, cls.AZURE, cls.LOCALHOST, cls.PRODUCTION]

    @classmethod
    def get_gcp_environments(cls) -> List["Environment"]:
        """Get environments where GCP services are available.

        Returns:
            List of Environment enums: [PREVIEW, OSS_PREVIEW, GCP, LOCALHOST, PRODUCTION]
        """
        return [cls.PREVIEW, cls.OSS_PREVIEW, cls.GCP, cls.LOCALHOST, cls.PRODUCTION]

    @classmethod
    def get_aws_environments(cls) -> List["Environment"]:
        """Get environments where AWS services are available.

        Returns:
            List of Environment enums: [PREVIEW, OSS_PREVIEW, AWS, LOCALHOST, PRODUCTION]
        """
        return [cls.PREVIEW, cls.OSS_PREVIEW, cls.AWS, cls.LOCALHOST, cls.PRODUCTION]
