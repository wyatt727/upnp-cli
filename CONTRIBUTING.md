# Contributing to UPnP CLI

Thank you for your interest in contributing to the UPnP CLI project! This document provides guidelines and information for contributors.

## Code of Conduct

This project adheres to a code of conduct that promotes a welcoming and inclusive environment. Please be respectful and professional in all interactions.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- A UPnP-enabled device for testing (optional but recommended)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/upnp-cli/upnp-cli.git
   cd upnp-cli
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e .[dev]
   ```

4. **Install pre-commit hooks** (optional but recommended)
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Development Guidelines

### Code Style

- Follow PEP 8 style guidelines
- Use `black` for code formatting: `black upnp_cli/`
- Use `flake8` for linting: `flake8 upnp_cli/`
- Use `mypy` for type checking: `mypy upnp_cli/`

### Testing

- Write tests for all new functionality
- Use `pytest` for testing: `pytest tests/`
- Aim for >80% code coverage
- Include both unit tests and integration tests
- Mark slow tests with `@pytest.mark.slow`

### Documentation

- Update docstrings for all functions and classes
- Update README.md if adding new features
- Add entries to CHANGELOG.md for all changes
- Update ADR.md for architectural decisions

### Commit Messages

Use conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(discovery): add async SSDP discovery
fix(soap): handle timeout errors gracefully
docs(readme): update installation instructions
```

## What to Contribute

### High Priority Areas

1. **Core Module Implementation**
   - Configuration and logging infrastructure
   - Device discovery engine
   - SOAP client implementation
   - Cache management system

2. **Device Protocol Support**
   - Chromecast Cast protocol integration
   - Samsung WAM API implementation
   - Roku ECP client
   - Additional device profiles

3. **Testing and Quality**
   - Unit tests for existing modules
   - Integration tests with mock devices
   - Performance testing and optimization

### Device Profiles

We welcome contributions of device profiles for new manufacturers and models:

1. Create a new entry in `profiles/profiles.json`
2. Include manufacturer, model, and service information
3. Test with real devices when possible
4. Document any device-specific quirks

### Bug Reports

When reporting bugs, please include:
- Python version and operating system
- Complete error messages and stack traces
- Steps to reproduce the issue
- Network environment details (if relevant)

### Feature Requests

For new features:
- Check existing issues first
- Describe the use case and benefits
- Consider backward compatibility
- Be willing to help implement or test

## Development Workflow

### Adding a New Module

1. Create the module file in `upnp_cli/`
2. Add comprehensive docstrings and type hints
3. Write unit tests in `tests/`
4. Update `upnp_cli/__init__.py` if needed
5. Add to documentation and ADR if architectural

### Adding Device Support

1. Research the device's protocol and API
2. Add device profile to `profiles/profiles.json`
3. Implement protocol handler if needed
4. Write tests with mock responses
5. Update documentation with supported devices

### Submitting Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow coding standards
   - Add tests
   - Update documentation

3. **Run the test suite**
   ```bash
   pytest tests/
   black upnp_cli/
   flake8 upnp_cli/
   mypy upnp_cli/
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat(scope): description of changes"
   ```

5. **Push and create a pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Security Considerations

This tool is designed for authorized penetration testing and network administration. When contributing:

- Include appropriate warnings about authorized use
- Implement rate limiting and stealth options
- Consider the ethical implications of new features
- Report security vulnerabilities privately

## Getting Help

- **Documentation**: Check the README.md and docs/ directory
- **Issues**: Search existing GitHub issues
- **Discussions**: Use GitHub Discussions for questions
- **Chat**: Join our Discord/Slack (if available)

## Recognition

Contributors will be recognized in:
- CHANGELOG.md for their contributions
- README.md contributors section
- Release notes for significant contributions

Thank you for helping make UPnP CLI better! 