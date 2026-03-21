"""Dagger pipeline for building Linux distribution packages.

Uses the Dagger Python SDK to run containerized builds for each
Linux distribution (Debian, Arch, RHEL) starting from base OS images,
downloading and compiling Python from source with SHA256 verification,
and building the application packages.
"""

# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownParameterType=false

import asyncio
import os
import sys
from pathlib import Path

import dagger  # type: ignore[import-not-found]

from ci.config import DistroConfig, PipelineConfig


def _get_registry_token() -> str | None:
    """Read GHCR token from GITHUB_TOKEN or GHCR_TOKEN environment variable."""
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GHCR_TOKEN")


def _get_system_deps_cmd(distro_type: str) -> list[str]:
    """Get the shell command to install system build dependencies.

    Args:
        distro_type: One of 'debian', 'arch', 'rhel'.

    Returns:
        Shell command as list for with_exec.
    """
    if distro_type == "debian":
        return [
            "sh",
            "-c",
            "apt-get update && apt-get install -y --no-install-recommends "
            "curl git build-essential ruby ruby-dev gcc make "
            "zlib1g-dev ca-certificates tcl-dev tk-dev "
            "libx11-6 libxext6 libxrender1 libxcb1 "
            "libbz2-dev libreadline-dev libsqlite3-dev libssl-dev libffi-dev "
            "wget tar liblzma-dev patch && "
            "apt-get clean && rm -rf /var/lib/apt/lists/*",
        ]
    elif distro_type == "arch":
        return [
            "sh",
            "-c",
            "pacman -Syu --noconfirm "
            "ruby ruby-bundler ruby-rake base-devel curl git tar "
            "ca-certificates ca-certificates-utils "
            "tk tcl libx11 libxext libxrender libxcb "
            "gcc make zlib bzip2 readline sqlite openssl libffi "
            "wget xz patch && "
            "update-ca-trust && pacman -Scc --noconfirm",
        ]
    elif distro_type == "rhel":
        return [
            "sh",
            "-c",
            "dnf -y update && dnf -y install "
            "gcc make zlib-devel bzip2 bzip2-devel readline-devel "
            "sqlite-devel openssl-devel libffi-devel wget tar git curl "
            "ruby rubygems rpm-build redhat-rpm-config gcc-c++ patch which "
            "xz-devel tk-devel tcl-devel libX11-devel libXext-devel "
            "libXrender-devel && dnf clean all",
        ]
    raise ValueError(f"Unknown distro type: {distro_type}")


def _get_python_configure_env(distro_type: str) -> str:
    """Get distro-specific LDFLAGS and CPPFLAGS for Python configure.

    Args:
        distro_type: One of 'debian', 'arch', 'rhel'.

    Returns:
        String with environment variable exports for the configure step.
    """
    if distro_type == "debian":
        return 'LDFLAGS="-L/usr/lib/x86_64-linux-gnu" CPPFLAGS="-I/usr/include/tcl8.6"'
    elif distro_type == "arch":
        return 'LDFLAGS="-L/usr/lib" CPPFLAGS="-I/usr/include"'
    elif distro_type == "rhel":
        return 'LDFLAGS="-L/usr/lib64" CPPFLAGS="-I/usr/include"'
    return ""


def _install_fpm(
    container: dagger.Container,
    distro_type: str,
    fpm_version: str,
) -> dagger.Container:
    """Install fpm (Effing Package Management) in the container.

    Args:
        container: Dagger container to install fpm in.
        distro_type: One of 'debian', 'arch', 'rhel'.
        fpm_version: Version of fpm to install.

    Returns:
        Container with fpm installed.
    """
    if distro_type == "arch":
        container = container.with_exec(
            ["gem", "install", "--no-document", "erb"]
        ).with_exec(
            [
                "sh",
                "-c",
                f'gem install --no-document -v "{fpm_version}" fpm && '
                "GEM_BIN_DIR=$(ruby -e 'puts Gem.user_dir')/bin && "
                'ln -sf "${GEM_BIN_DIR}/fpm" /usr/local/bin/fpm',
            ]
        )
    else:
        container = container.with_exec(
            ["gem", "install", "--no-document", "-v", fpm_version, "fpm"]
        )
    return container


