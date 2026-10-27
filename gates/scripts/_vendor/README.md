# Vendored YAML parser

`skills/maintenance-review/scripts/maintenance_check.py` reads Prometheus alerting rules
with PyYAML's pure-Python package, so it needs nothing installed. `yaml/` is the sdist's
`lib/yaml` directory, copied unmodified, with the sdist's `LICENSE` beside it. Every read goes
through `project_rules.depth_capped_loader()`, a `SafeLoader` capped at a fixed nesting depth,
which constructs no arbitrary Python object; without the
`_yaml` C extension, `yaml/cyaml.py`'s import fails and is skipped, as PyYAML intends.

| Package | Version | License | sdist SHA-256 |
| --- | --- | --- | --- |
| PyYAML | 6.0.3 | MIT (`yaml/LICENSE`) | `d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f` |

To upgrade, download the sdist with `pip download --no-deps --no-binary :all: PyYAML`, check
its hash against PyPI, replace `yaml/` with its `lib/yaml` and `LICENSE`, and run
`bash scripts/ci/all.sh`: `maintenance_check.py --self-test` fails on a release that needs
a newer Python grammar or a package beyond the standard library.
