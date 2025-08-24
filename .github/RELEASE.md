# Release Workflow Documentation

This document describes the automated release workflow for the Android File Handler ADB tool.

## Overview

The release workflow automatically builds and publishes native binaries for multiple platforms when a new tag is pushed. It creates:

- **Linux Binary**: Native executable for Linux systems
- **Windows Binary**: Native executable (.exe) for Windows systems  
- **DEB Packages**: Debian/Ubuntu packages (.deb)
- **RPM Packages**: Red Hat/Fedora packages (.rpm)
- **AUR Package**: Arch User Repository submission

## Triggering a Release

1. **Create and push a tag**:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **Manual workflow dispatch** (optional):
   - Go to Actions tab in GitHub
   - Select "Release" workflow
   - Click "Run workflow"
   - Optionally enable "Dry Run" mode

## Required Repository Secrets

For AUR publishing, configure these secrets in repository settings:

| Secret Name | Description |
|-------------|-------------|
| `AUR_SSH_PRIVATE_KEY` | SSH private key for AUR publishing |
| `AUR_USER_NAME` | Git username for AUR commits |
| `AUR_USER_EMAIL` | Git email for AUR commits |

## Workflow Features

### Multi-Platform Builds
- **Linux**: Built on Ubuntu with PyInstaller
- **Windows**: Cross-compiled on Ubuntu with PyInstaller
- **Arch Linux**: Built in native Arch container

### Security Features
- SHA256 checksums for all release assets
- Comprehensive file validation
- Binary integrity verification

### Package Management
- **DEB**: Created with `fpm` for APT repositories
- **RPM**: Created with `fpm` for DNF/YUM repositories
- **AUR**: Automated PKGBUILD generation and submission

### Quality Assurance
- Binary size validation (must be > 1MB)
- File existence verification
- Build success validation
- Comprehensive error reporting

## Dry Run Mode

Enable dry run mode to test the workflow without publishing:

1. Go to Actions → Release workflow
2. Click "Run workflow"
3. Check "Enable dry run mode"
4. Click "Run workflow"

In dry run mode:
- All builds are executed
- Validation is performed
- No actual publishing occurs
- Assets are still created for review

## Build Outputs

### Release Assets
All builds create files in the `release-assets/` directory:

```
release-assets/
├── android-file-handler           # Linux binary
├── android-file-handler.exe       # Windows binary  
├── android-file-handler_*.deb     # Debian packages
├── android-file-handler-*.rpm     # RPM packages
└── SHA256SUMS                     # Checksums file
```

### Validation Reports
The workflow provides comprehensive build quality assessment:

- ✅/❌ Binary creation success
- ✅/❌ Package count validation
- 📊 File size verification
- 🔒 SHA256 checksum generation

## Troubleshooting

### Common Issues

1. **No release assets created**
   - Check artifact download step
   - Verify PyInstaller execution
   - Review build logs for errors

2. **Binary validation fails**
   - Ensure binaries are > 1MB
   - Check file permissions
   - Verify executable format

3. **AUR publishing fails**
   - Verify SSH key configuration
   - Check AUR credentials
   - Ensure PKGBUILD syntax

### Debug Steps

1. **Enable dry run mode** to test without publishing
2. **Check build logs** for specific error messages
3. **Verify dependencies** in pyproject.toml
4. **Test locally** with PyInstaller before pushing

## Maintenance

### Updating the Workflow

When modifying the workflow:

1. Test changes in a fork first
2. Use dry run mode for validation
3. Monitor build quality metrics
4. Update this documentation

### Version Requirements

- Python 3.8+ (specified in workflow)
- Poetry for dependency management
- ADB platform tools (bundled)

## Security Considerations

- SSH keys are properly secured and permissioned
- Checksums provide integrity verification
- Secrets are never logged or exposed
- Build artifacts are validated before release

This workflow ensures reliable, secure, and comprehensive multi-platform releases for the Android File Handler ADB tool.
