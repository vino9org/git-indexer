import sys

from dotenv import load_dotenv

from .cli import main

if __name__ == "__main__":
    load_dotenv()
    main(argv=sys.argv[1:])
