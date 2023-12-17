import sys

from dotenv import load_dotenv
from loguru import logger

from .cli import main

logger.remove()
logger.add(sys.stdout, level="INFO")

if __name__ == "__main__":
    load_dotenv()
    main(argv=sys.argv[1:])
