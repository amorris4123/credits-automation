"""
Credit Bot - Main Orchestrator
Coordinates Slack monitoring, Looker query extraction, notebook execution, and result posting
"""

import logging
import sys
from typing import Dict, Optional
from pathlib import Path

from .config import Config
from .slack_client import SlackClient
from .looker_client import LookerClient
from .notebook_executor import NotebookExecutor  # TODO: Will be replaced by SageMakerExecutor (see SAGEMAKER_MIGRATION_PLAN.md)
from .state_manager import StateManager

# Setup logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class CreditBot:
    """
    Main bot orchestrator for automated credit processing
    """

    def __init__(self):
        """Initialize the credit bot with all necessary clients"""
        logger.info("="*80)
        logger.info("Initializing CreditBot")
        logger.info("="*80)

        # Initialize clients
        self.slack = SlackClient()
        self.looker = LookerClient()
        self.executor = NotebookExecutor()
        self.state = StateManager()

        # Get channel
        self.channel_name = Config.get_channel()
        self.channel_id = None

        logger.info(f"Bot Name: {Config.BOT_NAME}")
        logger.info(f"Target Channel: #{self.channel_name}")
        logger.info(f"Notebook: {Config.NOTEBOOK_PATH}")

    def initialize(self) -> bool:
        """
        Initialize and test all connections

        Returns:
            bool: True if all initializations successful
        """
        logger.info("\n" + "="*80)
        logger.info("Testing Connections")
        logger.info("="*80)

        # Test Slack
        if not self.slack.test_connection():
            logger.error("❌ Slack connection failed")
            return False
        logger.info("✅ Slack connection successful")

        # Get channel ID
        self.channel_id = self.slack.get_channel_id(self.channel_name)
        if not self.channel_id:
            logger.error(f"❌ Channel #{self.channel_name} not found")
            return False
        logger.info(f"✅ Found channel #{self.channel_name}")

        # Test Looker
        if not self.looker.authenticate():
            logger.error("❌ Looker authentication failed")
            return False
        logger.info("✅ Looker authentication successful")

        logger.info("\n✅ All systems initialized successfully")
        return True

    def process_message(self, parsed_request: Dict) -> Dict:
        """
        Process a single credit request message
        Handles multiple Looker URLs and combines credit amounts

        Args:
            parsed_request: Parsed message from Slack

        Returns:
            Processing result dictionary
        """
        message_ts = parsed_request['message_ts']
        looker_urls = parsed_request['looker_urls']  # Now a list

        logger.info("\n" + "="*80)
        logger.info(f"Processing Message: {message_ts}")
        logger.info("="*80)

        result = {
            'success': False,
            'message_ts': message_ts,
            'credit_amount': None,
            'error': None,
            'posted_to_slack': False,
            'urls_processed': []
        }

        # Check if Looker link is present
        if not parsed_request['has_looker_link']:
            logger.warning("No Looker link found in message")
            result['error'] = "No Looker link found"

            # Post message requesting Looker link
            self.slack.post_message(
                channel_id=self.channel_id,
                text="⚠️ Please provide a Looker link for processing",
                thread_ts=message_ts
            )
            result['posted_to_slack'] = True

            return result

        logger.info(f"Found {len(looker_urls)} Looker URL(s) to process")

        # Process all Looker URLs and accumulate credit amounts
        total_credit = 0.0
        successful_executions = []
        processing_errors = []

        for idx, looker_url in enumerate(looker_urls, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"Processing URL {idx}/{len(looker_urls)}")
            logger.info(f"{'='*80}")
            logger.info(f"Looker URL: {looker_url}")

            # Step 1: Extract SQL from Looker
            logger.info(f"\n📊 Step 1: Extracting SQL from Looker...")
            sql_query = self.looker.get_sql_from_url(looker_url)

            if not sql_query:
                error_msg = f"Failed to extract SQL from URL {idx}"
                logger.error(error_msg)
                processing_errors.append(f"URL {idx}: {error_msg}")
                continue

            logger.info(f"✅ SQL extracted ({len(sql_query)} characters)")

            # Step 2: Check if it's a Verify query
            logger.info(f"\n🔍 Step 2: Checking if this is a Verify query...")
            is_verify = self.executor.is_verify_query(sql_query)

            if not is_verify:
                logger.info("This appears to be a PSMS query - skipping silently")
                continue

            logger.info("✅ Confirmed: This is a Verify query")

            # Step 3: Execute notebook
            logger.info(f"\n📓 Step 3: Executing notebook...")
            exec_result = self.executor.execute(sql_query)

            if not exec_result['success']:
                error_msg = f"Notebook execution failed: {exec_result['error']}"
                logger.error(error_msg)
                processing_errors.append(f"URL {idx}: {error_msg}")
                continue

            credit_amount = exec_result['credit_amount']
            logger.info(f"✅ Notebook executed successfully")
            logger.info(f"💰 Credit Amount for URL {idx}: ${credit_amount:.2f}")

            # Accumulate credit amount
            total_credit += credit_amount
            successful_executions.append({
                'url': looker_url,
                'amount': credit_amount
            })

        # Check if we had any successful executions
        if not successful_executions:
            error_summary = "; ".join(processing_errors) if processing_errors else "No Verify queries found or all processing failed"
            logger.error(f"No successful executions: {error_summary}")
            result['error'] = error_summary
            self._handle_error(parsed_request, result['error'])
            return result

        # Step 4: Post combined result to Slack
        logger.info(f"\n{'='*80}")
        logger.info(f"All URLs Processed - Total: ${total_credit:.2f}")
        logger.info(f"{'='*80}")
        logger.info(f"\n💬 Step 4: Posting combined result to Slack...")

        post_success = self._post_result(
            channel_id=self.channel_id,
            thread_ts=message_ts,
            credit_amount=total_credit
        )

        result['success'] = True
        result['credit_amount'] = total_credit
        result['posted_to_slack'] = post_success
        result['urls_processed'] = successful_executions

        logger.info("\n✅ Message processing complete")
        return result

    def _post_result(self, channel_id: str, thread_ts: str, credit_amount: float) -> bool:
        """
        Post credit amount result to Slack thread

        Args:
            channel_id: Channel ID
            thread_ts: Thread timestamp
            credit_amount: Calculated credit amount

        Returns:
            bool: True if posted successfully
        """
        # Format message as requested: "Approved, (amount), (category)"
        # Category defaults to "exceptions" for now
        message = f"Approved, ${credit_amount:.2f}, exceptions"

        success = self.slack.post_message(
            channel_id=channel_id,
            text=message,
            thread_ts=thread_ts
        )
        if success:
            logger.info(f"✅ Posted result to Slack: {message}")
        else:
            logger.error("❌ Failed to post result to Slack")
        return success

    def _handle_error(self, parsed_request: Dict, error_message: str):
        """
        Handle processing errors by sending DM

        Args:
            parsed_request: Parsed request that failed
            error_message: Error description
        """
        message_ts = parsed_request['message_ts']
        user_id = parsed_request.get('user_id', 'Unknown')

        dm_text = (
            f"⚠️ Credit Bot Processing Error\n\n"
            f"Message: {message_ts}\n"
            f"Error: {error_message}\n\n"
            f"Please review manually."
        )

        if Config.SLACK_USER_ID:
            self.slack.send_dm(Config.SLACK_USER_ID, dm_text)
            logger.info(f"✅ Sent error DM to {Config.SLACK_USER_ID}")
        else:
            logger.warning("No SLACK_USER_ID configured for error DMs")

    def run_once(self):
        """
        Run one iteration of message checking and processing
        """
        logger.info("\n" + "="*80)
        logger.info("Starting Message Check")
        logger.info("="*80)

        # Get recent messages
        messages = self.slack.get_recent_messages(self.channel_id, limit=50)
        logger.info(f"Retrieved {len(messages)} messages")

        # Filter out already processed
        unprocessed = self.state.get_unprocessed_messages(messages)
        logger.info(f"Found {len(unprocessed)} unprocessed messages")

        if not unprocessed:
            logger.info("No new messages to process")
            self.state.update_last_check()
            return

        # Process each unprocessed message
        for message in unprocessed:
            parsed = self.slack.parse_credit_request(message)

            if not parsed:
                continue

            # Process the message
            result = self.process_message(parsed)

            # Mark as processed (even if it failed, so we don't retry indefinitely)
            self.state.mark_processed(
                parsed['message_ts'],
                metadata={
                    'success': result['success'],
                    'credit_amount': result['credit_amount'],
                    'error': result['error']
                }
            )

        # Update last check timestamp
        self.state.update_last_check()

        # Print stats
        stats = self.state.get_stats()
        logger.info("\n" + "="*80)
        logger.info("Session Complete")
        logger.info("="*80)
        logger.info(f"Total Processed (All Time): {stats['total_processed']}")
        logger.info(f"Last Check: {stats['last_check']}")


def main():
    """Main entry point"""
    logger.info("\n" + "="*80)
    logger.info(f"CREDIT BOT - {Config.BOT_NAME}")
    logger.info("="*80)
    logger.info(f"Environment: {Config.EXECUTION_ENV}")
    logger.info(f"S3 Storage: {'Enabled' if Config.USE_S3_STORAGE else 'Disabled (Local)'}")
    logger.info("="*80 + "\n")

    # Create bot
    bot = CreditBot()

    # Initialize
    if not bot.initialize():
        logger.error("Initialization failed. Exiting.")
        return 1

    # Run once
    try:
        bot.run_once()
        logger.info("\n✅ Bot execution complete")
        return 0
    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Bot stopped by user")
        return 130
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
