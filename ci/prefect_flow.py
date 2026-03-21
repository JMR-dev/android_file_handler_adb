"""Prefect orchestration flow for the CI/CD release pipeline.

Coordinates Dagger-based Linux builds, GPG signing, GitHub release
creation, and S3 artifact upload.

Usage:
    # Build all Linux distros (CI)
    poetry run python -m ci.prefect_flow build-linux

    # Sign artifacts in dist/
    poetry run python -m ci.prefect_flow sign --gpg-passphrase "$GPG_PASSPHRASE"

    # Create GitHub release + upload S3
    poetry run python -m ci.prefect_flow release --github-token "$GITHUB_TOKEN"

    # Full pipeline (build + sign + release + S3)
    poetry run python -m ci.prefect_flow full --gpg-passphrase "$GPG_PASSPHRASE" \\
        --github-token "$GITHUB_TOKEN"
"""

import asyncio
import argparse
import os
import subprocess
from pathlib import Path

from prefect import flow, task

from ci.config import PipelineConfig
from ci.dagger_pipeline import build_all_linux
from ci.signing import sign_and_hash

# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@task(name="build-linux-distros", retries=1, retry_delay_seconds=30)
def task_build_linux(config: PipelineConfig) -> dict[str, dict[str, Path]]:  # type: ignore[type-arg]
    """Build all Linux distribution packages via Dagger containers."""
    print("=== Building Linux packages via Dagger ===")
    results = asyncio.run(build_all_linux(config))
    print(f"Linux builds completed: {list(results.keys())}")
    return results


@task(name="sign-artifacts")
def task_sign_artifacts(
    dist_dir: Path,
    gpg_passphrase: str,
    patterns: list[str] | None = None,
) -> list[Path]:
    """Sign and hash all release artifacts matching the given glob patterns.

    Args:
        dist_dir: Directory containing artifacts.
        gpg_passphrase: GPG key passphrase.
        patterns: Glob patterns to match artifacts. Defaults to common package types.

    Returns:
        List of generated signature and hash file paths.
    """
    if patterns is None:
        patterns = ["*.exe", "*.deb", "*.rpm", "*.pkg.tar.zst"]

    generated_files: list[Path] = []

    for pattern in patterns:
        for match in dist_dir.glob(pattern):
            print(f"Signing: {match.name}")
            sig_path, hash_path = sign_and_hash(match, gpg_passphrase)
            generated_files.extend([sig_path, hash_path])

    if not generated_files:
        print(f"Warning: no artifacts matched patterns {patterns} in {dist_dir}")

    return generated_files


@task(name="get-version")
def task_get_version() -> str:
    """Read the project version from pyproject.toml via Poetry."""
    result = subprocess.run(
        ["poetry", "version", "-s"],
        capture_output=True,
        text=True,
        check=True,
    )
    version = result.stdout.strip()
    if not version:
        raise RuntimeError("Version is empty in pyproject.toml")
    print(f"Project version: {version}")
    return version


@task(name="prepare-release-files")
def task_prepare_release_files(dist_dir: Path, release_dir: Path) -> list[Path]:
    """Collect all release artifacts into a single directory.

    Args:
        dist_dir: Source directory containing built artifacts.
        release_dir: Target directory for release files.

    Returns:
        List of files copied into the release directory.
    """
    release_dir.mkdir(parents=True, exist_ok=True)

    extensions = ["*.exe", "*.deb", "*.rpm", "*.pkg.tar.*", "*.asc", "*.sha256"]
    copied: list[Path] = []

    for ext in extensions:
        for src in dist_dir.glob(ext):
            dst = release_dir / src.name
            if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
                import shutil

                shutil.copy2(src, dst)
                copied.append(dst)
                print(f"  {src.name}")

    print(f"Prepared {len(copied)} release files in {release_dir}")
    return copied


@task(name="create-github-release")
def task_create_github_release(
    version: str,
    release_dir: Path,
    github_token: str,
) -> None:
    """Create a GitHub release with artifacts using gh CLI.

    Args:
        version: Semantic version string (e.g. '0.1.1').
        release_dir: Directory containing release files.
        github_token: GitHub token for authentication.
    """
    tag = f"v{version}"
    files = list(release_dir.iterdir())

    if not files:
        raise RuntimeError(f"No files found in {release_dir}")

    env = {**os.environ, "GH_TOKEN": github_token}

    cmd = [
        "gh",
        "release",
        "create",
        tag,
        "--title",
        f"Release {tag}",
        "--latest",
    ] + [str(f) for f in files]

    print(f"Creating GitHub release {tag} with {len(files)} files")
    subprocess.run(cmd, check=True, env=env)
    print(f"GitHub release {tag} created successfully")


@task(name="upload-s3")
def task_upload_s3(
    release_dir: Path,
    s3_bucket: str,
    run_id: str,
) -> None:
    """Upload release artifacts to S3.

    Args:
        release_dir: Directory containing release files.
        s3_bucket: S3 bucket name.
        run_id: Unique identifier for this build run.
    """
    if not s3_bucket:
        print("S3_BUCKET not set; skipping upload")
        return

    target = f"s3://{s3_bucket}/builds/{run_id}/"
    print(f"Uploading to {target}")

    subprocess.run(
        ["aws", "s3", "sync", str(release_dir), target, "--acl", "private"],
        check=True,
        env={**os.environ, "AWS_PAGER": ""},
    )
    print("S3 upload complete")


