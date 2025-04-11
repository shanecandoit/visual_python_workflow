import logging
import sys
import time # Import time module for datefmt

def setup_logger(level=logging.INFO):
    """Configures a basic console logger with yyyy-mm-dd-hh-mm-ss timestamp."""
    log_format = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d-%H-%M-%S" # Define the desired date format
    logging.basicConfig(level=level, format=log_format, datefmt=date_format, stream=sys.stdout)
    logger = logging.getLogger(__name__)
    # Use time.strftime to format the current time for the initial message if needed,
    # or rely on the logger's formatter. The logger will handle it automatically.
    logger.info(f"Logger configured. Timestamp format: {date_format}")
    return logger

if __name__ == '__main__':
    # Example usage if run directly
    logger = setup_logger(logging.DEBUG)
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")