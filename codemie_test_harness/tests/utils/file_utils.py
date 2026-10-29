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


def save_file(response, target_file_path):
    """
    Saves the file from the API response to the specified path.

    Args:
        response: The response object containing the file data.
        target_file_path: The path where the file will be saved.

    Returns:
        file: The saved file.
    """
    try:
        # Open the target file in write-binary mode
        with open(target_file_path, "wb") as target_file:
            target_file.write(response)
    except Exception as e:
        raise RuntimeError("Failed to write the file!") from e

    return target_file_path
