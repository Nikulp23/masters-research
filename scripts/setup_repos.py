"""
Clone and install the real repositories required for the benchmark tasks.

Usage:
    python scripts/setup_repos.py
    python scripts/setup_repos.py --skip-install   # clone only, no pip/npm install

All 25 repos are listed below, grouped by language category.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


REPOS_DIR = Path(__file__).parent.parent / "repos"

REPOS: list[dict] = [
    # -------------------------------------------------------------------------
    # Python (5)
    # -------------------------------------------------------------------------
    {
        "name": "requests",
        "url": "https://github.com/psf/requests.git",
        "dest": str(REPOS_DIR / "requests"),
        "tasks": ["requests-header-injection"],
        "install_cmd": [sys.executable, "-m", "pip", "install", "-e",
                        str(REPOS_DIR / "requests"), "--quiet"],
    },
    {
        "name": "werkzeug",
        "url": "https://github.com/pallets/werkzeug.git",
        "dest": str(REPOS_DIR / "werkzeug"),
        "tasks": ["werkzeug-cookie-maxage"],
        "install_cmd": [sys.executable, "-m", "pip", "install", "-e",
                        str(REPOS_DIR / "werkzeug"), "--quiet"],
    },
    {
        "name": "click",
        "url": "https://github.com/pallets/click.git",
        "dest": str(REPOS_DIR / "click"),
        "tasks": ["click-intrange-open-bounds"],
        "install_cmd": [sys.executable, "-m", "pip", "install", "-e",
                        str(REPOS_DIR / "click"), "--quiet"],
    },
    {
        "name": "flask",
        "url": "https://github.com/pallets/flask.git",
        "dest": str(REPOS_DIR / "flask"),
        "tasks": ["flask-json-datetime"],
        "install_cmd": [sys.executable, "-m", "pip", "install", "-e",
                        str(REPOS_DIR / "flask"), "--quiet"],
    },
    {
        "name": "httpx",
        "url": "https://github.com/encode/httpx.git",
        "dest": str(REPOS_DIR / "httpx"),
        "tasks": ["httpx-backoff-formula"],
        "install_cmd": [sys.executable, "-m", "pip", "install", "-e",
                        str(REPOS_DIR / "httpx"), "--quiet"],
    },
    # -------------------------------------------------------------------------
    # Go (5)
    # -------------------------------------------------------------------------
    {
        "name": "viper",
        "url": "https://github.com/spf13/viper.git",
        "dest": str(REPOS_DIR / "viper"),
        "tasks": ["viper-config-merge"],
        "install_cmd": None,  # go modules; no pip install needed
    },
    {
        "name": "cobra",
        "url": "https://github.com/spf13/cobra.git",
        "dest": str(REPOS_DIR / "cobra"),
        "tasks": ["cobra-nil-map-panic"],
        "install_cmd": None,
    },
    {
        "name": "gin",
        "url": "https://github.com/gin-gonic/gin.git",
        "dest": str(REPOS_DIR / "gin"),
        "tasks": ["gin-query-empty-param"],
        "install_cmd": None,
    },
    {
        "name": "validator",
        "url": "https://github.com/go-playground/validator.git",
        "dest": str(REPOS_DIR / "validator"),
        "tasks": ["validator-printable-ascii-tab"],
        "install_cmd": None,
    },
    {
        "name": "testify",
        "url": "https://github.com/stretchr/testify.git",
        "dest": str(REPOS_DIR / "testify"),
        "tasks": ["testify-nil-vs-empty-slice"],
        "install_cmd": None,
    },
    # -------------------------------------------------------------------------
    # JavaScript (5)
    # -------------------------------------------------------------------------
    {
        "name": "commander.js",
        "url": "https://github.com/tj/commander.js.git",
        "dest": str(REPOS_DIR / "commander.js"),
        "tasks": ["commander-split-description"],
        "install_cmd": ["npm", "install", "--prefix", str(REPOS_DIR / "commander.js"),
                        "--legacy-peer-deps"],
    },
    {
        "name": "lodash",
        "url": "https://github.com/lodash/lodash.git",
        "dest": str(REPOS_DIR / "lodash"),
        "tasks": ["lodash-round-negative-exp"],
        "install_cmd": ["npm", "install", "--prefix", str(REPOS_DIR / "lodash"),
                        "--legacy-peer-deps"],
    },
    {
        "name": "date-fns",
        "url": "https://github.com/date-fns/date-fns.git",
        "dest": str(REPOS_DIR / "date-fns"),
        "tasks": ["datefns-month-zero-pad"],
        "install_cmd": ["npm", "install", "--prefix", str(REPOS_DIR / "date-fns"),
                        "--legacy-peer-deps"],
    },
    {
        "name": "axios",
        "url": "https://github.com/axios/axios.git",
        "dest": str(REPOS_DIR / "axios"),
        "tasks": ["axios-double-slash-url"],
        "install_cmd": ["npm", "install", "--prefix", str(REPOS_DIR / "axios"),
                        "--legacy-peer-deps"],
    },
    {
        "name": "marked",
        "url": "https://github.com/markedjs/marked.git",
        "dest": str(REPOS_DIR / "marked"),
        "tasks": ["marked-escape-order"],
        "install_cmd": ["npm", "install", "--prefix", str(REPOS_DIR / "marked"),
                        "--legacy-peer-deps"],
    },
    # -------------------------------------------------------------------------
    # TypeScript (5)
    # -------------------------------------------------------------------------
    {
        "name": "zod",
        "url": "https://github.com/colinhacks/zod.git",
        "dest": str(REPOS_DIR / "zod"),
        "tasks": ["zod-optional-validate"],
        "install_cmd": ["npm", "install", "--prefix", str(REPOS_DIR / "zod"),
                        "--legacy-peer-deps"],
    },
    {
        "name": "class-transformer",
        "url": "https://github.com/typestack/class-transformer.git",
        "dest": str(REPOS_DIR / "class-transformer"),
        "tasks": ["class-transformer-nested-keys"],
        "install_cmd": ["npm", "install", "--prefix", str(REPOS_DIR / "class-transformer"),
                        "--legacy-peer-deps"],
    },
    {
        "name": "ts-pattern",
        "url": "https://github.com/gvergnaud/ts-pattern.git",
        "dest": str(REPOS_DIR / "ts-pattern"),
        "tasks": ["ts-pattern-wildcard-order"],
        "install_cmd": ["npm", "install", "--prefix", str(REPOS_DIR / "ts-pattern"),
                        "--legacy-peer-deps"],
    },
    {
        "name": "yup",
        "url": "https://github.com/jquense/yup.git",
        "dest": str(REPOS_DIR / "yup"),
        "tasks": ["yup-collect-all-errors"],
        "install_cmd": ["npm", "install", "--prefix", str(REPOS_DIR / "yup"),
                        "--legacy-peer-deps"],
    },
    {
        "name": "typeorm",
        "url": "https://github.com/typeorm/typeorm.git",
        "dest": str(REPOS_DIR / "typeorm"),
        "tasks": ["typeorm-and-conditions"],
        "install_cmd": ["npm", "install", "--prefix", str(REPOS_DIR / "typeorm"),
                        "--legacy-peer-deps"],
    },
    # -------------------------------------------------------------------------
    # React (5)
    # -------------------------------------------------------------------------
    {
        "name": "react-hook-form",
        "url": "https://github.com/react-hook-form/react-hook-form.git",
        "dest": str(REPOS_DIR / "react-hook-form"),
        "tasks": ["react-hook-form-reset-baseline"],
        "install_cmd": ["npm", "install", "--prefix", str(REPOS_DIR / "react-hook-form"),
                        "--legacy-peer-deps"],
    },
    {
        "name": "zustand",
        "url": "https://github.com/pmndrs/zustand.git",
        "dest": str(REPOS_DIR / "zustand"),
        "tasks": ["zustand-persist-hydrate"],
        "install_cmd": ["npm", "install", "--prefix", str(REPOS_DIR / "zustand"),
                        "--legacy-peer-deps"],
    },
    {
        "name": "jotai",
        "url": "https://github.com/pmndrs/jotai.git",
        "dest": str(REPOS_DIR / "jotai"),
        "tasks": ["jotai-derived-recompute"],
        "install_cmd": ["npm", "install", "--prefix", str(REPOS_DIR / "jotai"),
                        "--legacy-peer-deps"],
    },
    {
        "name": "tanstack-query",
        "url": "https://github.com/TanStack/query.git",
        "dest": str(REPOS_DIR / "tanstack-query"),
        "tasks": ["tanstack-query-staletime"],
        "install_cmd": ["npm", "install", "--prefix", str(REPOS_DIR / "tanstack-query"),
                        "--legacy-peer-deps"],
    },
    {
        "name": "react-router",
        "url": "https://github.com/remix-run/react-router.git",
        "dest": str(REPOS_DIR / "react-router"),
        "tasks": ["react-router-wildcard-match"],
        "install_cmd": ["npm", "install", "--prefix", str(REPOS_DIR / "react-router"),
                        "--legacy-peer-deps"],
    },
]


def run(cmd: list[str], cwd: str | None = None) -> int:
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


# Clone the repo if it doesn't exist yet, then run its install command.
def setup_repo(repo: dict, skip_install: bool) -> bool:
    dest = Path(repo["dest"])
    print(f"\n{'='*60}")
    print(f"Repo:  {repo['name']}")
    print(f"Dest:  {dest}")
    print(f"Tasks: {', '.join(repo['tasks'])}")

    if dest.exists():
        print("  Already exists — skipping clone.")
    else:
        print("  Cloning...")
        rc = run(["git", "clone", "--depth", "1", repo["url"], str(dest)])
        if rc != 0:
            print(f"  ERROR: clone failed (exit {rc})")
            return False

    if not skip_install:
        install_cmd = repo.get("install_cmd")
        if install_cmd is None:
            print("  No install step (Go module — deps resolved at test time).")
        else:
            print(f"  Installing ({' '.join(str(c) for c in install_cmd)})...")
            rc = run(install_cmd)
            if rc != 0:
                print(f"  WARNING: install failed (exit {rc}) — tasks may not run correctly")

    print("  Ready.")
    return True


# Parse CLI args and set up whichever repos were requested (or all of them by default).
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clone and set up all benchmark repositories."
    )
    parser.add_argument(
        "--skip-install", action="store_true",
        help="Clone only, do not run install commands."
    )
    parser.add_argument(
        "--repos", nargs="*",
        help="Only set up repos with these names (default: all)."
    )
    args = parser.parse_args()

    REPOS_DIR.mkdir(parents=True, exist_ok=True)

    repos_to_setup = REPOS
    if args.repos:
        repos_to_setup = [r for r in REPOS if r["name"] in args.repos]
        if not repos_to_setup:
            print(f"No repos matched: {args.repos}")
            sys.exit(1)

    if not shutil.which("git"):
        print("ERROR: git not found on PATH.")
        sys.exit(1)

    results = [setup_repo(repo, args.skip_install) for repo in repos_to_setup]
    print(f"\n{'='*60}")
    print(f"Done. {sum(results)}/{len(results)} repos ready.")
    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
