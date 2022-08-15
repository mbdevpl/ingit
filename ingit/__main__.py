"""Entry point of ingit package."""

# PYTHON_ARGCOMPLETE_OK

from ._logging import Logging
from .main import main


if __name__ == '__main__':
    Logging.configure_basic()
    main()
