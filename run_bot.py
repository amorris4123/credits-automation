#!/usr/bin/env python3
"""
Credit Bot Runner
Runs the credit automation bot with production-ready features
"""

import sys
import signal
import logging
from src.credit_bot import main

logger = logging.getLogger(__name__)

# Track if we received a shutdown signal
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle graceful shutdown on SIGTERM/SIGINT"""
    global shutdown_requested
    signal_name = signal.Signals(signum).name
    logger.info(f"\n⚠️  Received {signal_name}, initiating graceful shutdown...")
    shutdown_requested = True


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    logger.debug("Signal handlers registered for SIGTERM and SIGINT")


if __name__ == "__main__":
    setup_signal_handlers()

    try:
        exit_code = main()
        sys.exit(exit_code if exit_code is not None else 0)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Keyboard interrupt received")
        sys.exit(130)  # Standard exit code for Ctrl+C
    except Exception as e:
        logger.error(f"❌ Unexpected error in main: {e}", exc_info=True)
        sys.exit(1)
