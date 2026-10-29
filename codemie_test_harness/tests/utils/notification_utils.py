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

import email
import imaplib
import logging
import re
from email.header import decode_header
from typing import Optional

import msal
import requests

from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

logger = logging.getLogger(__name__)


class OAuthGmailTokenRetriever:
    _instance = None
    token: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OAuthGmailTokenRetriever, cls).__new__(cls)
            cls._fetch_access_token()
        return cls._instance

    @staticmethod
    def _fetch_access_token():
        credentials = CredentialsManager.oauth_credentials()

        token_url = credentials[0].value
        if token_url is None:
            raise ValueError("Missing url")

        client_id = credentials[1].value
        if client_id is None:
            raise ValueError("Missing client_id")

        client_secret = credentials[2].value
        if client_secret is None:
            raise ValueError("Missing client_secret")

        refresh_token = credentials[3].value
        if refresh_token is None:
            raise ValueError("Missing refresh_token")

        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        response = requests.post(
            token_url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            logger.error(f"Failed to obtain gmail access token {response.reason}")
            raise RuntimeError(
                f"Failed to obtain gmail access token: {response.reason}"
            )

        OAuthGmailTokenRetriever._instance.token = response.json().get("access_token")


class GmailUtils:
    def __init__(self, base_url: str = "https://gmail.googleapis.com/gmail/v1"):
        self.base_url = base_url
        self.token = OAuthGmailTokenRetriever().token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

    def _build_url(self, endpoint: str) -> str:
        return f"{self.base_url}{endpoint}"

    def get_messages_list(self):
        logger.info("Get All Messages From Inbox")
        url = self._build_url("/users/me/messages")
        response = requests.get(url, headers=self.headers)
        return response.json()

    def get_specific_message_content(self, message_id: str):
        logger.info(f"Get Specific Message Content From {message_id}")
        url = self._build_url(f"/users/me/messages/{message_id}")
        response = requests.get(url, headers=self.headers)
        return response.json()

    def delete_specific_message(self, message_id: str):
        logger.info(f"Delete Specific Message With Id {message_id}")
        url = self._build_url(f"/users/me/messages/{message_id}")
        requests.delete(url, headers=self.headers)

    def delete_all_messages(self):
        logger.info("Deleting all messages from Gmail inbox...")
        message_data = self.get_messages_list()

        messages = message_data.get("messages", [])
        if not messages:
            logger.info("No messages found to delete.")
            return

        for msg in messages:
            message_id = msg["id"]
            self.delete_specific_message(message_id)

        logger.info("Finished deleting all messages.")


class OAuthAzureTokenRetriever:
    _instance = None
    token: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OAuthAzureTokenRetriever, cls).__new__(cls)
            cls._fetch_access_token()
        return cls._instance

    @staticmethod
    def _fetch_access_token():
        client_id = CredentialsManager.get_parameter("AZURE_EMAIL_CLIENT_ID")
        if client_id is None:
            raise ValueError("Missing AZURE_EMAIL_CLIENT_ID")

        tenant_id = CredentialsManager.get_parameter("AZURE_EMAIL_TENANT_ID")
        if tenant_id is None:
            raise ValueError("Missing AZURE_EMAIL_TENANT_ID")

        client_secret = CredentialsManager.get_parameter("AZURE_EMAIL_CLIENT_SECRET")
        if client_secret is None:
            raise ValueError("Missing AZURE_EMAIL_CLIENT_SECRET")

        authority = f"https://login.microsoftonline.com/{tenant_id}"
        scopes = ["https://outlook.office365.com/.default"]

        app = msal.ConfidentialClientApplication(
            client_id=client_id, authority=authority, client_credential=client_secret
        )

        result = app.acquire_token_for_client(scopes=scopes)

        if "access_token" in result:
            OAuthAzureTokenRetriever._instance.token = result["access_token"]
            logger.info("Azure access token acquired successfully")
        else:
            error_msg = f"Failed to acquire Azure access token: {result.get('error')} - {result.get('error_description')}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)


