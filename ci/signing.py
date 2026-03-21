"""GPG signing and SHA-256 hashing utilities for release artifacts."""

import hashlib
import subprocess
import tempfile
from pathlib import Path


def gpg_sign_file(file_path: Path, passphrase: str) -> Path:
    """Create a detached ASCII-armored GPG signature for a file.

    Args:
        file_path: Path to the file to sign.
        passphrase: GPG key passphrase.

    Returns:
        Path to the generated .asc signature file.

    Raises:
        subprocess.CalledProcessError: If GPG signing fails.
        FileNotFoundError: If the input file does not exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    sig_path = file_path.with_suffix(file_path.suffix + ".asc")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".pass", delete=True) as passfile:
        passfile.write(passphrase)
        passfile.flush()

        subprocess.run(
            [
                "gpg", "--batch", "--yes",
                "--passphrase-file", passfile.name,
                "--detach-sign", "--armor",
                str(file_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    print(f"Signed: {sig_path}")
    return sig_path


def sha256_hash_file(file_path: Path) -> tuple[str, Path]:
    """Compute SHA-256 hash of a file and write a .sha256 checksum file.

    Args:
        file_path: Path to the file to hash.

    Returns:
        Tuple of (hex digest, path to .sha256 file).

    Raises:
        FileNotFoundError: If the input file does not exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    sha256 = hashlib.sha256()
    with open(file_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            sha256.update(chunk)

    digest = sha256.hexdigest()
    hash_line = f"{digest}  {file_path.name}"

    hash_path = file_path.parent / f"{file_path.stem}.sha256"
    hash_path.write_text(hash_line, encoding="ascii")

    print(f"SHA-256 ({file_path.name}): {digest}")
    return digest, hash_path


def sign_and_hash(file_path: Path, passphrase: str) -> tuple[Path, Path]:
    """Sign a file with GPG and generate its SHA-256 checksum.

    Args:
        file_path: Path to the artifact to sign and hash.
        passphrase: GPG key passphrase.

    Returns:
        Tuple of (signature path, hash file path).
    """
    sig_path = gpg_sign_file(file_path, passphrase)
    _, hash_path = sha256_hash_file(file_path)
    return sig_path, hash_path
