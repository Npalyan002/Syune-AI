"""Internal process probe; do not route this endpoint through the public proxy."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


def main() -> int:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8080/ready", timeout=5) as response:
            payload = json.loads(response.read())
            return 0 if response.status == 200 and payload == {"status": "ready"} else 1
    except (OSError, ValueError, urllib.error.URLError):
        return 1


if __name__ == "__main__":
    sys.exit(main())