class AzureEmailUtils:
    def __init__(
        self, imap_server: str = "outlook.office365.com", imap_port: int = 993
    ):
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.user_email = CredentialsManager.get_parameter("AZURE_EMAIL_USER_EMAIL")
        self.token = OAuthAzureTokenRetriever().token

    @staticmethod
    def _generate_auth_string(user: str, token: str) -> str:
        """Generate OAuth2 authentication string for IMAP."""
        return f"user={user}\x01auth=Bearer {token}\x01\x01"

    @staticmethod
    def _decode_mime_words(s: str) -> str:
        """Decode MIME encoded words in email headers."""
        decoded_fragments = decode_header(s)
        fragments = []
        for fragment, encoding in decoded_fragments:
            if isinstance(fragment, bytes):
                fragments.append(fragment.decode(encoding or "utf-8"))
            else:
                fragments.append(fragment)
        return "".join(fragments)

    def _connect_imap(self) -> imaplib.IMAP4_SSL:
        """Connect and authenticate to IMAP server."""
        imap = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
        imap.authenticate(
            "XOAUTH2",
            lambda x: self._generate_auth_string(self.user_email, self.token),
        )
        imap.select("inbox")
        logger.info("Connected and authenticated to Azure IMAP server")
        return imap

    def get_messages_list(self):
        """Get list of all messages in inbox."""
        logger.info("Get All Messages From Azure Inbox")
        imap = self._connect_imap()

        try:
            status, messages = imap.search(None, "ALL")
            if status == "OK":
                email_ids = messages[0].split()
                message_list = {
                    "messages": [{"id": email_id.decode()} for email_id in email_ids]
                }
                logger.info(f"Found {len(email_ids)} messages in Azure inbox")
                return message_list
            else:
                logger.error(f"Failed to search messages: {status}")
                return {"messages": []}
        finally:
            imap.close()
            imap.logout()

    def get_specific_message_content(self, message_id: str):
        """Get specific message content by ID."""
        logger.info(f"Get Specific Message Content From {message_id}")
        imap = self._connect_imap()

        try:
            status, msg_data = imap.fetch(message_id.encode(), "(RFC822)")

            if status == "OK":
                msg = email.message_from_bytes(msg_data[0][1])

                # Get subject
                subject = self._decode_mime_words(msg.get("Subject", "No Subject"))

                # Get from
                from_header = self._decode_mime_words(msg.get("From", "Unknown"))

                # Get date
                date = msg.get("Date", "Unknown")

                # Extract body (gets text/plain part)
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition", ""))

                        # Skip attachments
                        if "attachment" in content_disposition:
                            continue

                        # Get text/plain part
                        if content_type == "text/html":
                            try:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    # payload can be bytes or str depending on encoding
                                    if isinstance(payload, bytes):
                                        body = payload.decode("utf-8", errors="ignore")
                                    else:
                                        body = str(payload)
                                    break
                            except Exception as e:
                                logger.warning(f"Failed to decode part: {e}")
                                continue
                else:
                    # Single part message
                    try:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            # payload can be bytes or str depending on encoding
                            if isinstance(payload, bytes):
                                body = payload.decode("utf-8", errors="ignore")
                            else:
                                body = str(payload)
                    except Exception as e:
                        logger.warning(f"Failed to decode message payload: {e}")
                        # Try without decoding
                        body = str(msg.get_payload())

                # Strip HTML tags from body
                body = re.sub(r"<[^>]+>", "", body)

                # Clean up body and create snippet
                body_cleaned = body.strip().replace("\r\n", " ").replace("\n", " ")
                snippet = (
                    body_cleaned if len(body_cleaned) <= 100 else body_cleaned[:100]
                )

                # Create a structure similar to Gmail API response
                return {
                    "snippet": snippet,
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": subject},
                            {"name": "From", "value": from_header},
                            {"name": "Date", "value": date},
                        ]
                    },
                }
            else:
                logger.error(f"Failed to fetch message {message_id}: {status}")
                return None
        finally:
            imap.close()
            imap.logout()

    def delete_specific_message(self, message_id: str):
        """Delete a specific message by ID."""
        logger.info(f"Delete Specific Message With Id {message_id}")
        imap = self._connect_imap()

        try:
            imap.store(message_id.encode(), "+FLAGS", "\\Deleted")
            imap.expunge()
            logger.info(f"Message {message_id} deleted successfully")
        finally:
            imap.close()
            imap.logout()

    def delete_all_messages(self):
        """Delete all messages with 'Test email' subject from Azure inbox."""
        logger.info("Deleting test messages from Azure inbox...")
        message_data = self.get_messages_list()

        messages = message_data.get("messages", [])
        if not messages:
            logger.info("No messages found to delete.")
            return

        deleted_count = 0
        for msg in messages:
            message_id = msg["id"]
            try:
                message_content = self.get_specific_message_content(message_id)
                if message_content:
                    # Get subject from headers
                    subject = next(
                        (
                            header["value"]
                            for header in message_content["payload"]["headers"]
                            if header["name"].lower() == "subject"
                        ),
                        None,
                    )

                    # Only delete messages with "Test email" subject
                    if subject and subject == "Test email":
                        self.delete_specific_message(message_id)
                        deleted_count += 1
                        logger.info(
                            f"Deleted message {message_id} with subject '{subject}'"
                        )
            except Exception as e:
                logger.warning(f"Failed to process message {message_id}: {e}")
                continue

        logger.info(f"Finished deleting test messages. Total deleted: {deleted_count}")
