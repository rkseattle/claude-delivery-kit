#!/usr/bin/env bash
# Every action a workflow file names is pinned to a 40-character commit SHA, the only ref that
# cannot move under it; a tag, branch, or short SHA can. Each workflow is parsed as YAML and
# every jobs.<id>.uses and jobs.<id>.steps[].uses is checked, as OpenSSF Scorecard's
# Pinned-Dependencies check does: a local ./ action passes, being versioned with the workflow,
# and a docker:// image passes only by @sha256 digest. Comments, run: text, and key spacing
# are YAML's to read, not a line pattern's. A local action's own action.yml is not read.
# Usage: actions-pinned.sh [repo-root]
set -euo pipefail
root="${1:-.}"
gates="$(cd "$(dirname "$0")/../../gates/scripts" && pwd)"
python3 - "$root" "$gates" <<'PY'
import glob
import os
import re
import sys

root, gates = sys.argv[1:3]
sys.dont_write_bytecode = True
sys.path.insert(0, gates)
from project_rules import YAML_VENDOR, vendored  # noqa: E402

vendored(YAML_VENDOR)
import yaml  # noqa: E402

PINNED = re.compile(r"^[^@\s]+@[0-9a-fA-F]{40}$")
DIGEST = re.compile(r"^docker://[^@\s]+@sha256:[0-9a-fA-F]{64}$")
workflows = sorted(glob.glob(os.path.join(glob.escape(root), ".github", "workflows", "*.yml"))
                   + glob.glob(os.path.join(glob.escape(root), ".github", "workflows", "*.yaml")))
if not workflows:
    sys.exit(f"no workflow files under {root}/.github/workflows")


def child(node, key):
    """The value node under key in a mapping node, or None."""
    if isinstance(node, yaml.MappingNode):
        for k, v in node.value:
            if isinstance(k, yaml.ScalarNode) and k.value == key:
                return v
    return None


def uses_nodes(document):
    """Every jobs.<id>.uses and jobs.<id>.steps[].uses node, in file order."""
    jobs = child(document, "jobs")
    if not isinstance(jobs, yaml.MappingNode):
        raise ValueError("has no jobs: mapping")
    for _, job in jobs.value:
        if child(job, "uses") is not None:
            yield child(job, "uses")
        steps = child(job, "steps")
        for step in steps.value if isinstance(steps, yaml.SequenceNode) else ():
            if child(step, "uses") is not None:
                yield child(step, "uses")


def pinned(ref):
    return ref.startswith("./") or bool(PINNED.match(ref) or DIGEST.match(ref))


unpinned, unparseable = [], []
for path in workflows:
    try:
        with open(path, encoding="utf-8") as handle:
            nodes = list(uses_nodes(yaml.compose(handle, Loader=yaml.SafeLoader)))
    except (OSError, ValueError, yaml.YAMLError) as error:
        unparseable.append(f"UNPARSEABLE {path}: {(str(error).splitlines() or [type(error).__name__])[0]}")
        continue
    for node in nodes:
        ref = node.value if isinstance(node, yaml.ScalarNode) else ""
        if not (isinstance(ref, str) and pinned(ref)):
            unpinned.append(f"{path}:{node.start_mark.line + 1}: uses: {ref or '<not a string>'}")
for line in unparseable + unpinned:
    print(line)
if unpinned:
    print("NOT PINNED: each uses: above names a ref other than a 40-character commit SHA")
if unpinned or unparseable:
    sys.exit(1)
print("ok: every action under .github/workflows is pinned to a commit SHA")
PY
