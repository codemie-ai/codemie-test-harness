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

"""Test data for vendor workflow e2e tests."""

import json
import pytest
from codemie_sdk.models.vendor_assistant import VendorType
from codemie_sdk.models.integration import CredentialTypes

from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


vendor_workflow_test_data = [
    pytest.param(
        VendorType.AWS,
        CredentialTypes.AWS,
        CredentialsManager.aws_credentials(),
        "codemie-autotests-flow-object-input",
        json.dumps({"genre": "pop", "number": 3}),
        """
            # Pop Playlist: Just Three Hits

            1. "As It Was" by Harry Styles
            2. "Blinding Lights" by The Weeknd
            3. "Levitating" by Dua Lipa

            These three modern pop classics offer a perfect mini-playlist with upbeat tempos and catchy hooks. Enjoy!
        """,
        marks=[pytest.mark.aws, pytest.mark.bedrock],
        id="AWS_Bedrock_Object_Input",
    ),
    pytest.param(
        VendorType.AWS,
        CredentialTypes.AWS,
        CredentialsManager.aws_credentials(),
        "codemie-autotests-flow-string-input",
        "pop",
        """
            # Pop Playlist (3 Songs)
            
            1. "Blinding Lights" - The Weeknd
               *Upbeat synth-pop track with irresistible 80s vibes and a catchy chorus*
            
            2. "As It Was" - Harry Styles
               *Melodic pop anthem with nostalgic undertones and danceable rhythm*
            
            3. "Levitating" - Dua Lipa
               *Disco-infused pop banger with infectious grooves and stellar vocals*
            
            Enjoy these modern pop hits! Would you like any specific recommendations or adjustments to the playlist?
        """,
        marks=[pytest.mark.aws, pytest.mark.bedrock],
        id="AWS_Bedrock_String_Input",
    ),
    pytest.param(
        VendorType.AWS,
        CredentialTypes.AWS,
        CredentialsManager.aws_credentials(),
        "codemie-autotests-flow-number-input",
        json.dumps(3),
        """
            # Pop Playlist (3 Songs)
            
            1. "Shape of You" - Ed Sheeran
            2. "Blinding Lights" - The Weeknd
            3. "Dance Monkey" - Tones and I
            
            Each of these songs has been a massive pop hit with catchy hooks and radio-friendly production. Enjoy your playlist!
        """,
        marks=[pytest.mark.aws, pytest.mark.bedrock],
        id="AWS_Bedrock_Number_Input",
    ),
    pytest.param(
        VendorType.AWS,
        CredentialTypes.AWS,
        CredentialsManager.aws_credentials(),
        "codemie-autotests-flow-boolean-input",
        json.dumps(True),
        """
            # Pop Playlist (3 Songs)
            
            1. "Bad Guy" by Billie Eilish
            2. "Blinding Lights" by The Weeknd
            3. "As It Was" by Harry Styles
            
            These are three popular pop songs from recent years that feature catchy melodies, modern production, and have achieved significant commercial success.
        """,
        marks=[pytest.mark.aws, pytest.mark.bedrock],
        id="AWS_Bedrock_Boolean_Input",
    ),
    pytest.param(
        VendorType.AWS,
        CredentialTypes.AWS,
        CredentialsManager.aws_credentials(),
        "codemie-autotests-flow-array-input",
        json.dumps(["pop", "rock"]),
        """
            # Playlist Creation
            
            Here are two playlists with 2 songs each:
            
            ## Pop Playlist (2 songs)
            1. "Shape of You" by Ed Sheeran
            2. "Bad Guy" by Billie Eilish
            
            ## Rock Playlist (2 songs)
            1. "Bohemian Rhapsody" by Queen
            2. "Sweet Child O' Mine" by Guns N' Roses
            
            Would you like me to expand either playlist with more song suggestions or provide information about any of these tracks?
        """,
        marks=[pytest.mark.aws, pytest.mark.bedrock],
        id="AWS_Bedrock_Array_Input",
    ),
    # pytest.param(
    #     VendorType.AZURE,
    #     CredentialTypes.AZURE,
    #     CredentialsManager.azure_credentials(),
    #     "workflow-name",
    #     json.dumps({"genre": "rock", "number": 5}),
    #     "Rock Playlist",
    #     marks=[pytest.mark.azure],
    #     id="Azure_AI_Object_Input",
    # ),
    # pytest.param(
    #     VendorType.GCP,
    #     CredentialTypes.GCP,
    #     CredentialsManager.gcp_credentials(),
    #     "workflow-name",
    #     json.dumps({"genre": "jazz", "number": 4}),
    #     "Jazz Playlist",
    #     marks=[pytest.mark.gcp],
    #     id="GCP_Vertex_AI_Object_Input",
    # ),
]
