#!/usr/bin/env python3
"""Watch a release stage's halt criteria for its monitoring window. Standard library only.

Called by skills/release/SKILL.md (Steps 1 and 5). The project.json rules it shares with
the other scripts are in gates/scripts/project_rules.py.

    halt_watch.py --config PATH     reads `halt_criteria` and `monitoring_window_minutes`
        from the project.json at PATH and runs each criterion from that project's root;
        prints `window clean` and exits 0 only when every criterion exited 0 in every
        round; otherwise prints one `HALT` line and exits 1
    halt_watch.py --check --config PATH
        validates those two keys and `rollout_stages` without watching; prints `ok` and
        exits 0, or prints `INVALID: <what>` to standard error and exits 1; release runs
        it before the tag.
        With `mobile` in `disciplines`, `rollout_stages` must list at least two stages: the
        stores' phased release (rule book Appendix B3) has a partial phase before the full one.
    halt_watch.py --self-test       runs every case below; exit 0 only if each one matches

A round starts on each minute from 0 through the window's end and runs every criterion at
once, as an Argo Rollouts AnalysisRun measures at a fixed interval with a failure limit of
zero. A criterion fires when it exits non-zero or is still running 55 seconds into its
round, since a check that cannot finish within its minute cannot run once a minute. A value
the watch cannot read is a halt too: a watch with nothing to check would pass.
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "gates", "scripts"))
from project_rules import (PROJECT_KEYS, cli_case,  # noqa: E402
                           named_disciplines, read_config, report)

ROUND_SECONDS = 60
BUDGET_SECONDS = 55
POLL_SECONDS = 0.05


def load(config_path):
    """(criteria, window) from project.json, or raise ValueError naming what is wrong."""
    return settings(read_config(config_path))


def settings(config):
    # gates/release.md stops on any value but these shapes, so read_keys' unset rule is not
    # applied: a halt_criteria of none or a window of none is an error, not unset.
    criteria = config.get("halt_criteria")
    PROJECT_KEYS["halt_criteria"].check(criteria)
    window = config.get("monitoring_window_minutes", 60)
    PROJECT_KEYS["monitoring_window_minutes"].check(window)
    return criteria, window


def check(config_path):
    """Validate every value the watch and the stage loop read, or raise ValueError."""
    config = read_config(config_path)
    settings(config)
    stages = config.get("rollout_stages", "none")
    if ("mobile" in named_disciplines(config)
            and not (isinstance(stages, list) and len(stages) >= 2)):
        raise ValueError("rollout_stages lists fewer than two stages, and mobile needs a phased "
                         "store release")
    PROJECT_KEYS["rollout_stages"].check(stages)


def stop(procs):
    for proc in procs:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def watch(criteria, window, round_seconds=ROUND_SECONDS, budget_seconds=BUDGET_SECONDS,
          cwd=None):
    """`window clean`, or the `HALT` line naming the round and the first criterion to fire."""
    running = []

    def on_signal(signum, _frame):
        stop(running)
        print(f"HALT: the watch was stopped by signal {signum}")
        sys.exit(1)

    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, on_signal)
    start = time.monotonic()
    for minute in range(window + 1):
        round_start = start + round_seconds * minute
        time.sleep(max(0, round_start - time.monotonic()))
        procs = running
        procs.clear()
        for c in criteria:
            procs.append(subprocess.Popen(["bash", "-c", c], stdin=subprocess.DEVNULL, cwd=cwd,
                                          start_new_session=True))
        pending = dict(zip(procs, criteria))
        deadline = round_start + budget_seconds
        while pending:
            for proc, criterion in list(pending.items()):
                code = proc.poll()
                if code is None:
                    continue
                del pending[proc]
                if code != 0:
                    stop(procs)
                    return f"HALT at minute {minute}: {criterion} ({code})"
            if pending and time.monotonic() >= deadline:
                stop(procs)
                criterion = next(iter(pending.values()))
                return (f"HALT at minute {minute}: {criterion} "
                        f"(no exit within {budget_seconds:g} seconds)")
            time.sleep(POLL_SECONDS)
        stop(procs)
    return "window clean"


def write_config(directory, value, name=None):
    path = os.path.join(directory, name or f"project-{abs(hash(repr(value)))}.json")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(value if isinstance(value, str) else json.dumps(value))
    return path


WATCH_CASES = [
    ("every criterion passes", ["true", "exit 0"], 1, "window clean"),
    ("a criterion exits non-zero", ["true", "exit 3"], 1, "HALT at minute 0: exit 3 (3)"),
    ("a criterion fires in a later round",
     ["test ! -e \"$MARK\" && touch \"$MARK\""], 2, "HALT at minute 1"),
    ("a criterion outlives its round", ["sleep 5"], 0, "HALT at minute 0: sleep 5 (no exit"),
    ("quotes and newlines survive", ["printf 'a\\nb\\n' | wc -l | grep -q 2"], 0, "window clean"),
]

SLOW_THEN_FAILING = ["sleep 1.5; true", "exit 7"]

CLI_CASES = [
    ("a clean window exits 0", [], {"halt_criteria": ["true"], "monitoring_window_minutes": 1},
     "window clean", 0),
    ("a fired criterion exits 1", [],
     {"halt_criteria": ["exit 4"], "monitoring_window_minutes": 1}, "HALT at minute 0", 1),
    ("criteria run from the project root", [],
     {"halt_criteria": ["test -f root-marker"], "monitoring_window_minutes": 1},
     "window clean", 0),
    ("an invalid config halts", [], {"halt_criteria": "true"},
     "HALT: halt_criteria is not", 1),
    ("--check passes a valid config", ["--check"],
     {"halt_criteria": ["true"], "rollout_stages": ["canary", "all"]}, "ok", 0),
    ("--check fails a bad config", ["--check"],
     {"halt_criteria": ["true"], "rollout_stages": ["staging"]}, "INVALID: rollout_stages", 1),
    ("--check fails a bad window", ["--check"],
     {"halt_criteria": ["true"], "monitoring_window_minutes": 0},
     "INVALID: monitoring_window_minutes", 1),
]

CHECK_CASES = [
    ("stages none", {"halt_criteria": ["true"], "rollout_stages": "none"}, "ok"),
    ("stages absent", {"halt_criteria": ["true"]}, "ok"),
    ("stages valid", {"halt_criteria": ["true"], "rollout_stages": ["canary", "v1.all_x-2"]},
     "ok"),
    ("stages as a string", {"halt_criteria": ["true"], "rollout_stages": "canary"},
     "ValueError"),
    ("stages empty", {"halt_criteria": ["true"], "rollout_stages": []}, "ValueError"),
    ("a blank stage", {"halt_criteria": ["true"], "rollout_stages": ["canary", ""]},
     "ValueError"),
    ("a staging stage", {"halt_criteria": ["true"], "rollout_stages": ["staging"]},
     "ValueError"),
    ("a repeated stage", {"halt_criteria": ["true"], "rollout_stages": ["a", "a"]},
     "ValueError"),
    ("a stage with a space", {"halt_criteria": ["true"], "rollout_stages": ["can ary"]},
     "ValueError"),
    ("a stage with a metacharacter", {"halt_criteria": ["true"], "rollout_stages": ["a;b"]},
     "ValueError"),
    ("a stage that looks like an option", {"halt_criteria": ["true"], "rollout_stages": ["-rf"]},
     "ValueError"),
    ("a stage that is a path", {"halt_criteria": ["true"], "rollout_stages": [".."]},
     "ValueError"),
    ("staging in another case", {"halt_criteria": ["true"], "rollout_stages": ["Staging"]},
     "ValueError"),
    ("a stage with a trailing newline", {"halt_criteria": ["true"], "rollout_stages": ["canary\n"]},
     "ValueError"),
    ("a non-string stage", {"halt_criteria": ["true"], "rollout_stages": ["canary", 3]},
     "ValueError"),
    ("bad criteria fail the check", {"halt_criteria": []}, "ValueError"),
    ("mobile with two stages", {"halt_criteria": ["true"], "disciplines": ["mobile"],
                                "rollout_stages": ["phased", "full"]}, "ok"),
    ("mobile with one stage", {"halt_criteria": ["true"], "disciplines": ["mobile"],
                               "rollout_stages": ["full"]}, "ValueError"),
    ("mobile with stages none on a small project",
     {"halt_criteria": ["true"], "disciplines": ["mobile"], "project_size": "small",
      "rollout_stages": "none"}, "ValueError"),
    ("mobile with stages absent", {"halt_criteria": ["true"], "disciplines": ["mobile"]},
     "ValueError"),
    ("disciplines as a string", {"halt_criteria": ["true"], "disciplines": "mobile",
                                 "rollout_stages": ["full"]}, "ValueError"),
    ("an unknown discipline", {"halt_criteria": ["true"], "disciplines": ["Mobile"],
                               "rollout_stages": ["full"]}, "ValueError"),
    ("one stage without mobile", {"halt_criteria": ["true"], "disciplines": ["sre"],
                                  "rollout_stages": ["full"]}, "ok"),
]

LOAD_CASES = [
    ("a valid config", {"halt_criteria": ["true"], "monitoring_window_minutes": 5},
     (["true"], 5)),
    ("the window defaults to 60", {"halt_criteria": ["true"]}, (["true"], 60)),
    ("criteria as a string", {"halt_criteria": "true"}, "ValueError"),
    ("criteria as an object", {"halt_criteria": {"a": 1}}, "ValueError"),
    ("criteria none", {"halt_criteria": "none"}, "ValueError"),
    ("an empty list", {"halt_criteria": []}, "ValueError"),
    ("a blank entry", {"halt_criteria": ["true", "  "]}, "ValueError"),
    ("a non-string entry", {"halt_criteria": ["true", 3]}, "ValueError"),
    ("criteria missing", {}, "ValueError"),
    ("a zero window", {"halt_criteria": ["true"], "monitoring_window_minutes": 0}, "ValueError"),
    ("a fractional window", {"halt_criteria": ["true"], "monitoring_window_minutes": 1.5},
     "ValueError"),
    ("a boolean window", {"halt_criteria": ["true"], "monitoring_window_minutes": True},
     "ValueError"),
    ("a string window", {"halt_criteria": ["true"], "monitoring_window_minutes": "60"},
     "ValueError"),
    ("not json", "not json", "ValueError"),
    ("a json list", [1], "ValueError"),
    ("a missing file", None, "ValueError"),
    ("a <placeholder>", {"halt_criteria": ["<shell command exiting non-zero>"]},
     "ValueError"),
]


def self_test():
    failures = 0
    with tempfile.TemporaryDirectory() as directory:
        os.environ["MARK"] = os.path.join(directory, "mark")
        for name, criteria, window, expected in WATCH_CASES:
            got = watch(criteria, window, round_seconds=0.5, budget_seconds=0.4)
            failures += report("watch", name, got[:len(expected)], expected)
        began = time.monotonic()
        got = watch(SLOW_THEN_FAILING, 0, round_seconds=2, budget_seconds=1.8)
        failures += report("watch", "a later failure is not held up by an earlier slow one",
                           (got, time.monotonic() - began < 1.0),
                           ("HALT at minute 0: exit 7 (7)", True))
        stamps = os.path.join(directory, "stamps")
        began = time.monotonic()
        got = watch([f"python3 -c 'import time; print(time.monotonic())' >> '{stamps}'"], 2,
                    round_seconds=0.5, budget_seconds=0.4)
        elapsed = time.monotonic() - began
        with open(stamps, encoding="utf-8") as handle:
            starts = [float(line) for line in handle.read().split()]
        gaps = [later - earlier for earlier, later in zip(starts, starts[1:])]
        failures += report("watch", "a clean window waits out every round",
                           (got, elapsed >= 1.0, len(starts)), ("window clean", True, 3))
        failures += report("watch", "each round starts a round apart",
                           all(gap >= 0.4 for gap in gaps), True)
        leftover = os.path.join(directory, "leftover")
        got = watch([f"(sleep 0.5; touch '{leftover}') & exit 0"], 0, round_seconds=0.5,
                    budget_seconds=0.4)
        time.sleep(1)
        failures += report("watch", "a clean round's background children are killed",
                           (got, os.path.exists(leftover)), ("window clean", False))
        for name, value, expected in LOAD_CASES:
            path = "/nonexistent/project.json" if value is None else write_config(directory, value)
            try:
                got = load(path)
            except ValueError:
                got = "ValueError"
            failures += report("load", name, got, expected)
        failures += cli_case(os.path.abspath(__file__), "no --config is a usage error", [], "", 2)
        for name, value, expected in CHECK_CASES:
            try:
                check(write_config(directory, value))
                got = "ok"
            except ValueError:
                got = "ValueError"
            failures += report("check", name, got, expected)
        script = os.path.abspath(__file__)
        root = os.path.join(directory, "root")
        os.makedirs(os.path.join(root, ".claude"))
        open(os.path.join(root, "root-marker"), "w").close()
        elsewhere = os.path.join(directory, "elsewhere")
        os.makedirs(elsewhere)
        clock = ["--round-seconds", "0.5", "--budget-seconds", "0.4"]
        for name, arguments, value, expected_output, expected_exit in CLI_CASES:
            config = write_config(os.path.join(root, ".claude"), value, "project.json")
            run = subprocess.run([sys.executable, script, *arguments, "--config", config, *clock],
                                 cwd=elsewhere, capture_output=True, text=True, check=False)
            stream = run.stderr if expected_output.startswith("INVALID") else run.stdout
            last = stream.strip().splitlines()[-1:] or [""]
            failures += report("cli", name, (last[0][:len(expected_output)], run.returncode),
                               (expected_output, expected_exit))
        signalled = os.path.join(directory, "signalled")
        config = write_config(os.path.join(root, ".claude"),
                              {"halt_criteria": [f"(sleep 1; touch '{signalled}') & wait"],
                               "monitoring_window_minutes": 1}, "project.json")
        watcher = subprocess.Popen([sys.executable, script, "--config", config,
                                    "--round-seconds", "30", "--budget-seconds", "25"],
                                   stdout=subprocess.PIPE, text=True)
        time.sleep(0.5)
        watcher.terminate()
        output = watcher.communicate()[0].strip()
        time.sleep(1)
        failures += report("cli", "a stopped watch halts and kills its criteria",
                           (output[:37], watcher.returncode, os.path.exists(signalled)),
                           ("HALT: the watch was stopped by signal", 1, False))
        orphan = os.path.join(directory, "orphan")
        watch([f"(sleep 1; touch '{orphan}') & wait"], 0, round_seconds=0.5,
              budget_seconds=0.4)
        time.sleep(2)
        failures += report("watch", "a halted criterion's children are killed",
                           os.path.exists(orphan), False)
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--config")
    # Shortened clocks for the self-test's command-line cases only.
    parser.add_argument("--round-seconds", type=float, default=ROUND_SECONDS,
                        help=argparse.SUPPRESS)
    parser.add_argument("--budget-seconds", type=float, default=BUDGET_SECONDS,
                        help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.config:
        parser.print_usage(sys.stderr)
        return 2
    if args.check:
        try:
            check(args.config)
        except ValueError as error:
            print(f"INVALID: {error}", file=sys.stderr)
            return 1
        print("ok")
        return 0
    try:
        criteria, window = load(args.config)
    except ValueError as error:
        print(f"HALT: {error}")
        return 1
    root = os.path.dirname(os.path.dirname(os.path.abspath(args.config)))
    verdict = watch(criteria, window, args.round_seconds, args.budget_seconds, cwd=root)
    print(verdict)
    return 0 if verdict == "window clean" else 1


if __name__ == "__main__":
    sys.exit(main())
