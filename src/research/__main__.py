"""Entry point for `python -m src.research`.

Thin wrapper that delegates to cli.main(). Kept separate so cli.py can be
imported in tests without triggering argparse side effects.
"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
