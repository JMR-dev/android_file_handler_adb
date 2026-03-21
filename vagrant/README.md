# Vagrant Windows 11 Test Environment

Automated testing of the Android File Handler installer on a clean Windows 11 VM using Hyper-V.

## Prerequisites

- [Vagrant](https://www.vagrantup.com/) >= 2.4
- Hyper-V enabled (`Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All`)
- [Inno Setup 6](https://jrsoftware.org/isdl.php) installed (default path or ISCC.exe in PATH)
- Poetry environment set up (`poetry install`)

## Setup (one-time)

```powershell
cd vagrant
vagrant up --provider=hyperv
vagrant snapshot save clean
```

> **Note:** Vagrant will prompt for your Windows credentials to set up the SMB synced folder.
> You can set `VAGRANT_SMB_USERNAME` and `VAGRANT_SMB_PASSWORD` environment variables to skip the prompt.

## Running Tests

From the repo root:

```powershell
.\scripts\windows\run_vagrant_tests.ps1
```

This will:

1. Build the installer locally (PyInstaller + Inno Setup)
2. Restore the VM to the `clean` snapshot
3. Push the installer to the VM via WinRM
4. Run the installer silently inside the VM
5. Verify installation (directory, exe, shortcuts, registry)
6. Launch the app, find the window, take a GUI screenshot
7. Run silent uninstall and verify cleanup
8. Retrieve results CSV + screenshots to `vagrant_test_results\<timestamp>\`
9. Print a summary table to the CLI
10. Revert the VM back to the `clean` snapshot

### Options

| Flag | Description |
|---|---|
| `-SkipBuild` | Skip the local build step (use an existing installer in `dist\`) |
| `-SkipRevert` | Leave the VM in post-test state (useful for debugging) |
| `-SnapshotName <name>` | Use a different snapshot name (default: `clean`) |
| `-LocalResultsDir <path>` | Override where results are saved |

## What Gets Tested

| # | Test | Description |
|---|---|---|
| 1 | Installer exists | Checks the built `.exe` is present |
| 2 | Silent install | Runs the Inno Setup installer with `/VERYSILENT` |
| 3 | Install directory | Verifies `C:\Program Files\Android File Handler` exists |
| 4 | Executable present | Checks the app `.exe` is in the install directory |
| 5 | Start Menu shortcut | Verifies the Start Menu entry was created |
| 6 | Registry entry | Checks Add/Remove Programs registration |
| 7 | App launches | Starts the app and confirms it stays running |
| 8 | Window found | Finds the main window by its title |
| 9 | Silent uninstall | Runs the uninstaller and verifies cleanup |

## File Structure

```
vagrant/
├── Vagrantfile          # VM definition (Windows 11 Enterprise, Hyper-V)
├── provision.ps1        # VM provisioning (nircmd for screenshots)
├── test_installer.ps1   # Test script that runs inside the VM
└── README.md            # This file
scripts/windows/
└── run_vagrant_tests.ps1  # Host-side orchestrator (builds, pushes, tests, reverts)
```

## Troubleshooting

**VM won't start**: Ensure Hyper-V is enabled and you are running the terminal as Administrator.

**WinRM connection fails**: The box uses plaintext WinRM on port 55985. Ensure no firewall blocks it.

**SMB share prompt**: Set `VAGRANT_SMB_USERNAME` and `VAGRANT_SMB_PASSWORD` environment variables to avoid interactive credential prompts.

**Inno Setup not found**: Install Inno Setup 6 to the default path or add `ISCC.exe` to your PATH.

**Want to inspect the VM manually**: Use `vagrant rdp` or pass `-SkipRevert`.
