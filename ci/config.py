"""Shared configuration for CI/CD pipeline."""

from dataclasses import dataclass, field
from pathlib import Path


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
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent.resolve())

    # Container images (from GHCR)
    debian_image: str = "ghcr.io/jmr-dev/android-file-handler-debian-builder:debian13-trixie"
    arch_image: str = "ghcr.io/jmr-dev/android-file-handler-arch-builder:latest"
    rhel_image: str = "ghcr.io/jmr-dev/android-file-handler-rhel-builder:fedora42"

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
    artifact_patterns: dict[str, list[str]] = field(default_factory=lambda: {
        "debian": ["dist/android-file-handler_*.deb"],
        "arch": ["dist/android-file-handler-*.pkg.tar.zst"],
        "rhel": ["dist/android-file-handler-*.rpm"],
        "windows": [
            "dist/android-file-handler-windows.exe",
            "dist/android-file-handler-setup.exe",
        ],
    })
