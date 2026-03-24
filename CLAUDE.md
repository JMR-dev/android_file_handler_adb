# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python GUI tool for managing Android device files via ADB (Android Debug Bridge). The application automatically downloads ADB platform-tools if needed, detects connected devices, and provides a Tkinter-based interface for transferring files between Android devices and local systems.

**Supported Platforms:** Windows, Linux (Debian, Arch, RHEL/Fedora)

## Development Setup

### Installation
```sh
poetry install
```

### Running the Application
```sh
poetry run python -m src.main
```

## Common Commands

### Testing
```sh

# Test if application runs
poetry run python -m src.main

# Run all tests
poetry run pytest tests/ -v

# Run tests with coverage
poetry run pytest tests/ -v --cov

# Run specific test file
poetry run pytest tests/core/test_adb_manager.py -v
```

### Code Quality
```sh
# Format code with Black
poetry run black src/ tests/

# Lint with flake8
poetry run flake8 src/ tests/

# Type checking with mypy
poetry run mypy src/
```

### Building and Packaging

#### Local Development Build (Linux)
```sh
# Interactive build (prompts for distro selection)
poetry run python scripts/build_package_linux.py
```

#### Prefect + Dagger Build (CI Pipeline Locally)
```sh
# Install CI dependencies
poetry install --with ci

# Build all Linux distros via Dagger containers
poetry run python -m ci.prefect_flow build-linux

# Sign artifacts
poetry run python -m ci.prefect_flow sign --gpg-passphrase "$GPG_PASSPHRASE"

# Full pipeline (build + sign + release)
poetry run python -m ci.prefect_flow full \
  --gpg-passphrase "$GPG_PASSPHRASE" \
  --github-token "$GITHUB_TOKEN"

# Upload artifacts to Cloudflare R2 (standalone)
poetry run python -m ci.prefect_flow upload-r2 \
  --gcp-project-id "$GCP_PROJECT_ID"
```

#### Podman Compose Build (Recommended for Linux)
```sh
# Build all distributions
podman-compose up --build

# Build specific distribution
podman-compose up --build debian
podman-compose up --build arch
podman-compose up --build rhel

# Clean build artifacts
podman-compose down -v && rm -rf dist pkg_dist_* dist_*
```

See [scripts/docker/README.md](scripts/docker/README.md) for detailed Docker build documentation.

#### Platform-Specific Builds
```sh
# Windows executable (PyInstaller)
poetry run pyinstaller scripts/spec_scripts/android-file-handler-windows.spec

# Windows installer (Inno Setup, after PyInstaller build)
# Inno Setup 6.7.1 is installed by the CI/CD workflow via Chocolatey (pinned version)
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" scripts\windows\android-file-handler-setup.iss /DMyAppVersion=0.1.1

# Linux packages use distro-specific spec files:
# - android-file-handler-debian.spec
# - android-file-handler-arch.spec
# - android-file-handler-rhel.spec
```

## Architecture

### Directory Structure

- **src/core/**: Core ADB functionality
  - `adb_manager.py`: Main ADB interface and operations coordinator
  - `adb_command.py`: Command execution wrapper
  - `file_transfer.py`: File transfer logic
  - `platform_tools.py`: ADB binary management and download
  - `platform_utils.py`: Platform detection utilities
  - `progress_tracker.py`: Transfer progress tracking

- **src/gui/**: GUI components
  - `main_window.py`: Main application window (entry point for GUI)
  - `components/`: Reusable UI widgets (file browser, path selectors, etc.)
  - `handlers/`: Event and animation handlers
  - `dialogs/`: Dialog windows (license agreement, device instructions, etc.)

- **src/managers/**: Business logic coordination
  - `device_manager.py`: Device detection and management
  - `transfer_manager.py`: Coordinates transfers between GUI and ADB manager

- **src/utils/**: Utility modules
  - `file_deduplication.py`: File deduplication logic

- **scripts/**: Build and packaging scripts
  - `build_package_linux.py`: Unified Linux packaging script (uses DISTRO_TYPE env var)
  - `spec_scripts/`: PyInstaller spec files for each platform
  - `windows/android-file-handler-setup.iss`: Inno Setup installer configuration

- **ci/**: CI/CD pipeline orchestration
  - `config.py`: Shared build configuration (distro configs, image references)
  - `dagger_pipeline.py`: Dagger container build definitions for Linux
  - `prefect_flow.py`: Prefect flow orchestration and CLI entry point
  - `signing.py`: GPG signing and SHA-256 hashing utilities

- **tests/**: Test suite mirroring src/ structure

### Application Flow

1. **Startup**: `src/main.py` → License check → `gui/main_window.py:main()`
2. **ADB Setup**: ADBManager checks for platform-tools, downloads if needed
3. **Device Detection**: DeviceManager checks for connected devices
4. **File Transfer**: TransferManager coordinates UI updates with ADB file operations

### Key Patterns

- **Import Fallbacks**: Most modules use try/except for relative vs. direct imports to support both module and direct execution
- **Manager Pattern**: Business logic separated into DeviceManager, TransferManager, ADBManager
- **Component Composition**: GUI built from reusable components in `gui/components/`
- **Threading**: File transfers run in background threads; UI updates via callbacks

## CI/CD

The project uses a **Prefect + Dagger** pipeline wrapped by GitHub Actions (`.github/workflows/release-prefect-dagger.yml`):

- **Dagger** runs containerized Linux builds (Debian, Arch, RHEL) using pre-built builder images
- **Prefect** orchestrates the pipeline: build → sign → release → R2 upload
- **GitHub Actions** provides the runner infrastructure and Windows build (cannot containerize)
- **Podman** is the container runtime (Dagger connects via Podman socket)

Pipeline structure:
1. `build-windows` — Native Windows build on `windows-latest`
2. `build-linux` — All Linux distros built in parallel via Prefect + Dagger
3. `do-release` — Creates GitHub release with all artifacts
4. `upload-r2` — Uploads artifacts to Cloudflare R2 (credentials from GCP Secrets Manager)
5. `sync-wiki` — Wiki synchronization

The CI pipeline modules live in `ci/`:
- `ci/config.py` — Shared build configuration
- `ci/dagger_pipeline.py` — Dagger container build definitions
- `ci/prefect_flow.py` — Prefect flow orchestration and CLI
- `ci/r2_upload.py` — Cloudflare R2 upload with GCP Secrets Manager integration
- `ci/signing.py` — GPG signing and SHA-256 hashing utilities

## Coding Standards

- Follow PEP 8 guidelines
- Use type hints for all function parameters and return values
- Write docstrings for all public modules, functions, and classes
- Use f-strings for string formatting
- No single-letter variable names except `e` for exceptions
- Always run Python commands through Poetry
- Do not recreate deleted files
- Do not change user-facing text unless asked
- Always run the application to test if it will run and have it run successfully before declaring an iteration complete
- Never use the squash merge strategy unless specifically instructed to do so

## Notes

- **ADB Binaries**: Stored in `src/platform-tools/` - do not modify or delete unless explictly instructed to
- **Python Version**: Requires Python 3.13 (< 3.14)
- **Package Mode**: Poetry is configured with `package-mode = false`
- **License**: First-run license agreement required on Windows
