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
Environment resolver utility that determines environment from CODEMIE_API_DOMAIN.

This module provides a robust way to resolve the environment based on the
API domain, eliminating the need for hardcoded ENV variables and preventing
configuration drift between domain and environment settings.
"""

import re
from urllib.parse import urlparse

from codemie_test_harness.tests.enums.environment import Environment


class EnvironmentResolver:
    """
    Resolves environment configuration based on CODEMIE_API_DOMAIN.

    Supported environments and their domain patterns:
    - prod: Production domains
    - preview: Preview domains
    - oss_preview: OSS Preview domains
    - localhost: Local development
    - azure: Azure sandbox environments
    - gcp: GCP sandbox environments
    - aws: AWS sandbox environments
    - unknown: Any unrecognized domain
    """

    # Regex patterns (re.search, ignore case) applied to the hostname of the API domain.
    # Order matters - more specific first.
    HOST_PATTERNS = (
        (r"codemie\.lab\.", Environment.PRODUCTION),
        (r"codemie-preview\.lab\.", Environment.PREVIEW),
        (r"codemie-preview-oss\.lab\.", Environment.OSS_PREVIEW),
        (r"codemie-azure\.eks-sandbox\.", Environment.AZURE),
        (r"codemie-gcp\.eks-sandbox\.", Environment.GCP),
        (r"codemie-aws\.eks-sandbox\.", Environment.AWS),
    )

    # Local development patterns
    LOCAL_PATTERNS = (
        r"^https?://localhost(:\d+)?(/.*)?$",
        r"^https?://127\.0\.0\.1(:\d+)?(/.*)?$",
        r"^https?://192\.168\.\d{1,3}\.\d{1,3}(:\d+)?(/.*)?$",
    )

    @classmethod
    def get_environment(cls) -> Environment:
        """
        Get the current environment based on CODEMIE_API_DOMAIN.

        This is the main method that should be used throughout the codebase
        to replace os.getenv("ENV") calls.

        Returns:
            Environment: The resolved environment enum value

        Raises:
            ValueError: If CODEMIE_API_DOMAIN is not set
        """
        # Imported here: credentials_manager imports this module.
        from codemie_test_harness.tests.utils.credentials_manager import (
            CredentialsManager,
        )

        codemie_api_domain = CredentialsManager.get_parameter("CODEMIE_API_DOMAIN")

        if not codemie_api_domain:
            raise ValueError("CODEMIE_API_DOMAIN environment variable is not set")

        # Clean up the domain (remove trailing slashes)
        domain = codemie_api_domain.rstrip("/")

        for pattern in cls.LOCAL_PATTERNS:
            if re.match(pattern, domain, re.IGNORECASE):
                return Environment.LOCALHOST

        # Host patterns match the hostname only (no scheme, port or path).
        hostname = urlparse(domain).hostname or domain
        for pattern, environment in cls.HOST_PATTERNS:
            if re.search(pattern, hostname, re.IGNORECASE):
                return environment

        # If no match found, return 'unknown'
        return Environment.UNKNOWN

    @classmethod
    def is_production(cls) -> bool:
        """Check if current environment is production."""
        return cls.get_environment().is_production

    @classmethod
    def is_preview(cls) -> bool:
        """Check if current environment is preview."""
        return cls.get_environment().is_preview

    @classmethod
    def is_localhost(cls) -> bool:
        """Check if current environment is localhost."""
        return cls.get_environment().is_localhost

    @classmethod
    def is_sandbox(cls) -> bool:
        """Check if current environment is any sandbox environment."""
        return cls.get_environment().is_sandbox

    @classmethod
    def is_azure(cls) -> bool:
        """Check if current environment is Azure."""
        return cls.get_environment().is_azure

    @classmethod
    def is_gcp(cls) -> bool:
        """Check if current environment is GCP."""
        return cls.get_environment().is_gcp

    @classmethod
    def is_aws(cls) -> bool:
        """Check if current environment is AWS."""
        return cls.get_environment().is_aws


def get_environment() -> Environment:
    """
    Convenience function to get the current environment.

    This is the primary function that should replace os.getenv("ENV") throughout the codebase.

    Returns:
        Environment: The resolved environment enum value
    """
    return EnvironmentResolver.get_environment()
