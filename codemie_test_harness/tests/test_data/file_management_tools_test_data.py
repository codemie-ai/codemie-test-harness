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

from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver

import pytest

from codemie_test_harness.tests.enums.tools import FileManagementTool
from codemie_test_harness.tests.utils.base_utils import get_random_name

CODE_INTERPRETER_TOOL_TASK = """
execute:

print("test_message" + "123")
"""

RESPONSE_FOR_CODE_INTERPRETER = """
    test_message123  
"""

# The listing tool needs an existing path, so the prompt creates a unique /tmp directory
# with a marker file first; this avoids shared container paths that drift with the image.
LIST_DIR_UNIQUE_DIR = get_random_name()
LIST_DIR_MARKER_FILE = f"{get_random_name()}.txt"

LIST_DIR_TOOL_TASK = (
    f"Execute command: mkdir -p /tmp/{LIST_DIR_UNIQUE_DIR} "
    f"&& touch /tmp/{LIST_DIR_UNIQUE_DIR}/{LIST_DIR_MARKER_FILE}. "
    f"Then list the files in the directory /tmp/{LIST_DIR_UNIQUE_DIR}"
)

RESPONSE_FOR_LIST_DIR = f"""
      Here are the files in the /tmp/{LIST_DIR_UNIQUE_DIR} directory:

    - `{LIST_DIR_MARKER_FILE}`

Let me know if you need further details or assistance with any specific directory or file.
"""

WRITE_FILE_TASK = (
    "Under /tmp directory create a new env.properties file with content env=preview"
)

RESPONSE_FOR_WRITE_FILE_TASK = """
   The file env.properties with the content env=preview has been successfully recreated in the /tmp directory.
   If you need any further assistance, feel free to let me know!
"""

COMMAND_LINE_UNIQUE_DIR = get_random_name()
COMMAND_LINE_MARKER_FILE = f"{get_random_name()}.txt"

COMMAND_LINE_TOOL_TASK = (
    f"Execute command: mkdir -p /tmp/{COMMAND_LINE_UNIQUE_DIR} "
    f"&& touch /tmp/{COMMAND_LINE_UNIQUE_DIR}/{COMMAND_LINE_MARKER_FILE} "
    f"&& ls /tmp/{COMMAND_LINE_UNIQUE_DIR}"
)

RESPONSE_FOR_COMMAND_LINE_TASK = f"""
    The `/tmp/{COMMAND_LINE_UNIQUE_DIR}` directory contains the following file:

    - `{COMMAND_LINE_MARKER_FILE}`

    If you need further details about any of these directories or any other assistance, feel free to let me know!
"""

READ_FILE_TOOL_TASK = "Show the content of /tmp/env.properties file"

RESPONSE_FOR_READ_FILE_TASK = """
    The content of the file `/tmp/env.properties` is:

    ```
    env=preview
    ```
"""

GENERATE_IMAGE_TOOL_TASK = """
    Generate an image with mountain view. Something similar to Alps. After image is generated send image url to user
"""

file_management_tools_test_data = [
    pytest.param(
        # The prompt chains a shell command to create the directory it then
        # lists (see LIST_DIR_TOOL_TASK), so both tools must be attached.
        (FileManagementTool.RUN_COMMAND_LINE, FileManagementTool.LIST_DIRECTORY),
        LIST_DIR_TOOL_TASK,
        RESPONSE_FOR_LIST_DIR,
        marks=pytest.mark.skipif(
            EnvironmentResolver.is_localhost(),
            reason="Skipping this test on local environment",
        ),
        id=FileManagementTool.LIST_DIRECTORY,
    ),
    pytest.param(
        FileManagementTool.WRITE_FILE,
        WRITE_FILE_TASK,
        RESPONSE_FOR_WRITE_FILE_TASK,
        id=FileManagementTool.WRITE_FILE,
    ),
    pytest.param(
        FileManagementTool.RUN_COMMAND_LINE,
        COMMAND_LINE_TOOL_TASK,
        RESPONSE_FOR_COMMAND_LINE_TASK,
        id=FileManagementTool.RUN_COMMAND_LINE,
    ),
]

