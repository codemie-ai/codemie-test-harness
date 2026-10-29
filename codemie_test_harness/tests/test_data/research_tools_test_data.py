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

search_tools_test_data = [
    (
        ResearchToolName.GOOGLE_SEARCH,
        """
            Run Google Search Tool and query: AI trends.
            Represent in JSON format with title and link
        """,
        50,
    ),
    pytest.param(
        ResearchToolName.TAVILY_SEARCH,
        """
            Run Google Search Tool and query: AI trends
            Represent in JSON format with title and link
        """,
        50,
        marks=pytest.mark.skip(
            reason="Temporarily skipping Tavily test until it is fixed"
        ),
    ),
]
# Live place data (ratings, review counts, open status) drifts, so only the
# durable identity of each place is asserted.
interactions_tools_test_data = [
    (
        ResearchToolName.GOOGLE_PLACES,
        "Find McDonald in the Kyiv on the Khreschatyk, 19-a",
        """
            I found a McDonald's location on Khreschatyk Street in Kyiv:
            McDonald's
            Address: Khreschatyk St, 19-a, Kyiv, Ukraine
            The response also reports a rating, a number of user ratings, an "open now" status,
            and a price level for the place.
        """,
    ),
    (
        ResearchToolName.GOOGLE_PLACES_FIND_NEAR,
        "Find McDonalds in the Kyiv near Khreschatyk in radius 2 km",
        """
            A McDonald's-branded location found within 2 km of Khreschatyk, Kyiv.
            The response reports the place's name, address, an operational/open status,
            a rating, and a Google Place ID.
        """,
    ),
    # (
    #     ResearchToolName.WIKIPEDIA,
    #     "Short description of AI from Wikipedia",
    #     """
    #         Artificial intelligence (AI) is the capability of computer systems to perform tasks requiring human intelligence,
    #         such as learning, reasoning, problem-solving, and decision-making. It encompasses various technologies and methods,
    #         including machine learning and neural networks, enabling machines to perceive their environment, adapt, and take
    #         actions to achieve specific goals. AI applications include virtual assistants, self-driving cars, recommendation systems,
    #         and advanced game play, with ongoing advancements raising ethical and regulatory considerations.
    #     """,
    # ),
    (
        ResearchToolName.WEB_SCRAPPER,
        "Web Scrap this page https://webscraper.io/about-us",
        """
            Here is the scraped content from the [Web Scraper - About Us](https://webscraper.io/about-us) page:
            # About us | Web Scraper
            ## Our story
            Web Scraper started as a Chrome browser extension in 2013. Its popularity quickly grew as it was the most advanced and completely free. Today Web Scraper is both a free browser extension and also a Cloud based Web Scraping solution for complete automation.
            ## Our mission
            Our mission is to make web data accessible to everyone by making the most advanced and easiest to use web scraping tool.
            ## Company data
            - **Company**: “Web Graph“ SIA
            - **Address**: Ubelu 5-71, Adazi, Latvia, LV-2164
            ## Contact Us
            - Email: [info@webscraper.io](mailto:info@webscraper.io)
        """,
    ),
]