# ---------------------------------------------------------------------------
# Flows
# ---------------------------------------------------------------------------


@flow(name="build-linux-flow", log_prints=True)
def flow_build_linux() -> dict[str, dict[str, Path]]:  # type: ignore[type-arg]
    """Build all Linux distribution packages."""
    config = PipelineConfig()
    return task_build_linux(config)  # type: ignore[return-value]


@flow(name="sign-flow", log_prints=True)
def flow_sign(gpg_passphrase: str) -> list[Path]:
    """Sign all artifacts in the dist/ directory."""
    config = PipelineConfig()
    return task_sign_artifacts(config.project_root / "dist", gpg_passphrase)


@flow(name="release-flow", log_prints=True)
def flow_release(
    github_token: str,
    s3_bucket: str = "",
    run_id: str = "",
) -> None:
    """Create a GitHub release and optionally upload to S3."""
    config = PipelineConfig()
    version = task_get_version()

    release_dir = config.project_root / "release-files"
    task_prepare_release_files(config.project_root / "dist", release_dir)
    task_create_github_release(version, release_dir, github_token)

    if s3_bucket:
        task_upload_s3(release_dir, s3_bucket, run_id or "local")


@flow(name="full-pipeline", log_prints=True)
def flow_full_pipeline(
    gpg_passphrase: str = "",
    github_token: str = "",
    s3_bucket: str = "",
    run_id: str = "",
    skip_build: bool = False,
    skip_sign: bool = False,
    skip_release: bool = False,
) -> None:
    """Run the complete CI/CD pipeline: build → sign → release → S3.

    Args:
        gpg_passphrase: GPG key passphrase for signing.
        github_token: GitHub token for release creation.
        s3_bucket: Optional S3 bucket for artifact upload.
        run_id: Build run identifier for S3 path.
        skip_build: Skip the Linux build step.
        skip_sign: Skip the signing step.
        skip_release: Skip the release + S3 step.
    """
    config = PipelineConfig()

    # Step 1: Build Linux distros
    if not skip_build:
        task_build_linux(config)

    # Step 2: Sign artifacts
    if not skip_sign:
        if not gpg_passphrase:
            raise ValueError("--gpg-passphrase is required for signing")
        task_sign_artifacts(config.project_root / "dist", gpg_passphrase)

    # Step 3: Release
    if not skip_release:
        if not github_token:
            raise ValueError("--github-token is required for release")
        version = task_get_version()
        release_dir = config.project_root / "release-files"
        task_prepare_release_files(config.project_root / "dist", release_dir)
        task_create_github_release(version, release_dir, github_token)

        if s3_bucket:
            task_upload_s3(release_dir, s3_bucket, run_id or "local")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for running pipeline actions."""
    parser = argparse.ArgumentParser(
        description="CI/CD pipeline orchestration via Prefect + Dagger"
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    # build-linux
    subparsers.add_parser("build-linux", help="Build all Linux distribution packages")

    # sign
    sign_parser = subparsers.add_parser("sign", help="Sign artifacts in dist/")
    sign_parser.add_argument("--gpg-passphrase", required=True, help="GPG passphrase")

    # release
    release_parser = subparsers.add_parser("release", help="Create GitHub release")
    release_parser.add_argument("--github-token", required=True, help="GitHub token")
    release_parser.add_argument("--s3-bucket", default="", help="S3 bucket name")
    release_parser.add_argument("--run-id", default="", help="Build run ID")

    # full
    full_parser = subparsers.add_parser("full", help="Run full pipeline")
    full_parser.add_argument("--gpg-passphrase", default="", help="GPG passphrase")
    full_parser.add_argument("--github-token", default="", help="GitHub token")
    full_parser.add_argument("--s3-bucket", default="", help="S3 bucket name")
    full_parser.add_argument("--run-id", default="", help="Build run ID")
    full_parser.add_argument("--skip-build", action="store_true")
    full_parser.add_argument("--skip-sign", action="store_true")
    full_parser.add_argument("--skip-release", action="store_true")

    args = parser.parse_args()

    if args.action == "build-linux":
        flow_build_linux()
    elif args.action == "sign":
        flow_sign(gpg_passphrase=args.gpg_passphrase)
    elif args.action == "release":
        flow_release(
            github_token=args.github_token,
            s3_bucket=args.s3_bucket,
            run_id=args.run_id,
        )
    elif args.action == "full":
        flow_full_pipeline(
            gpg_passphrase=args.gpg_passphrase,
            github_token=args.github_token,
            s3_bucket=args.s3_bucket,
            run_id=args.run_id,
            skip_build=args.skip_build,
            skip_sign=args.skip_sign,
            skip_release=args.skip_release,
        )


if __name__ == "__main__":
    main()
