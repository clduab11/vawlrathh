# arena-improver

Hackathon submission for LiquidMetal/Raindrop submission.

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
[![Security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Pre-commit: enabled](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://pre-commit.com/)

## Table of Contents

- [Overview](#overview)
- [Requirements](#requirements)
- [Installation](#installation)
- [Development Setup](#development-setup)
- [Code Quality](#code-quality)
- [Testing](#testing)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Overview

This project follows modern Python best practices as of November 2025, including:

- **Modern Dependency Management**: Using `pyproject.toml` (PEP 621) with pinned versions
- **Code Quality Tools**: Ruff (linter & formatter), MyPy (type checking), Bandit (security)
- **Automated Workflows**: Pre-commit hooks for consistent code quality
- **Comprehensive Testing**: Pytest with coverage reporting
- **Security First**: Regular dependency audits and secrets detection
- **Editor Integration**: EditorConfig for consistent coding styles

## Requirements

- **Python**: 3.11 or higher
- **pip**: Latest version recommended
- **Git**: For version control and pre-commit hooks

## Installation

### Quick Start

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/arena-improver.git
   cd arena-improver
   ```

2. Create and activate a virtual environment:

   ```bash
   # Using venv (built-in)
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate

   # Or using pyenv
   pyenv virtualenv 3.11.10 arena-improver
   pyenv local arena-improver
   ```

3. Install production dependencies:

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

## Development Setup

### Install Development Dependencies

```bash
# Option 1: Using requirements files
pip install -r requirements.txt -r requirements-dev.txt

# Option 2: Using pyproject.toml (recommended)
pip install -e ".[dev]"

# Option 3: Using Makefile (easiest)
make dev
```

### Setup Pre-commit Hooks

Pre-commit hooks automatically run code quality checks before each commit:

```bash
# Install hooks
pre-commit install
pre-commit install --hook-type commit-msg

# Or using Makefile
make hooks

# Run manually on all files
pre-commit run --all-files
```

### Available Development Tools

| Tool         | Purpose                       | Command                  |
| ------------ | ----------------------------- | ------------------------ |
| **Ruff**     | Fast linting & formatting     | `ruff check .`           |
| **MyPy**     | Static type checking          | `mypy .`                 |
| **Pytest**   | Testing framework             | `pytest`                 |
| **Bandit**   | Security vulnerability scan   | `bandit -r .`            |
| **Pip-audit** | Dependency vulnerability scan | `pip-audit`              |
| **Black**    | Code formatter                | `black .`                |
| **isort**    | Import statement organizer    | `isort .`                |
| **Coverage** | Code coverage measurement     | `pytest --cov=.`         |

## Code Quality

### Automated Checks

All code quality checks are automated through pre-commit hooks and can be run manually:

```bash
# Run all checks (recommended before committing)
make check

# Individual checks
make lint           # Run all linters
make type-check     # Run type checking
make security       # Run security scans
make format         # Format code
```

### Code Style

This project follows:

- **PEP 8**: Python style guide
- **PEP 484**: Type hints
- **PEP 257**: Docstring conventions
- **Ruff**: Fast linting and formatting (100 character line length)
- **Black-compatible**: Code formatting

### Type Checking

All code should include type hints:

```python
def example_function(name: str, count: int) -> list[str]:
    """Example of proper type hints."""
    return [name] * count
```

Run type checking:

```bash
mypy .
# Or
make type-check
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=arena_improver --cov-report=html

# Run specific test file
pytest tests/test_example.py

# Run tests in parallel (faster)
pytest -n auto

# Or using Makefile
make test                # Basic test run
make test-coverage       # With coverage report
make test-fast          # Parallel execution
```

### Test Structure

```
tests/
├── unit/              # Unit tests
├── integration/       # Integration tests
├── conftest.py        # Pytest configuration
└── fixtures/          # Test fixtures
```

### Writing Tests

```python
import pytest

def test_example():
    """Example test with docstring."""
    assert 1 + 1 == 2

@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
])
def test_parameterized(input: int, expected: int):
    """Example of parameterized test."""
    assert input * 2 == expected
```

## Documentation

### Building Documentation

```bash
# Using Sphinx
cd docs
make html
python -m http.server 8000 --directory _build/html

# Using MkDocs
mkdocs serve

# Or using Makefile
make docs           # Build docs
make docs-serve     # Serve locally
```

## Dependency Management

### Philosophy

This project follows November 2025 best practices for Python dependency management:

1. **Pinned Versions**: All dependencies have exact versions for reproducibility
2. **Separate Dev Dependencies**: Development tools isolated from production
3. **Regular Updates**: Dependencies are reviewed and updated regularly
4. **Security First**: Regular vulnerability scans using pip-audit and safety
5. **Modern Tools**: Support for pip-tools, uv, poetry, and pdm

### Managing Dependencies

#### Adding New Dependencies

```bash
# For production dependencies
echo "package-name==1.0.0" >> requirements.txt
pip install -r requirements.txt

# For development dependencies
echo "package-name==1.0.0" >> requirements-dev.txt
pip install -r requirements-dev.txt
```

#### Updating Dependencies

```bash
# Using pip-tools (recommended)
pip-compile --upgrade requirements.in

# Using pip directly (be cautious)
pip install --upgrade package-name

# Check for outdated packages
pip list --outdated
```

#### Security Audits

```bash
# Scan for known vulnerabilities
pip-audit

# Alternative security scanner
safety check

# Or using Makefile
make security
make deps-audit
```

### Alternative Dependency Managers

This project supports modern Python dependency managers:

#### Using uv (Ultra-fast installer)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv pip install -r requirements.txt
```

#### Using Poetry

```bash
# Convert to Poetry
poetry init
poetry add $(cat requirements.txt)
```

#### Using PDM

```bash
# Convert to PDM
pdm init
pdm add $(cat requirements.txt)
```

## Project Structure

```
arena-improver/
├── .editorconfig              # Editor configuration
├── .gitignore                 # Git ignore patterns
├── .pre-commit-config.yaml    # Pre-commit hooks configuration
├── .python-version            # Python version for pyenv
├── .secrets.baseline          # Secrets detection baseline
├── .yamllint.yaml             # YAML linting configuration
├── LICENSE                    # AGPLv3 license
├── Makefile                   # Development commands
├── README.md                  # This file
├── pyproject.toml             # Project configuration (PEP 621)
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
├── arena_improver/            # Main package (to be created)
│   ├── __init__.py
│   └── ...
└── tests/                     # Test suite (to be created)
    ├── __init__.py
    └── ...
```

## Makefile Commands

The project includes a comprehensive Makefile for common tasks:

| Command               | Description                              |
| --------------------- | ---------------------------------------- |
| `make help`           | Show all available commands              |
| `make install`        | Install production dependencies          |
| `make dev`            | Install development dependencies         |
| `make hooks`          | Install pre-commit hooks                 |
| `make lint`           | Run all linters                          |
| `make format`         | Format code                              |
| `make type-check`     | Run type checking                        |
| `make security`       | Run security checks                      |
| `make test`           | Run tests                                |
| `make test-coverage`  | Run tests with coverage                  |
| `make check`          | Run all checks (lint + type + test)      |
| `make ci`             | Run full CI pipeline locally             |
| `make clean`          | Clean build artifacts and cache          |
| `make deps-audit`     | Audit dependencies for vulnerabilities   |

Run `make help` to see all available commands.

## Contributing

### Development Workflow

1. **Create a feature branch**:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** with proper type hints and tests

3. **Run quality checks**:

   ```bash
   make check
   ```

4. **Commit using conventional commits**:

   ```bash
   git commit -m "feat: add new feature"
   ```

   Commit types:

   - `feat`: New feature
   - `fix`: Bug fix
   - `docs`: Documentation changes
   - `style`: Code style changes (formatting, etc.)
   - `refactor`: Code refactoring
   - `test`: Test changes
   - `chore`: Build process or auxiliary tool changes

5. **Push and create a pull request**:
   ```bash
   git push origin feature/your-feature-name
   ```

### Code Review Checklist

- [ ] Code follows project style (Ruff + Black)
- [ ] All tests pass
- [ ] Type hints are included
- [ ] Documentation is updated
- [ ] Security checks pass
- [ ] No new vulnerabilities introduced
- [ ] Pre-commit hooks pass

## CI/CD Integration

This project is configured for easy CI/CD integration. Example configurations:

### GitHub Actions

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: make dev
      - run: make ci
```

### GitLab CI

```yaml
test:
  image: python:3.11
  script:
    - make dev
    - make ci
```

## Troubleshooting

### Common Issues

**Import errors after installation**:

```bash
pip install -e .
```

**Pre-commit hooks failing**:

```bash
pre-commit clean
pre-commit install
pre-commit run --all-files
```

**Type checking errors**:

```bash
mypy --install-types
```

**Dependency conflicts**:

```bash
pip install --force-reinstall -r requirements.txt
```

## Resources

- [PEP 8 - Style Guide](https://peps.python.org/pep-0008/)
- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [PEP 621 - Project Metadata](https://peps.python.org/pep-0621/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Pytest Documentation](https://docs.pytest.org/)

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).
See [LICENSE](LICENSE) file for details.

## Contact

For questions or issues, please open an issue on the GitHub repository.

---

**Last Updated**: 2025-11-11
**Python Version**: 3.11+
**Maintained by**: Arena Improver Team
