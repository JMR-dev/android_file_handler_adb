#!/usr/bin/env python3

import os
import subprocess
import shutil
import sys
from pathlib import Path
from enum import Enum
from typing import List


class DistroType(Enum):
    DEBIAN = "debian"
    ARCH = "arch"
    RHEL = "rhel"


def run_command(cmd: list[str], check: bool = True, working_dir: str = None) -> subprocess.CompletedProcess:
    """Run command and handle errors."""
    print(f"Running: {' '.join(cmd)}")
    try:
        return subprocess.run(cmd, check=check, capture_output=False, cwd=working_dir)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}: {' '.join(cmd)}")
        sys.exit(e.returncode)
    except FileNotFoundError:
        print(f"Command not found: {cmd[0]}")
        sys.exit(1)


def get_distro_config(distro_type: DistroType) -> dict:
    """Get configuration for specific distro type."""
    configs = {
        DistroType.DEBIAN: {
            "name": "Debian",
            "bin_path": "usr/local/bin",
            "pkg_suffix": "debian",
            "spec_file": "scripts/spec_scripts/android-file-handler-debian.spec"
        },
        DistroType.ARCH: {
            "name": "Arch",
            "bin_path": "usr/bin",
            "pkg_suffix": "arch",
            "spec_file": "scripts/spec_scripts/android-file-handler-arch.spec"
        },
        DistroType.RHEL: {
            "name": "RHEL",
            "bin_path": "usr/bin", 
            "pkg_suffix": "rhel",
            "spec_file": "scripts/spec_scripts/android-file-handler-rhel.spec"
        }
    }
    return configs[distro_type]


def prompt_distro_selection() -> List[DistroType]:
    """Prompt user for distro selection."""
    print("Select distribution(s) to build for:")
    print("1. Debian")
    print("2. Arch")
    print("3. RHEL")
    print("4. All distributions")
    
    while True:
        choice = input("Enter choice (1-4): ").strip()
        if choice == "1":
            return [DistroType.DEBIAN]
        elif choice == "2":
            return [DistroType.ARCH]
        elif choice == "3":
            return [DistroType.RHEL]
        elif choice == "4":
            return [DistroType.DEBIAN, DistroType.ARCH, DistroType.RHEL]
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")


def build_for_distro(distro_type: DistroType, version: str, project_root: Path) -> None:
    """Build package for specific distro type."""
    config = get_distro_config(distro_type)
    print(f"\n=== Building for {config['name']} ===")
    
    # Construct absolute paths
    spec_file = project_root / config['spec_file']
    dist_dir = project_root / f"dist_{config['pkg_suffix']}"
    
    # Verify spec file exists
    if not spec_file.exists():
        print(f"ERROR: Spec file not found: {spec_file}")
        sys.exit(1)
    
    # Build with distro-specific spec file
    print(f"Building binary using {spec_file}")
    run_command([
        "poetry", "run", "pyinstaller", 
        str(spec_file),
        "--distpath", str(dist_dir)
    ], working_dir=str(project_root))
    
    # Make binary executable
    binary_path = Path(f"dist_{config['pkg_suffix']}/android-file-handler")
    binary_path.chmod(0o755)
    
    # Package preparation
    pkg_dir = Path(f"pkg_dist_{config['pkg_suffix']}")
    
    # Clean and create package structure
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)
    
    directories = [
        config["bin_path"],
        "usr/share/applications", 
        "usr/share/icons/hicolor/256x256/apps"
    ]
    
    for directory in directories:
        (pkg_dir / directory).mkdir(parents=True, exist_ok=True)
    
    # Copy built binary
    binary_dst = pkg_dir / config["bin_path"] / "android-file-handler"
    shutil.copy2(f"dist_{config['pkg_suffix']}/android-file-handler", binary_dst)
    binary_dst.chmod(0o755)
    
    # Handle icon
    icon_src = Path("icon_media/robot_files_256.png")
    icon_dst = pkg_dir / "usr/share/icons/hicolor/256x256/apps/android-file-handler.png"
    icon_included = False
    
    if icon_src.exists():
        shutil.copy2(icon_src, icon_dst)
        icon_dst.chmod(0o644)
        icon_included = True
    else:
        print(f"Warning: icon not found at {icon_src}; packaging without icon")
    
    # Create .desktop file with correct exec path
    exec_path = f"/{config['bin_path']}/android-file-handler"
    desktop_content = f"""[Desktop Entry]
Type=Application
Name=Android File Handler
Comment=Manage Android device files via ADB
Exec={exec_path} %U
Icon=android-file-handler
Terminal=false
Categories=Utility;Development;
StartupNotify=true
"""
    
    desktop_path = pkg_dir / "usr/share/applications/android-file-handler.desktop"
    desktop_path.write_text(desktop_content)
    desktop_path.chmod(0o644)
    
    # Build package items list
    pkg_items = [
        f"{config['bin_path']}/android-file-handler",
        "usr/share/applications/android-file-handler.desktop"
    ]
    
    if icon_included:
        pkg_items.append("usr/share/icons/hicolor/256x256/apps/android-file-handler.png")
    
    # Debug listing
    print(f"Packaging the following items for {config['name']} (relative to {pkg_dir}):")
    for item in pkg_items:
        print(f" - {item}")
        item_path = pkg_dir / item
        if item_path.exists():
            stat = item_path.stat()
            print(f"   {oct(stat.st_mode)[-3:]} {stat.st_size:>8} {item_path}")
        else:
            print(f"   (missing) {item_path}")


def main():
    # Get project root (parent of scripts directory)
    project_root = Path(__file__).parent.parent.resolve()
    print(f"Project root: {project_root}")
    
    # Change to project root
    os.chdir(project_root)
    
    # Check if running in CI/CD mode
    is_ci_cd = os.environ.get("CI_CD", "false").lower() == "true"
    
    if is_ci_cd:
        distro_env = os.environ.get("DISTRO_TYPE", "").lower()
        if distro_env == "debian":
            selected_distros = [DistroType.DEBIAN]
            print("CI/CD mode detected - building for Debian")
        elif distro_env == "arch":
            selected_distros = [DistroType.ARCH]
            print("CI/CD mode detected - building for Arch")
        elif distro_env == "rhel":
            selected_distros = [DistroType.RHEL]
            print("CI/CD mode detected - building for RHEL")
        else:
            print(f"Error: Invalid or missing DISTRO_TYPE environment variable: '{distro_env}'")
            print("Valid values: debian, arch, rhel")
            sys.exit(1)
    else:
        selected_distros = prompt_distro_selection()
    
    # Poetry operations (only once)
    print("=== Preparing Poetry environment ===")
    if is_ci_cd:
        print("CI/CD mode: skipping poetry lock")
        run_command(["poetry", "install"])
    else:
        print("Development mode: running poetry lock and install")
        run_command(["poetry", "lock"])
        run_command(["poetry", "install"])
    
    # Get version from Poetry
    result = subprocess.run(
        ["poetry", "version", "-s"], 
        capture_output=True, 
        text=True, 
        check=True
    )
    version = result.stdout.strip()
    print(f"Version: {version}")
    
    # Build for selected distributions
    for distro_type in selected_distros:
        build_for_distro(distro_type, version, project_root)
    
    print(f"\n=== Build complete for: {', '.join([get_distro_config(d)['name'] for d in selected_distros])} ===")
    
    # Show output directories
    print("\nOutput directories:")
    for distro_type in selected_distros:
        config = get_distro_config(distro_type)
        print(f"  {config['name']}: pkg_dist_{config['pkg_suffix']}/")


if __name__ == "__main__":
    main()