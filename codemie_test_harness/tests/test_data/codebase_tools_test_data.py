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

from codemie_test_harness.tests.enums.tools import Toolkit, CodeBaseTool
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

code_tools_test_data = [
    pytest.param(
        Toolkit.CODEBASE_TOOLS,
        CodeBaseTool.GET_REPOSITORY_FILE_TREE_V2,
        "Get repo file tree and answer what programming language repository has?",
        """The repository primarily uses Java as the programming language,
as indicated by the file paths and extensions such as .java.""",
        marks=pytest.mark.smoke,
    ),
    (
        Toolkit.CODEBASE_TOOLS,
        CodeBaseTool.READ_FILES_CONTENT,
        "Find build.gradle and show main library or framework what we use in project, only name",
        """The main libraries and frameworks used in the project, as specified in the `build.gradle` file, include:
    RestAssure, Selenide, Log4j, JUnit, AssertJ, Lombok, Jackson, Awaitility, JsonPath, AspectJ, Apache Commons,
    Amazon AWS SDK, Java, SonarQube""",
    ),
    (
        Toolkit.CODEBASE_TOOLS,
        CodeBaseTool.READ_FILES_CONTENT_SUMMARY,
        "Find build.gradle and say for what purpose we use the project, only one purpose",
        """
            The project appears to be focused on automated testing, 
            particularly regression testing for APIs and UI components as well as featured run
        """,
    ),
    (
        Toolkit.CODEBASE_TOOLS,
        CodeBaseTool.SEARCH_CODE_REPO_BY_PATH,
        "Find the file be path src/main/Test.java and return value which in file",
        """
            File contain only one method 
            public class TestClass {  
                public static void main(String[] args) {
                    System.out.println("Hello, World!");
                }
            }
        """,
    ),
    (
        Toolkit.CODEBASE_TOOLS,
        CodeBaseTool.SEARCH_CODE_REPO_V2,
        "Do we use Rest assure if yes, pls, show dependency and file name where the dependency",
        "Yes we have the dependency and file where saved the dependency build.gradle",
    ),
]

sonar_tools_test_data = [
    pytest.param(
        Toolkit.CODEBASE_TOOLS,
        CodeBaseTool.SONAR,
        CredentialsManager.sonar_credentials(),
        """
            Always run tool for each user request.
            Try to find any code smells and return if you have an access to sonar or not? 
            relative_url='/api/issues/search'
            params={'types': ['CODE_SMELL'], 'ps': 1}
            Do not pass any other parameters.
            Answer must be: Yes, I have an access to SonarQube or No, I do not have an access to SonarQube. Without any information about code smells.
        """,
        "Yes, I have an access to SonarQube",
        marks=pytest.mark.sonar,
        id=CodeBaseTool.SONAR,
    ),
    pytest.param(
        Toolkit.CODEBASE_TOOLS,
        CodeBaseTool.SONAR_CLOUD,
        CredentialsManager.sonar_cloud_credentials(),
        """
            Always run tool for each user request.
            Try to find any code smells and return if you have an access to sonar or not? 
            relative_url='/api/issues/search'
            params={'types': ['CODE_SMELL'], 'ps': 1}
            Do not pass any other parameters.
            Answer must be: Yes, I have an access to SonarQube or No, I do not have an access to SonarQube. Without any information about code smells.
        """,
        "Yes, I have an access to SonarQube",
        marks=[pytest.mark.sonar, pytest.mark.cloud],
        id=CodeBaseTool.SONAR_CLOUD,
    ),
]
