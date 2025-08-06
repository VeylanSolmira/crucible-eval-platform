# Contributing to Crucible Evaluation Platform

We're excited that you're interested in contributing to Crucible! This document provides guidelines for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:
- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Respect differing viewpoints and experiences

## How to Contribute

### Reporting Issues

1. **Check existing issues** - Before creating a new issue, please check if it already exists
2. **Use issue templates** - We provide templates for bug reports and feature requests
3. **Be specific** - Include:
   - Clear description of the issue
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - System information (OS, Python version, etc.)

### Suggesting Features

1. Open a feature request issue
2. Explain the use case and benefits
3. Consider implementation complexity
4. Be open to discussion and feedback

### Contributing Code

#### Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/crucible-eval-platform.git
   cd crucible-eval-platform
   ```
3. Set up your development environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements-dev.txt
   ```

#### Development Process

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following our coding standards:
   - Follow PEP 8 for Python code
   - Use TypeScript for frontend code
   - Write meaningful commit messages
   - Add tests for new functionality
   - Update documentation as needed

3. Run tests and linting:
   ```bash
   # Python linting and type checking
   ruff check .
   mypy src/
   
   # Run tests
   pytest tests/ -v
   
   # Frontend tests
   cd frontend && npm test
   ```

4. Commit your changes:
   ```bash
   git add .
   git commit -m "feat: add new feature X"
   ```

   We follow conventional commits:
   - `feat:` - New features
   - `fix:` - Bug fixes
   - `docs:` - Documentation changes
   - `style:` - Code style changes (formatting, etc.)
   - `refactor:` - Code refactoring
   - `test:` - Test additions or modifications
   - `chore:` - Build process or auxiliary tool changes

5. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

6. Create a Pull Request

#### Pull Request Guidelines

- **One feature per PR** - Keep PRs focused on a single feature or fix
- **Write a clear description** - Explain what changes you made and why
- **Reference issues** - Link to related issues using `Fixes #123`
- **Keep it small** - Smaller PRs are easier to review
- **Update tests** - Ensure all tests pass
- **Document changes** - Update relevant documentation

### Testing

- Write unit tests for new functionality
- Ensure integration tests pass
- Add e2e tests for user-facing features
- Aim for good test coverage

### Documentation

- Update README.md if needed
- Add docstrings to Python functions
- Document API changes in OpenAPI specs
- Update architecture docs for significant changes

## Project Structure

Key directories:
- `api/` - FastAPI backend service
- `frontend/` - React TypeScript dashboard
- `k8s/` - Kubernetes manifests
- `tests/` - Test suites
- `docs/` - Documentation

## Development Setup

See [DEVELOPMENT_ENVIRONMENT_CHECKLIST.md](DEVELOPMENT_ENVIRONMENT_CHECKLIST.md) for detailed setup instructions.

## Questions?

- Open a discussion in GitHub Discussions
- Ask in issues for specific problems
- Review existing documentation

## Recognition

Contributors will be recognized in our README.md file. Thank you for helping make Crucible better!

## License

By contributing to Crucible, you agree that your contributions will be licensed under the MIT License.