async def build_linux_distro(
    client: dagger.Client,
    config: PipelineConfig,
    distro: DistroConfig,
    registry_token: str | None = None,
) -> dict[str, Path]:
    """Build a single Linux distribution package inside a Dagger container.

    Starts from a base OS image, compiles Python from source with SHA256
    verification, installs build tools (Poetry, fpm), and builds the package.

    Args:
        client: Active Dagger client connection.
        config: Pipeline configuration.
        distro: Distribution-specific build configuration.
        registry_token: Optional registry auth token.

    Returns:
        Dictionary mapping artifact names to their local output paths.
    """
    print(f"[dagger] Starting {distro.name} build using {distro.container_image}")

    source = client.host().directory(
        str(config.project_root),
        exclude=[".venv", "__pycache__", "dist", "dist_*", "pkg_dist_*", ".git"],
    )

    python = config.python_build
    configure_env = _get_python_configure_env(distro.distro_type)

    base = client.container()
    if registry_token:
        secret = client.set_secret("ghcr_token", registry_token)
        base = base.with_registry_auth("ghcr.io", "_token", secret)

    # Start from base image and install system dependencies
    container = base.from_(distro.container_image).with_exec(
        _get_system_deps_cmd(distro.distro_type)
    )

    # Download Python source and verify SHA256 against python.org
    print(f"[dagger] Downloading Python {python.version} and verifying SHA256")
    container = container.with_exec(
        ["wget", "-q", python.source_url, "-O", f"/tmp/Python-{python.version}.tgz"]
    ).with_exec(
        [
            "sh",
            "-c",
            f'echo "{python.sha256}  /tmp/Python-{python.version}.tgz" '
            f"| sha256sum -c -",
        ]
    )

    # Build and install Python from source
    print(f"[dagger] Compiling Python {python.version} from source")
    container = (
        container.with_exec(
            ["tar", "xzf", f"/tmp/Python-{python.version}.tgz", "-C", "/tmp"]
        )
        .with_exec(
            [
                "sh",
                "-c",
                f"cd /tmp/Python-{python.version} && "
                f"{configure_env} ./configure --enable-shared "
                f"--with-ensurepip=install --prefix=/usr/local && "
                f"make -j$(nproc) && "
                f"make install",
            ]
        )
        .with_exec(
            [
                "sh",
                "-c",
                'echo "/usr/local/lib" > /etc/ld.so.conf.d/python.conf && ldconfig',
            ]
        )
        .with_exec(["ln", "-sf", "/usr/local/bin/python3", "/usr/local/bin/python"])
        .with_exec(
            [
                "sh",
                "-c",
                f"rm -rf /tmp/Python-{python.version} "
                f"/tmp/Python-{python.version}.tgz",
            ]
        )
        .with_exec(
            [
                "python3",
                "-c",
                "import tkinter; import _tkinter; print('tkinter support verified')",
            ]
        )
    )

    # Install Poetry
    container = (
        container.with_exec(
            [
                "sh",
                "-c",
                "curl -sSL https://install.python-poetry.org | python3 - --yes",
            ]
        )
        .with_env_variable(
            "PATH", "/root/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        )
        .with_exec(["poetry", "--version"])
    )

    # Install fpm
    container = _install_fpm(container, distro.distro_type, config.fpm_version)

    # Mount workspace and run build
    container = (
        container.with_directory("/workspace", source)
        .with_workdir("/workspace")
        .with_env_variable("CI_CD", "true")
        .with_env_variable("DISTRO_TYPE", distro.distro_type)
        .with_env_variable("FPM_VERSION", config.fpm_version)
        .with_env_variable("POETRY_VIRTUALENVS_IN_PROJECT", "false")
        .with_env_variable("POETRY_VIRTUALENVS_PATH", "/tmp/poetry-cache")
        .with_exec(["poetry", "install", "--no-interaction"])
        .with_exec(["poetry", "run", "python", "scripts/build_package_linux.py"])
    )

    # Export build artifacts back to host
    dist_output = config.project_root / "dist"
    pkg_dist_output = config.project_root / f"pkg_dist_{distro.distro_type}"

    await container.directory("/workspace/dist").export(str(dist_output))
    await container.directory(f"/workspace/pkg_dist_{distro.distro_type}").export(
        str(pkg_dist_output)
    )

    print(
        f"[dagger] {distro.name} build complete — artifacts exported to {dist_output}"
    )

    return {
        "dist": dist_output,
        "pkg_dist": pkg_dist_output,
    }


async def build_all_linux(
    config: PipelineConfig | None = None,
) -> dict[str, dict[str, Path]]:
    """Build all Linux distribution packages in parallel via Dagger.

    Args:
        config: Pipeline configuration. Uses defaults if not provided.

    Returns:
        Dictionary mapping distro names to their artifact paths.
    """
    if config is None:
        config = PipelineConfig()

    results: dict[str, dict[str, Path]] = {}

    token = _get_registry_token()

    async with dagger.Connection(dagger.Config(log_output=sys.stderr)) as client:
        tasks = {
            distro.distro_type: build_linux_distro(
                client, config, distro, registry_token=token
            )
            for distro in config.distros
        }

        # Run all distro builds concurrently
        completed = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for distro_type, result in zip(tasks.keys(), completed):
            if isinstance(result, Exception):
                print(f"[dagger] ERROR: {distro_type} build failed: {result}")
                raise result
            results[distro_type] = result  # type: ignore[assignment]

    return results


async def build_single_linux(
    distro_type: str, config: PipelineConfig | None = None
) -> dict[str, Path]:
    """Build a single Linux distribution package.

    Args:
        distro_type: One of 'debian', 'arch', 'rhel'.
        config: Pipeline configuration. Uses defaults if not provided.

    Returns:
        Dictionary of artifact paths for the built distro.
    """
    if config is None:
        config = PipelineConfig()

    distro = next((d for d in config.distros if d.distro_type == distro_type), None)
    if distro is None:
        raise ValueError(
            f"Unknown distro type '{distro_type}'. Valid: debian, arch, rhel"
        )

    token = _get_registry_token()

    async with dagger.Connection(dagger.Config(log_output=sys.stderr)) as client:
        return await build_linux_distro(client, config, distro, registry_token=token)


if __name__ == "__main__":
    asyncio.run(build_all_linux())
