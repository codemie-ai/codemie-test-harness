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

"""Utility class for category operations."""

from codemie_sdk.models.categories import (
    CategoryCreateRequest,
    CategoryUpdateRequest,
)
from codemie_test_harness.tests.utils.base_utils import BaseUtils, get_random_name


class CategoriesUtils(BaseUtils):
    """Utility class for managing assistant categories."""

    def get_categories(self):
        """Get all available assistant categories (legacy, non-paginated).

        Returns:
            List of all categories
        """
        return self.client.categories.get_categories()

    def list_categories(self, page: int = 0, per_page: int = 10):
        """Get paginated list of categories with assistant counts.

        Args:
            page: Page number (0-indexed, default: 0)
            per_page: Number of items per page (1-100, default: 10)

        Returns:
            CategoryListResponse with categories and metadata
        """
        return self.client.categories.list_categories(page=page, per_page=per_page)

    def get_category(self, category_id: str):
        """Get a specific category by ID with assistant counts.

        Args:
            category_id: Category ID (humanized, e.g., "migration_modernization")

        Returns:
            CategoryResponse with category details and assistant counts
        """
        return self.client.categories.get_category(category_id)

    def create_category(self, name: str = None, description: str = None):
        """Create a new category. Admin access required.

        The category ID will be auto-generated from the name.

        Args:
            name: Category name (if not provided, generates random name)
            description: Category description (optional)

        Returns:
            CategoryResponse with created category details
        """
        category_name = name if name else get_random_name()
        category_description = (
            description if description else "Integration test category"
        )

        request = CategoryCreateRequest(
            name=category_name,
            description=category_description,
        )

        return self.client.categories.create_category(request)

    def update_category(
        self, category_id: str, name: str = None, description: str = None
    ):
        """Update an existing category. Admin access required.

        Args:
            category_id: Category ID to update
            name: New category name (optional)
            description: New category description (optional)

        Returns:
            CategoryResponse with updated category details
        """
        # Get current category details if name/description not provided
        if name is None or description is None:
            current_category = self.get_category(category_id)
            name = name if name else current_category.name
            description = description if description else current_category.description

        request = CategoryUpdateRequest(
            name=name,
            description=description,
        )

        return self.client.categories.update_category(category_id, request)

    def delete_category(self, category_id: str):
        """Delete a category. Admin access required.

        This operation will fail if any assistants are assigned to this category.

        Args:
            category_id: Category ID to delete

        Returns:
            Empty dict on successful deletion
        """
        return self.client.categories.delete_category(category_id)

    def send_create_category_request(self, request: CategoryCreateRequest):
        """Send a category creation request.

        Args:
            request: CategoryCreateRequest with category details

        Returns:
            CategoryResponse with created category details
        """
        return self.client.categories.create_category(request)

    def send_update_category_request(
        self, category_id: str, request: CategoryUpdateRequest
    ):
        """Send a category update request.

        Args:
            category_id: Category ID to update
            request: CategoryUpdateRequest with updated details

        Returns:
            CategoryResponse with updated category details
        """
        return self.client.categories.update_category(category_id, request)
