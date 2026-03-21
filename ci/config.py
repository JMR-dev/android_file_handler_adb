"""Shared configuration for CI/CD pipeline."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class PythonBuildConfig:
    """Configuration for building Python from source."""

    version: str = "3.14.3"
    source_url: str = "https://www.python.org/ftp/python/3.14.3/Python-3.14.3.tgz"
    sha256: str = "d7fe130d0501ae047ca318fa92aa642603ab6f217901015a1df6ce650d5470cd"


@dataclass(frozen=True)
class DistroConfig:
    """Configuration for a Linux distribution build."""

    name: str
    distro_type: str
    container_image: str
    bin_path: str
    pkg_type: str
    architecture: str
    postinstall: str | None = None


@dataclass(frozen=True)
class PipelineConfig:
    """Top-level pipeline configuration."""

    fpm_version: str = "1.16.0"
    project_root: Path = field(
        default_factory=lambda: Path(__file__).parent.parent.resolve()
    )
    python_build: PythonBuildConfig = field(default_factory=PythonBuildConfig)

    # Base container images (Python and tools are installed by the pipeline)
    debian_image: str = "debian:13"
    arch_image: str = "archlinux:latest"
    rhel_image: str = "fedora:42"

    @property
    def distros(self) -> list[DistroConfig]:
        """Return all Linux distribution build configurations."""
        return [
            DistroConfig(
                name="Debian",
                distro_type="debian",
                container_image=self.debian_image,
                bin_path="usr/local/bin",
                pkg_type="deb",
                architecture="amd64",
                postinstall="scripts/debian_postinst.sh",
            ),
            DistroConfig(
                name="Arch",
                distro_type="arch",
                container_image=self.arch_image,
                bin_path="usr/bin",
                pkg_type="pacman",
                architecture="x86_64",
                postinstall=None,
            ),
            DistroConfig(
                name="RHEL",
                distro_type="rhel",
                container_image=self.rhel_image,
                bin_path="usr/bin",
                pkg_type="rpm",
                architecture="x86_64",
                postinstall="scripts/rhel_postinst.sh",
            ),
        ]

    # Artifact patterns for each distro
    artifact_patterns: dict[str, list[str]] = field(
        default_factory=lambda: {
            "debian": ["dist/android-file-handler_*.deb"],
            "arch": ["dist/android-file-handler-*.pkg.tar.zst"],
            "rhel": ["dist/android-file-handler-*.rpm"],
            "windows": [
                "dist/android-file-handler-windows.exe",
                "dist/android-file-handler-setup.exe",
            ],
        }
    )
