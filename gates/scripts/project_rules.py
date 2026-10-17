"""The project.json rules, and the self-test helpers, the kit's release, review, and incident
scripts share. Standard library only.

Imported by skills/release/scripts/halt_watch.py,
skills/release-readiness/scripts/readiness_check.py, skills/ci-green/scripts/review_gate.py,
skills/incident-review/scripts/incident_check.py, and gates/scripts/sarif_gate.py, so no two
of them can disagree on what an unset key, a placeholder, or a discipline is. Each
importer's self-test covers the rules it uses; this module has no entry point of its own.
"""
import json
import re

PLACEHOLDER = re.compile(r"^\s*<.*>\s*$")
# A value passed to a command as a bare argument: no option, path, or shell metacharacter.
BARE_ARGUMENT = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]*$")
DISCIPLINES = ("security", "data-ml", "mobile", "embedded", "sre")


def is_unset(value):
    """Absent, blank, `none` in any case, or a README placeholder: a key nothing was
    configured for."""
    if value is None:
        return True
    if isinstance(value, str):
        return (not value.strip() or value.strip().lower() == "none"
                or PLACEHOLDER.match(value) is not None)
    return isinstance(value, list) and any(isinstance(entry, str) and PLACEHOLDER.match(entry)
                                           for entry in value)


def read_config(config_path):
    """project.json as a dict, or raise ValueError naming what is wrong."""
    try:
        with open(config_path, encoding="utf-8") as handle:
            config = json.load(handle)
    except (OSError, ValueError) as error:
        raise ValueError(f"project.json unreadable: {error}")
    if not isinstance(config, dict):
        raise ValueError("project.json is not an object")
    return config


def named_disciplines(config):
    """The `disciplines` list, matched with case; absent is the README's default, []."""
    value = config.get("disciplines", [])
    if not (isinstance(value, list) and all(isinstance(name, str) for name in value)):
        raise ValueError("disciplines is not a list of names")
    unknown = [name for name in value if name not in DISCIPLINES]
    if unknown:
        raise ValueError(f"disciplines names {', '.join(map(repr, unknown))}, not one of "
                         + ", ".join(DISCIPLINES))
    return value


def report(kind, name, got, expected):
    """One self-test line; 1 on a mismatch, so callers can sum failures."""
    if got == expected:
        print(f"ok   {kind}: {name}")
        return 0
    print(f"FAIL {kind}: {name} — expected {expected!r}, got {got!r}")
    return 1


def result_of(function, *arguments):
    """The function's result, or "ValueError" when it raises one."""
    try:
        return function(*arguments)
    except ValueError:
        return "ValueError"


def error_of(function, *arguments):
    """"ok" when the function returns, or "ValueError" when it raises one."""
    try:
        function(*arguments)
    except ValueError:
        return "ValueError"
    return "ok"
