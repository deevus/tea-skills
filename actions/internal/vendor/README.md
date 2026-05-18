# Vendored dependencies

This directory contains third-party Python modules used by bundled actions without requiring plugin users to install Python packages separately.

## `yaml` (PyYAML)

- Source: https://github.com/yaml/pyyaml
- Vendored from commit: `d51d8a138f7230834fc6e95635ff09ebd329185f`
- License: MIT (`yaml/LICENSE`)
- Vendored subset: `lib/yaml/`

The bundled actions use `yaml.safe_load()` for tea config parsing.
