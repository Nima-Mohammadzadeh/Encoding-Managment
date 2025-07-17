# Encoding Manager Distribution Guide

This document provides instructions for distributing the Encoding Manager application to end users.

## Distribution Package

The distribution package is located in the `dist` folder after running the build script. It contains:

- `encoding_manager.exe` - The main application executable
- Various support directories:
  - `active_jobs` - Directory for active job data
  - `active_jobs_source` - Directory for job source files
  - `archive` - Directory for archived jobs
  - `logs` - Directory for application logs
  - `templates` - Directory for document templates
  - `serial_numbers` - Directory for serial number data
- Configuration and documentation files:
  - `settings.json` - Application settings
  - Various `.md` files with documentation

## Distribution Options

### Option 1: Direct Distribution

1. Copy the entire `dist` folder to a USB drive or network share
2. Have users copy the folder to their desired location (e.g., Desktop or Program Files)
3. Create a shortcut to `encoding_manager.exe` for easy access

### Option 2: Create an Installer

For a more professional distribution, you can create an installer using tools like:

- [Inno Setup](https://jrsoftware.org/isinfo.php) (Free)
- [NSIS](https://nsis.sourceforge.io/Main_Page) (Free)
- [Advanced Installer](https://www.advancedinstaller.com/) (Paid)

Basic steps for creating an installer:
1. Point the installer to the contents of the `dist` folder
2. Configure installation directory (e.g., `C:\Program Files\Encoding Manager`)
3. Add desktop/start menu shortcuts
4. Add uninstallation support

## System Requirements

- Windows 10 or later
- At least 4GB of RAM
- 200MB of disk space
- Administrator privileges for installation (if using an installer)

## First-Time Setup

When users first run the application, they should:

1. Open the application by double-clicking `encoding_manager.exe`
2. Go to the Settings tab to configure:
   - Default directories for jobs and archives
   - User preferences
   - Network paths (if applicable)
3. Restart the application after initial setup

## Updating the Application

To update the application:

1. Build a new version using the build script
2. Distribute the new executable and any changed files
3. Users should back up their data before updating
4. Replace the old executable and files with the new ones

## Troubleshooting

If users encounter issues:

- Check the `logs` directory for error messages
- Ensure all required directories exist and are accessible
- Verify that the user has appropriate permissions
- For network-related issues, check network connectivity and share permissions

## Support

For support issues, users should contact the system administrator or IT support team. 