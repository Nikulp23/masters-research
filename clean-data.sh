#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Cleaning generated benchmark and site data..."
rm -rf "$ROOT_DIR/benchmark_runs"
rm -rf "$ROOT_DIR/site-data"
mkdir -p "$ROOT_DIR/benchmark_runs"
mkdir -p "$ROOT_DIR/site-data"
cat > "$ROOT_DIR/site-data/conversations.json" <<'EOF'
{
  "generated_from": "benchmark_runs",
  "issue_count": 0,
  "issues": []
}
EOF
cat > "$ROOT_DIR/site-data/conversations.js" <<'EOF'
window.AGENTIC_CONVERSATIONS = {
  "generated_from": "benchmark_runs",
  "issue_count": 0,
  "issues": []
};
EOF
echo "Done."
