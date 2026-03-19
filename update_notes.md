## terraform ##
```bash
terraform state replace-provider \
  "registry.terraform.io/-/aws" \
  "registry.terraform.io/hashicorp/aws"

terraform init -upgrade

```

## python ##
Successfully modernized the defenda-data-lake repository. 

**Pipenv → uv**: Replaced `Pipfile` with `pyproject.toml` using uv for dependency management. Deleted `Pipfile`, `Pipfile.lock`, `requirements.txt`, and `pytest.ini` (config moved to pyproject.toml).

**Python 3.8 → 3.13**: Updated all references — Terraform lambda runtimes, Dockerfile base image (now `public.ecr.aws/sam/build-python3.13`), and CI config. Also modernized `dates.py` to use stdlib `datetime.timezone` instead of `pytz` (which used `.localize()`/`.normalize()` methods incompatible with modern `zoneinfo`), and replaced deprecated `pynsive` plugin loader with a clean `importlib`+`pathlib` implementation (~same code, zero dependencies).

**Lambda build pipeline**: The Dockerfile now uses the official AWS SAM build image with `uv` for fast dependency installation. `generate_lambda_zip.py` no longer depends on pipenv. CI moved from Travis CI to GitHub Actions.

**Additional fixes**: Updated tests from `setup()` to `setup_method()` (required by pytest 9), fixed hardcoded file paths in tests to use `Path(__file__).parent`, removed unused imports (`__future__`, `pkg_resources`), and removed `pytz` dependency entirely. All 31 tests pass.
