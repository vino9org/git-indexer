import os
import sys

from dotenv import load_dotenv
from loguru import logger

from .cli import main

if __name__ == "__main__":
    load_dotenv()

    logger.remove()
    log_file = os.environ.get("LOG_FILE")
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    logger.add(log_file if log_file else sys.stdout, level=log_level)  # type: ignore

    main(argv=sys.argv[1:])
