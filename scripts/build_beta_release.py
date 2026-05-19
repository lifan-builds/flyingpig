#!/usr/bin/env python3
"""Build a local Flying Pig beta release zip."""

from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_NAME = "flyingpig-beta"

INCLUDE_PATHS = [
    "README.md",
    "pyproject.toml",
    "requirements.txt",
    "docs/beta.md",
    "dashboard",
    "src",
    "scripts",
    "prompts",
]

EXCLUDE_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".DS_Store",
}


def should_include(path: Path) -> bool:
    return not any(part in EXCLUDE_NAMES for part in path.parts)


def add_path(zf: zipfile.ZipFile, source: Path, archive_root: str) -> None:
    if source.is_file():
        zf.write(source, Path(archive_root) / source.relative_to(ROOT))
        return

    for path in source.rglob("*"):
        if should_include(path) and path.is_file():
            zf.write(path, Path(archive_root) / path.relative_to(ROOT))


def build_release(version: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_root = f"{DEFAULT_NAME}-{version}"
    zip_path = output_dir / f"{archive_root}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in INCLUDE_PATHS:
            add_path(zf, ROOT / item, archive_root)
        zf.writestr(
            f"{archive_root}/INSTALL_BETA.md",
            beta_install_text(),
        )
    return zip_path


def beta_install_text() -> str:
    return """# Flying Pig Beta Install

1. Install Python 3.12+ and Chrome.
2. From this folder, run:

   ```bash
   pip install -e ".[dev]"
   playwright install
   flyingpig-helper
   ```

   Keep this terminal open while using Flying Pig. Press Ctrl+C to stop.

3. Use the dashboard at `http://127.0.0.1:8765/dashboard/`.
4. Click **Launch Work Window**.
5. Prepare the customer-service tab, choose a playbook, confirm the task, and supervise the run.

Optional background helper service:

```bash
flyingpig-macos-helper install
flyingpig-macos-helper status
flyingpig-macos-helper stop
flyingpig-macos-helper start
flyingpig-macos-helper uninstall
```
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--clean", action="store_true", help="Remove output dir before building")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.clean and args.output_dir.exists():
        shutil.rmtree(args.output_dir)
    zip_path = build_release(args.version, args.output_dir)
    print(f"Built beta release: {zip_path}")


if __name__ == "__main__":
    main()
