"""Extract only the PostgreSQL server directories from a Windows binaries zip.

The EnterprisedDB archive bundles pgAdmin 4, whose paths exceed Windows' 260
character limit and make a full extraction fail. The server itself (bin, share,
lib, include) is all this repository needs.

    python scripts/data/extract_pg.py postgres.zip C:\\pg
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

WANTED = ("pgsql/bin/", "pgsql/share/", "pgsql/lib/", "pgsql/include/")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", help="postgresql-*-windows-x64-binaries.zip")
    parser.add_argument("target", help="Directory to extract into")
    args = parser.parse_args()

    target = Path(args.target)
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.archive) as bundle:
        members = [name for name in bundle.namelist() if name.startswith(WANTED)]
        print(f"extracting {len(members)} of {len(bundle.namelist())} entries")
        for name in members:
            bundle.extract(name, target)
    print(f"done: {target / 'pgsql' / 'bin'}")


if __name__ == "__main__":
    main()
