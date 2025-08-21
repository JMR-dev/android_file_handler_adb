# Project Overview

This is a small Python GUI tool for managing Android device files via ADB (Android Debug Bridge).
## Folder Structure

- `/src`: Contains the source code for the application.
    - `platform-tools/`: Directory where ADB binaries are stored. Do not modify or delete this folder.
- .github: Contains GitHub-related files, including workflows and issue templates.
    - `copilot-instructions.md`: Instructions for GitHub Copilot to assist in code generation. Do not touch this file.

## Libraries and Frameworks

- Tkinter for the GUI.
- Requests for HTTP requests.
- Zipfile for handling zip archives.
- Poetry for package management.

## Coding Standards

- Follow PEP 8 guidelines for Python code.
- Use meaningful variable and function names.
- Write docstrings for all public modules, functions, and classes.
- Include type hints for all function parameters and return values.
- Use f-strings for string formatting.
- No single letter variable names except for `e` when appropriate.

## UI guidelines

- Application should have a modern and clean design.

## Runtime Instructions
- Always run Python commands through Poetry to ensure the correct environment is used.
- Use `poetry run python src/main.py` to start the application.