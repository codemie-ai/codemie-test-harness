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

"""Test data for mermaid diagram generation."""

import uuid
from typing import Literal, Tuple
import pytest

ThemeType = Literal["dark", "default"]


def generate_unique_id() -> str:
    """Generate a unique identifier to avoid S3 caching."""
    return str(uuid.uuid4())[:8]


def create_flowchart(theme: ThemeType) -> Tuple[str, str, str]:
    """Create a flowchart diagram with random data."""
    unique_id = generate_unique_id()
    theme_directive = (
        f"%%{{init: {{'theme':'{theme}'}}}}%%\n" if theme != "default" else ""
    )

    code = f"""{theme_directive}flowchart TD
    Start_{unique_id}[Start Process] --> Decision_{unique_id}{{Is Valid?}}
    Decision_{unique_id} -->|Yes| Process_{unique_id}[Process Data]
    Decision_{unique_id} -->|No| Error_{unique_id}[Handle Error]
    Process_{unique_id} --> End_{unique_id}[End]
    Error_{unique_id} --> End_{unique_id}
"""

    return ("flowchart", code, theme)


def create_sequence_diagram(theme: ThemeType) -> Tuple[str, str, str]:
    """Create a sequence diagram with random data."""
    unique_id = generate_unique_id()
    theme_directive = (
        f"%%{{init: {{'theme':'{theme}'}}}}%%\n" if theme != "default" else ""
    )

    code = f"""{theme_directive}sequenceDiagram
    participant User_{unique_id}
    participant API_{unique_id}
    participant DB_{unique_id}

    User_{unique_id}->>API_{unique_id}: Request Data
    API_{unique_id}->>DB_{unique_id}: Query
    DB_{unique_id}-->>API_{unique_id}: Results
    API_{unique_id}-->>User_{unique_id}: Response
"""

    return ("sequence", code, theme)


def create_class_diagram(theme: ThemeType) -> Tuple[str, str, str]:
    """Create a class diagram with random data."""
    unique_id = generate_unique_id()
    theme_directive = (
        f"%%{{init: {{'theme':'{theme}'}}}}%%\n" if theme != "default" else ""
    )

    code = f"""{theme_directive}classDiagram
    class User_{unique_id} {{
        +String name
        +String email_{unique_id}
        +login()
        +logout()
    }}
    class Session_{unique_id} {{
        +String id_{unique_id}
        +DateTime created
        +validate()
    }}
    User_{unique_id} --> Session_{unique_id}
"""

    return ("class", code, theme)


def create_state_diagram(theme: ThemeType) -> Tuple[str, str, str]:
    """Create a journey diagram with random data."""
    unique_id = generate_unique_id()
    theme_directive = (
        f"%%{{init: {{'theme':'{theme}'}}}}%%\n" if theme != "default" else ""
    )

    code = f"""{theme_directive}journey
    title User Journey {unique_id}
    section Planning {unique_id}
      Create Task: 5: User
      Review Task: 3: Manager
    section Development {unique_id}
      Implement: 4: Developer
      Test: 5: QA
"""

    return ("journey", code, theme)


def create_er_diagram(theme: ThemeType) -> Tuple[str, str, str]:
    """Create an entity relationship diagram with random data."""
    unique_id = generate_unique_id()
    theme_directive = (
        f"%%{{init: {{'theme':'{theme}'}}}}%%\n" if theme != "default" else ""
    )

    code = f"""{theme_directive}erDiagram
    USER_{unique_id} ||--o{{ ORDER_{unique_id} : places
    ORDER_{unique_id} ||--|{{ LINE_ITEM_{unique_id} : contains
    PRODUCT_{unique_id} ||--o{{ LINE_ITEM_{unique_id} : includes
    USER_{unique_id} {{
        string id_{unique_id}
        string name
        string email
    }}
"""

    return ("er", code, theme)


