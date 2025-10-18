# Docker Build Environment

This directory contains Dockerfiles for building the Android File Handler on different Linux distributions. These images match exactly the images used in the CI/CD pipeline.

## Quick Start

### Using Docker Compose (Recommended)

Build for all distributions:
```bash
docker-compose up --build
```

Build for a specific distribution:
```bash
docker-compose up --build debian
docker-compose up --build arch
docker-compose up --build rhel
```

Build all distributions in parallel:
```bash
docker-compose up --build --parallel
```

### Manual Docker Build

Build the image:
```bash
# Debian
docker build -f scripts/docker/Dockerfile.debian -t android-file-handler-debian-builder .

# Arch
docker build -f scripts/docker/Dockerfile.arch -t android-file-handler-arch-builder .

# RHEL/Fedora
docker build -f scripts/docker/Dockerfile.rhel -t android-file-handler-rhel-builder .
```

Run the build:
```bash
# Debian
docker run --rm -v $(pwd):/workspace -w /workspace android-file-handler-debian-builder

# Arch
docker run --rm -v $(pwd):/workspace -w /workspace android-file-handler-arch-builder

# RHEL/Fedora
docker run --rm -v $(pwd):/workspace -w /workspace android-file-handler-rhel-builder
```

## Output

After building, you'll find:

- `dist/` - Final packaged files (.deb, .rpm, .pkg.tar.zst)
- `pkg_dist_{distro}/` - Staging directories for package contents
- `dist_{distro}/` - PyInstaller build outputs

## Images

### Debian Builder
- **Image**: `ghcr.io/jmr-dev/android-file-handler-debian-builder:debian13-trixie`
- **Base**: `debian:13`
- **Python**: 3.13 (via pyenv)
- **Tools**: Poetry, fpm, PyInstaller

### Arch Builder
- **Image**: `ghcr.io/jmr-dev/android-file-handler-arch-builder:latest`
- **Base**: `archlinux:latest`
- **Python**: 3.13 (via pyenv)
- **Tools**: Poetry, fpm, PyInstaller

### RHEL Builder
- **Image**: `ghcr.io/jmr-dev/android-file-handler-rhel-builder:fedora42`
- **Base**: `fedora:42`
- **Python**: 3.13 (via pyenv)
- **Tools**: Poetry, fpm, PyInstaller

## Troubleshooting

### Virtualenv Conflicts

The Docker Compose configuration automatically excludes the host's `.venv` directory to prevent conflicts between the host Python environment and the container Python environment. Each container creates its own virtualenv in `/tmp/poetry-cache`.

If you encounter virtualenv-related errors, ensure you're using the latest docker-compose.yml configuration.

## Cleaning Up

Remove build artifacts:
```bash
rm -rf dist pkg_dist_* dist_*
```

Remove Docker volumes and containers:
```bash
docker compose down -v
```

## Customization

### Override FPM Version

Build with a specific fpm version:
```bash
docker-compose build --build-arg FPM_VERSION=1.15.0 debian
```

### Environment Variables

All builds use these environment variables:
- `CI_CD=true` - Runs in CI/CD mode
- `DISTRO_TYPE` - Set to `debian`, `arch`, or `rhel`
- `FPM_VERSION` - Version of fpm to use (default: 1.16.0)

## Notes

- All images use Python 3.13 built from source with tkinter support
- The builds are identical to what runs in GitHub Actions
- Poetry and fpm are pre-installed in all images
- The Python build script handles both PyInstaller and fpm packaging
