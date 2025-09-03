# Contributing to InjectQ

Thank you for your interest in contributing to InjectQ! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

There are many ways to contribute to InjectQ:

- **Bug Reports**: Report bugs and issues
- **Feature Requests**: Suggest new features and improvements
- **Documentation**: Improve documentation and examples
- **Code**: Submit bug fixes and new features
- **Testing**: Add tests and improve test coverage
- **Reviews**: Review pull requests and provide feedback

## 🐛 Reporting Issues

When reporting issues, please include:

1. **Clear Description**: Describe the issue clearly
2. **Reproduction Steps**: Provide minimal code to reproduce the issue
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Environment**: Python version, InjectQ version, OS, etc.

### Issue Template

```markdown
## Description
Brief description of the issue

## Reproduction
```python
# Minimal code to reproduce the issue
```

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- Python version: 
- InjectQ version: 
- Operating System: 
```

## 🚀 Setting Up Development Environment

### Prerequisites

- Python 3.8 or higher
- uv (recommended) or pip
- Git

### Setup Steps

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/injectq.git
   cd injectq
   ```

2. **Install Dependencies**
   ```bash
   # Using uv (recommended)
   uv sync --dev
   
   # Or using pip
   pip install -e .[dev]
   ```

3. **Install Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

4. **Run Tests**
   ```bash
   # Run all tests
   pytest
   
   # Run with coverage
   pytest --cov=injectq
   
   # Run specific test file
   pytest tests/test_container.py
   ```

5. **Run Linting**
   ```bash
   # Run all checks
   ruff check .
   
   # Auto-fix issues
   ruff check . --fix
   
   # Format code
   ruff format .
   ```

## 🏗️ Development Workflow

### Branch Strategy

- `main`: Stable release branch
- `develop`: Development branch
- `feature/*`: Feature branches
- `bugfix/*`: Bug fix branches
- `hotfix/*`: Critical hotfix branches

### Workflow Steps

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write code following our style guidelines
   - Add tests for new functionality
   - Update documentation if needed

3. **Run Tests**
   ```bash
   pytest
   ruff check .
   mypy injectq
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

## 📝 Code Style Guidelines

### Python Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

- **Line Length**: 88 characters
- **Import Sorting**: isort-compatible
- **Formatting**: Black-compatible
- **Type Hints**: Required for all public APIs

### Docstring Style

We use Google-style docstrings:

```python
def example_function(param1: str, param2: int) -> bool:
    """Example function with proper docstring.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param1 is empty
        
    Example:
        >>> example_function("test", 42)
        True
    """
    if not param1:
        raise ValueError("param1 cannot be empty")
    return len(param1) == param2
```

### Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding or fixing tests
- `chore`: Maintenance tasks

Examples:
```
feat: add async dependency resolution
fix(container): resolve circular dependency issue
docs: update getting started guide
test: add tests for scoped services
```

## 🧪 Testing Guidelines

### Test Structure

```
tests/
├── test_container.py          # Container functionality
├── test_scopes.py            # Scoping tests
├── test_modules.py           # Module system tests
├── test_integrations/        # Framework integrations
│   ├── test_fastapi.py
│   └── test_taskiq.py
└── fixtures/                 # Test fixtures
    └── conftest.py
```

### Writing Tests

1. **Test Files**: Match source file names with `test_` prefix
2. **Test Classes**: Group related tests in classes
3. **Test Methods**: Use descriptive names starting with `test_`
4. **Fixtures**: Use pytest fixtures for setup/teardown
5. **Mocking**: Use unittest.mock or pytest-mock

Example test:

```python
import pytest
from injectq import InjectQ, inject

class TestContainer:
    def test_simple_registration(self):
        """Test simple service registration."""
        container = InjectQ()
        container[str] = "test"
        
        assert container[str] == "test"
    
    def test_dependency_injection(self):
        """Test automatic dependency injection."""
        container = InjectQ()
        container[str] = "hello"
        
        @inject
        def func(message: str) -> str:
            return f"Got: {message}"
        
        result = func()
        assert result == "Got: hello"
    
    @pytest.mark.asyncio
    async def test_async_injection(self):
        """Test async dependency injection."""
        container = InjectQ()
        container[str] = "async"
        
        @inject
        async def async_func(message: str) -> str:
            return f"Async: {message}"
        
        result = await async_func()
        assert result == "Async: async"
```

### Test Coverage

- **Minimum Coverage**: 95%
- **Missing Coverage**: Should be documented
- **Test Types**: Unit, integration, and end-to-end tests

## 📚 Documentation Guidelines

### Documentation Structure

Documentation is written in Markdown and built with MkDocs:

```
docs/
├── index.md                  # Home page
├── getting-started/          # Installation and quick start
├── core-concepts/           # Fundamental concepts
├── injection-patterns/      # Different injection styles
├── scopes/                  # Service lifetimes
├── modules/                 # Module system
├── integrations/            # Framework integrations
├── testing/                 # Testing utilities
├── advanced/                # Advanced features
├── examples/                # Examples and patterns
├── best-practices/          # Best practices
├── api-reference/           # API documentation
└── migration/               # Migration guides
```

### Writing Documentation

1. **Tutorial Style**: Documentation should be tutorial-oriented
2. **Code Examples**: Include working code examples
3. **Clear Headings**: Use descriptive headings and subheadings
4. **Cross-references**: Link to related sections
5. **Up-to-date**: Keep examples current with latest API

### Building Documentation

```bash
# Install documentation dependencies
pip install -e .[docs]

# Serve documentation locally
mkdocs serve

# Build documentation
mkdocs build
```

## 🔄 Pull Request Process

### Before Submitting

1. **Tests Pass**: All tests must pass
2. **Linting Clean**: No linting errors
3. **Coverage**: Maintain or improve test coverage
4. **Documentation**: Update docs if needed
5. **Changelog**: Add entry to changelog

### PR Requirements

- **Clear Title**: Descriptive title following commit convention
- **Description**: Explain what the PR does and why
- **Issue Reference**: Link to related issues
- **Testing**: Describe how the change was tested
- **Breaking Changes**: Clearly mark breaking changes

### PR Template

```markdown
## Description
Brief description of the changes

## Changes
- List of changes
- Another change

## Testing
How the changes were tested

## Checklist
- [ ] Tests pass
- [ ] Linting clean
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Breaking changes noted
```

### Review Process

1. **Automated Checks**: CI must pass
2. **Code Review**: At least one maintainer review
3. **Discussion**: Address feedback and questions
4. **Approval**: Maintainer approval required
5. **Merge**: Squash and merge to main

## 🏷️ Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Steps

1. **Update Version**: Update version in `pyproject.toml`
2. **Update Changelog**: Add release notes
3. **Create Release**: Tag and create GitHub release
4. **Publish**: Publish to PyPI
5. **Documentation**: Update documentation

## 📋 Code Review Guidelines

### For Contributors

- **Self Review**: Review your own code before submitting
- **Small PRs**: Keep changes focused and small
- **Context**: Provide context and explanation
- **Responsive**: Respond to feedback promptly

### For Reviewers

- **Be Kind**: Provide constructive feedback
- **Be Thorough**: Check code, tests, and documentation
- **Be Timely**: Review PRs in reasonable time
- **Be Clear**: Explain suggestions and concerns

## 🆘 Getting Help

- **GitHub Issues**: Ask questions in issues
- **Discussions**: Use GitHub Discussions for general questions
- **Documentation**: Check documentation first
- **Examples**: Look at example code

## 🎉 Recognition

Contributors are recognized in:

- **Changelog**: Major contributions noted
- **Documentation**: Contributors acknowledged
- **Releases**: Contributions highlighted

Thank you for contributing to InjectQ! 🚀