def create_gantt_chart(theme: ThemeType) -> Tuple[str, str, str]:
    """Create a Gantt chart with random data."""
    unique_id = generate_unique_id()
    theme_directive = (
        f"%%{{init: {{'theme':'{theme}'}}}}%%\n" if theme != "default" else ""
    )

    code = f"""{theme_directive}gantt
    title Project_{unique_id}
    dateFormat  YYYY-MM-DD
    section Phase1_{unique_id}
    Task1_{unique_id}    :a1, 2024-01-01, 30d
    Task2_{unique_id}    :after a1, 20d
    section Phase2_{unique_id}
    Task3_{unique_id}    :2024-02-01, 25d
"""

    return ("gantt", code, theme)


def create_pie_chart(theme: ThemeType) -> Tuple[str, str, str]:
    """Create a pie chart with random data."""
    unique_id = generate_unique_id()
    theme_directive = (
        f"%%{{init: {{'theme':'{theme}'}}}}%%\n" if theme != "default" else ""
    )

    # Use fixed valid percentages to avoid rendering issues
    code = f"""{theme_directive}pie title Distribution_{unique_id}
    "Category_A_{unique_id}" : 30
    "Category_B_{unique_id}" : 25
    "Category_C_{unique_id}" : 25
    "Category_D_{unique_id}" : 20
"""

    return ("pie", code, theme)


def create_gitgraph(theme: ThemeType) -> Tuple[str, str, str]:
    """Create a git graph with random data."""
    unique_id = generate_unique_id()
    theme_directive = (
        f"%%{{init: {{'theme':'{theme}'}}}}%%\n" if theme != "default" else ""
    )

    code = f"""{theme_directive}gitGraph
    commit id: "init_{unique_id}"
    branch develop_{unique_id}
    commit id: "feature_{unique_id}"
    checkout main
    merge develop_{unique_id}
    commit id: "release_{unique_id}"
"""

    return ("gitgraph", code, theme)


def create_mindmap(theme: ThemeType) -> Tuple[str, str, str]:
    """Create a mindmap with random data."""
    unique_id = generate_unique_id()
    theme_directive = (
        f"%%{{init: {{'theme':'{theme}'}}}}%%\n" if theme != "default" else ""
    )

    code = f"""{theme_directive}mindmap
  root((Project_{unique_id}))
    Planning_{unique_id}
      Requirements_{unique_id}
      Design_{unique_id}
    Development_{unique_id}
      Frontend_{unique_id}
      Backend_{unique_id}
    Testing_{unique_id}
"""

    return ("mindmap", code, theme)


def create_timeline(theme: ThemeType) -> Tuple[str, str, str]:
    """Create a timeline with random data."""
    unique_id = generate_unique_id()
    theme_directive = (
        f"%%{{init: {{'theme':'{theme}'}}}}%%\n" if theme != "default" else ""
    )

    code = f"""{theme_directive}timeline
    title History_{unique_id}
    2021 : Event_{unique_id}_A
         : Event_{unique_id}_B
    2022 : Event_{unique_id}_C
    2023 : Event_{unique_id}_D
"""

    return ("timeline", code, theme)


# Diagram generators - 5 with dark theme, 5 with default (light) theme
DIAGRAM_GENERATORS = [
    create_flowchart,
    create_sequence_diagram,
    create_class_diagram,
    create_state_diagram,
    create_er_diagram,
    create_gantt_chart,
    create_pie_chart,
    create_gitgraph,
    create_mindmap,
    create_timeline,
]


def generate_test_data():
    """Generate parametrized test data with 10 test cases.

    Returns 5 diagrams with dark theme and 5 with light theme.
    Each run generates unique identifiers to avoid S3 caching.
    """
    test_data = []

    # First 5 with dark theme + SVG
    for i, generator in enumerate(DIAGRAM_GENERATORS[:5]):
        diagram_type, code, theme = generator("dark")
        test_data.append(
            pytest.param(
                diagram_type, code, theme, "svg", id=f"{diagram_type}_dark_svg"
            )
        )

    # Next 5 with default (light) theme + PNG
    for i, generator in enumerate(DIAGRAM_GENERATORS[5:]):
        diagram_type, code, theme = generator("default")
        test_data.append(
            pytest.param(
                diagram_type, code, theme, "png", id=f"{diagram_type}_light_png"
            )
        )

    return test_data


# Generate test data once per test session
mermaid_test_data = generate_test_data()
