"""Dagger pipeline for building Linux distribution packages.

Uses the Dagger Python SDK to run containerized builds for each
Linux distribution (Debian, Arch, RHEL) using pre-built builder images.
"""
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownParameterType=false

import asyncio
import sys
from pathlib import Path

import dagger  # type: ignore[import-not-found]

from ci.config import DistroConfig, PipelineConfig


async def build_linux_distro(
    client: dagger.Client,
    config: PipelineConfig,
    distro: DistroConfig,
) -> dict[str, Path]:
    """Build a single Linux distribution package inside a Dagger container.

    Args:
        client: Active Dagger client connection.
        config: Pipeline configuration.
        distro: Distribution-specific build configuration.

    Returns:
        Dictionary mapping artifact names to their local output paths.
    """
    print(f"[dagger] Starting {distro.name} build using {distro.container_image}")

    # Mount the project source into the container, excluding local venv
    source = client.host().directory(
        str(config.project_root),
        exclude=[".venv", "__pycache__", "dist", "dist_*", "pkg_dist_*", ".git"],
    )

    container = (
        client.container()
        .from_(distro.container_image)
        .with_directory("/workspace", source)
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

    print(f"[dagger] {distro.name} build complete — artifacts exported to {dist_output}")

    return {
        "dist": dist_output,
        "pkg_dist": pkg_dist_output,
    }


async def build_all_linux(config: PipelineConfig | None = None) -> dict[str, dict[str, Path]]:
    """Build all Linux distribution packages in parallel via Dagger.

    Args:
        config: Pipeline configuration. Uses defaults if not provided.

    Returns:
        Dictionary mapping distro names to their artifact paths.
    """
    if config is None:
        config = PipelineConfig()

    results: dict[str, dict[str, Path]] = {}

    async with dagger.Connection(dagger.Config(log_output=sys.stderr)) as client:
        tasks = {
            distro.distro_type: build_linux_distro(client, config, distro)
            for distro in config.distros
        }

        # Run all distro builds concurrently
        completed = await asyncio.gather(
            *tasks.values(), return_exceptions=True
        )

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

    distro = next(
        (d for d in config.distros if d.distro_type == distro_type), None
    )
    if distro is None:
        raise ValueError(
            f"Unknown distro type '{distro_type}'. Valid: debian, arch, rhel"
        )

    async with dagger.Connection(dagger.Config(log_output=sys.stderr)) as client:
        return await build_linux_distro(client, config, distro)


if __name__ == "__main__":
    asyncio.run(build_all_linux())
