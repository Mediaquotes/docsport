# Contributing to DocsPort

Thank you for your interest in contributing to DocsPort!

## How to Contribute

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/my-feature`)
3. **Commit** your changes (`git commit -m "Add my feature"`)
4. **Push** to your branch (`git push origin feature/my-feature`)
5. **Open** a Pull Request

## Development Setup

```bash
# Clone the repo
git clone https://github.com/mediaquotes/docsport.git
cd docsport

# Install dependencies
pip install -r requirements.txt

# Run the development server
python main.py
```

## Guidelines

- Follow existing code style and patterns
- Add docstrings to new functions and classes
- Test your changes before submitting
- Keep pull requests focused on a single change

## Adding Translations

DocsPort supports multilingual UI. To add a new language:

1. Create `frontend/locales/<lang>.json` (copy from `en.json`)
2. Create `backend/locales/<lang>.json` (copy from `en.json`)
3. Add the language option to `frontend/templates/index.html` in the locale switcher
4. Update `backend/i18n.py` to include the new language in the `supported` set

## Reporting Issues

Please use [GitHub Issues](https://github.com/mediaquotes/docsport/issues) to report bugs or request features.
