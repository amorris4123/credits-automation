"""
Looker API Client
Handles authentication and SQL query extraction from Looker
"""

import requests
import logging
from urllib.parse import urlparse, parse_qs
from typing import Optional
from .config import Config

logger = logging.getLogger(__name__)


class LookerClient:
    """Client for interacting with Looker API"""

    def __init__(self, client_id: str = None, client_secret: str = None, base_url: str = None):
        """
        Initialize Looker client

        Args:
            client_id: Looker API client ID (defaults to Config)
            client_secret: Looker API client secret (defaults to Config)
            base_url: Looker instance base URL (defaults to Config)
        """
        self.client_id = client_id or Config.LOOKER_CLIENT_ID
        self.client_secret = client_secret or Config.LOOKER_CLIENT_SECRET
        self.base_url = (base_url or Config.LOOKER_BASE_URL).rstrip('/')
        self.api_url = f"{self.base_url}/api/4.0"
        self.access_token = None

    def authenticate(self) -> bool:
        """
        Authenticate with Looker API and get access token

        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            auth_url = f"{self.api_url}/login"
            response = requests.post(
                auth_url,
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret
                }
            )
            response.raise_for_status()

            data = response.json()
            self.access_token = data.get('access_token')

            if not self.access_token:
                logger.error("No access token in Looker API response")
                return False

            logger.info("Successfully authenticated with Looker API")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Looker authentication failed: {e}")
            return False

    def _get_headers(self) -> dict:
        """Get request headers with authentication token"""
        if not self.access_token:
            if not self.authenticate():
                raise RuntimeError("Failed to authenticate with Looker")

        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def extract_look_id(self, url: str) -> Optional[str]:
        """
        Extract Look ID from Looker URL

        Args:
            url: Looker URL

        Returns:
            Look ID if found, None otherwise

        Examples:
            https://twilio.cloud.looker.com/looks/12345 -> "12345"
            https://twilio.cloud.looker.com/x/abcd1234 -> None (explore link)
        """
        try:
            parsed = urlparse(url)

            # Check for /looks/ pattern
            if '/looks/' in parsed.path:
                parts = parsed.path.split('/looks/')
                if len(parts) > 1:
                    look_id = parts[1].split('/')[0].split('?')[0]
                    return look_id

            # Check for /x/ pattern (short links)
            # These require a different API call
            if '/x/' in parsed.path:
                logger.warning(f"Short link format detected: {url}")
                logger.warning("Short links not yet supported - please use full Look URL")
                return None

            logger.warning(f"Could not extract Look ID from URL: {url}")
            return None

        except Exception as e:
            logger.error(f"Error parsing Looker URL: {e}")
            return None

    def get_look_sql(self, look_id: str) -> Optional[str]:
        """
        Get SQL query for a Look by ID

        Args:
            look_id: Look ID

        Returns:
            SQL query string if found, None otherwise
        """
        try:
            # First, get the Look details to get the query_id
            look_url = f"{self.api_url}/looks/{look_id}"
            response = requests.get(look_url, headers=self._get_headers())
            response.raise_for_status()

            look_data = response.json()
            query_id = look_data.get('query_id')

            if not query_id:
                logger.error(f"No query_id found for Look {look_id}")
                return None

            # Now get the query details to get the SQL
            query_url = f"{self.api_url}/queries/{query_id}"
            response = requests.get(query_url, headers=self._get_headers())
            response.raise_for_status()

            query_data = response.json()

            # The SQL might be in different fields depending on query type
            sql = None

            # Try different possible SQL fields
            if 'sql' in query_data:
                sql = query_data['sql']
            elif 'client_id' in query_data:
                # For some queries, we need to run them to get SQL
                sql = self._run_query_for_sql(query_id)

            if sql:
                logger.info(f"Successfully extracted SQL from Look {look_id}")
                return sql
            else:
                logger.error(f"Could not find SQL in query {query_id}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Look SQL: {e}")
            return None

    def _run_query_for_sql(self, query_id: str) -> Optional[str]:
        """
        Run a query to get its SQL
        Some queries require execution to generate SQL

        Args:
            query_id: Query ID

        Returns:
            SQL string if found, None otherwise
        """
        try:
            run_url = f"{self.api_url}/queries/{query_id}/run/sql"
            response = requests.get(run_url, headers=self._get_headers())
            response.raise_for_status()

            return response.text

        except requests.exceptions.RequestException as e:
            logger.error(f"Error running query for SQL: {e}")
            return None

    def get_sql_from_url(self, url: str) -> Optional[str]:
        """
        Extract SQL query from a Looker URL

        Args:
            url: Looker Look URL

        Returns:
            SQL query string if successful, None otherwise
        """
        logger.info(f"Extracting SQL from Looker URL: {url}")

        # Extract Look ID
        look_id = self.extract_look_id(url)
        if not look_id:
            logger.error("Could not extract Look ID from URL")
            return None

        # Get SQL
        sql = self.get_look_sql(look_id)
        if not sql:
            logger.error("Could not retrieve SQL from Look")
            return None

        return sql


# Example usage
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        client = LookerClient()

        if client.authenticate():
            sql = client.get_sql_from_url(test_url)
            if sql:
                print("\n" + "="*80)
                print("EXTRACTED SQL:")
                print("="*80)
                print(sql)
                print("="*80)
            else:
                print("Failed to extract SQL")
        else:
            print("Authentication failed")
    else:
        print("Usage: python -m src.looker_client <looker_url>")
