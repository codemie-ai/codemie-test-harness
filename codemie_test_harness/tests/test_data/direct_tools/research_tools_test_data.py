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

from codemie_test_harness.tests.enums.tools import ResearchToolName

# Live search results drift, so the expectation describes the result shape only.
research_tools_test_data = [
    (
        ResearchToolName.GOOGLE_SEARCH,
        {"query": "AI trends 2024"},
        """
        A JSON list of web search results about AI trends in 2024. Each result is an object with a
        'title' field, a 'link' field (a URL), and a 'snippet' field summarizing the page content.
        """,
    ),
    pytest.param(
        ResearchToolName.TAVILY_SEARCH,
        {
            "query": "AI trends 2024",
        },
        """
        answer
        """,
        marks=pytest.mark.skip(
            reason="Temporarily skipping Tavily test until it is fixed"
        ),
        id=ResearchToolName.TAVILY_SEARCH,
    ),
    # Place IDs are stable per-place identifiers, not PII, so a placeholder
    # pattern is enough to describe the shape without a real phone number.
    (
        ResearchToolName.GOOGLE_PLACES,
        {"query": "McDonalds in Olomouc"},
        """
            A numbered list of McDonald's locations in Olomouc, Czechia. Each entry has the name
            "McDonald's", a street address in Olomouc, and a Google place ID matching the pattern
            "ChIJ...".
        """,
    ),
    (
        ResearchToolName.GOOGLE_PLACES_FIND_NEAR,
        {"current_location_query": "Kyiv", "target": "McDonalds", "radius": 20},
        """
        A JSON list of place results for McDonald's near Kyiv. Each result is an object with a
        'business_status' field (e.g. "OPERATIONAL"), a 'geometry.location' object with 'lat' and
        'lng' coordinates, a 'name' field containing "McDonald's", a 'rating' field, and a 'place_id'
        matching the pattern "ChIJ...".
        """,
    ),
    (
        ResearchToolName.WEB_SCRAPPER,
        {
            "url": "https://webscraper.io/about-us",
        },
        """
        # About us | Web Scraper

        *Source: https://webscraper.io/about-us*

        ## Our story

        Web Scraper started as a Chrome browser extension in 2013. Its
        popularity quickly grew as it was the most advanced and completely
        free. Today Web Scraper is both a free browser extension and also a
        Cloud based Web Scraping solution for complete automation.

        ## Our mission

        Our mission is to make web data accessible to everyone by making
        the most advanced and easiest to use web scraping tool.

        ## Company data

        * Company: “Web Graph“ SIA
        * Address: Ubelu 5-71, Adazi, Latvia, LV-2164

        ## Contact Us

        * [info@webscraper.io](mailto:info@webscraper.io)
        """,
    ),
    # (
    #     ResearchToolName.WIKIPEDIA,
    #     {"query": "Ethics of artificial intelligence"},
    #     """
    #     Page: Ethics of artificial intelligence
    #     Summary: The ethics of artificial intelligence covers a broad range of topics within AI that are considered to have particular
    #     ethical stakes. This includes algorithmic biases, fairness, automated decision-making, accountability, privacy, and regulation.
    #     It also covers various emerging or potential future challenges such as machine ethics (how to make machines that behave ethically),
    #     lethal autonomous weapon systems, arms race dynamics, AI safety and alignment, technological unemployment, AI-enabled misinformation,
    #      how to treat certain AI systems if they have a moral status (AI welfare and rights), artificial superintelligence and existential risks.
    #     Some application areas may also have particularly important ethical implications, like healthcare, education, criminal justice, or the military.
    #
    #     Page: Friendly artificial intelligence
    #     Summary: Friendly artificial intelligence (friendly AI or FAI) is hypothetical artificial general intelligence (AGI)
    #     that would have a positive (benign) effect on humanity or at least align with human interests such as fostering the improvement of the
    #     human species. It is a part of the ethics of artificial intelligence and is closely related to machine ethics. While machine ethics is
    #     concerned with how an artificially intelligent agent should behave, friendly artificial intelligence research is focused on how to practically
    #     bring about this behavior and ensuring it is adequately constrained.
    #
    #     Page: Regulation of artificial intelligence
    #     Summary: Regulation of artificial intelligence is the development of public sector policies and laws for promoting and
    #     regulating artificial intelligence (AI). It is part of the broader regulation of algorithms. The regulatory and policy landscape
    #     for AI is an emerging issue in jurisdictions worldwide, including for international organizations without direct enforcement power
    #     like the IEEE or the OECD. Since 2016, numerous AI ethics guidelines have been published in order to maintain social control over
    #     the technology. Regulation is deemed necessary to both foster AI innovation and manage associated risks. Furthermore, organizations
    #     deploying AI have a central role to play in creating and implementing trustworthy AI, adhering to established principles, and taking
    #     accountability for mitigating risks. Regulating AI through mechanisms such as review boards can also be seen as social means to approach
    #     the AI control problem.
    #     """,
    # ),
]