code_tools_test_data = [
    pytest.param(
        FileManagementTool.CODE_EXECUTOR,
        """
            Generate a CSV file with sample employee data including columns:
            Employee_ID, Name, Department, Salary, Years_of_Service.
            Include at least 5 rows of data.
        """,
        """
            I have generated the CSV file with sample employee data. You can download it using the link below:
            
            [Download sample_employee_data.csv](sandbox:/v1/files/...sample_employee_data.csv)
        """,
        True,  # expect_file_generation
        id=f"{FileManagementTool.CODE_EXECUTOR}_generate_csv",
        marks=[pytest.mark.code_executor],
    ),
    pytest.param(
        FileManagementTool.CODE_EXECUTOR,
        """
            Generate an Excel file (.xlsx) with sample sales data including columns:
            Date, Product, Quantity, Price, Total.
            Include at least 10 rows of data across multiple months.
        """,
        """
            I have generated the Excel file containing sample sales data as requested. You can download it using the link below:
            
            [Download sample_sales_data.xlsx](sandbox:/v1/files/...sample_sales_data.xlsx)
        """,
        True,  # expect_file_generation
        id=f"{FileManagementTool.CODE_EXECUTOR}_generate_xlsx",
        marks=[pytest.mark.code_executor],
    ),
    pytest.param(
        FileManagementTool.CODE_EXECUTOR,
        """
            Generate a text file with a short story about a robot learning to code.
            The story should be at least 5 sentences long.
        """,
        """
            I have created a text file with a short story about a robot learning to code. You can download it using the link below:
            
            [Download the story - Robot Learns to Code](sandbox:/v1/files/...Robot_Learns_to_Code.txt)
        """,
        True,  # expect_file_generation
        id=f"{FileManagementTool.CODE_EXECUTOR}_generate_txt",
        marks=[pytest.mark.code_executor],
    ),
    pytest.param(
        FileManagementTool.CODE_EXECUTOR,
        """
            Generate a Word document (.docx) with a formatted report titled "Q4 2025 Summary".
            Include a title, 3 sections with headings, and some sample content in each section.
        """,
        """
            The Word document titled "Q4 2025 Summary" has been generated successfully. It contains the specified title and sections with headings. You can download it using the link below:
            
            [Download Q4_2025_Summary.docx](sandbox:/v1/files/...Q4_2025_Summary.docx)
        """,
        True,  # expect_file_generation
        id=f"{FileManagementTool.CODE_EXECUTOR}_generate_docx",
        marks=[pytest.mark.code_executor],
    ),
    pytest.param(
        FileManagementTool.CODE_EXECUTOR,
        """
            Generate a bar chart showing monthly revenue data for 2025.
            Use random data between 50000 and 150000 for each month.
            Save it as a PNG image.
        """,
        """
            The bar chart showing monthly revenue data for 2025 has been generated and saved as a PNG image. You can download it using the link below:
            
            [Download the chart](sandbox:/v1/files/...monthly_revenue_2025.png)
        """,
        True,  # expect_file_generation
        id=f"{FileManagementTool.CODE_EXECUTOR}_generate_plot",
        marks=[pytest.mark.code_executor],
    ),
]


def create_file_task(file_name: str) -> str:
    return f"Create a new file {file_name} under /tmp and add a method in python to sum two numbers"


def insert_to_file_task(file_name: str) -> str:
    return f"Insert comment 'Calculate the sum' before return statement to the file /tmp/{file_name}"


def show_diff_task(file_name: str) -> str:
    return f"Show the diff in /tmp/{file_name} file"


def show_file_task(file_name: str) -> str:
    return f"Show the content of the file /tmp/{file_name}"


RESPONSE_FOR_DIFF_UPDATE = """
    Here's the diff for the file:

    +    # Calculate the sum

"""

RESPONSE_FOR_FILE_EDITOR = """
    Here is the updated content of the file with the inserted comment:

    ```python
    1    def sum_two_numbers(x, y):
    2        # Calculate the sum of x and y
    3        return x + y
    ```

    If you need any further modifications or have other requests, please let me know!
"""

file_editing_tools_test_data = [
    (
        (FileManagementTool.WRITE_FILE, FileManagementTool.DIFF_UPDATE),
        RESPONSE_FOR_DIFF_UPDATE,
    ),
    (
        FileManagementTool.FILESYSTEM_EDITOR,
        RESPONSE_FOR_FILE_EDITOR,
    ),
]
