# Birthmark GIMP Plugin - Installation Guide

This guide will walk you through installing the Birthmark modification tracking plugin for GIMP 2.10.

## Prerequisites

- **GIMP 2.10 or later** installed with Python-Fu support (included by default)
- **Birthmark aggregation server** running (or accessible at a known URL)
- **SSA validation server** running (or accessible at a known URL)
- **Software certificate** from SSA provisioning process

## Installation Steps

### 1. Locate GIMP Plug-ins Directory

The plugin file needs to be placed in GIMP's plug-ins directory.

#### Windows

1. Open File Explorer
2. In the address bar, type: `%APPDATA%\GIMP\2.10\plug-ins`
3. Press Enter

**Alternative method (find in GIMP):**
1. Open GIMP
2. Go to **Edit → Preferences**
3. Expand **Folders** in the left panel
4. Click **Plug-ins**
5. Note the directory path shown (use the one in your user directory)

Common paths:
- `C:\Users\YourUsername\AppData\Roaming\GIMP\2.10\plug-ins`

#### Linux

The default location is:
```
~/.config/GIMP/2.10/plug-ins/
```

Or check in GIMP via **Edit → Preferences → Folders → Plug-ins**

#### macOS

The default location is:
```
~/Library/Application Support/GIMP/2.10/plug-ins/
```

Or check in GIMP via **GIMP → Preferences → Folders → Plug-ins**

### 2. Create Plugin Directory

Create a new folder for the Birthmark plugin:

```
plug-ins/birthmark/
```

**Windows example:**
```
%APPDATA%\GIMP\2.10\plug-ins\birthmark\
```

### 3. Copy Plugin File

Copy `birthmark_gimp_plugin.py` into the newly created directory:

```
%APPDATA%\GIMP\2.10\plug-ins\birthmark\birthmark_gimp_plugin.py
```

### 4. Make Executable (Linux/macOS only)

On Linux and macOS, the plugin file must be executable:

```bash
chmod +x ~/.config/GIMP/2.10/plug-ins/birthmark/birthmark_gimp_plugin.py
```

**Windows users can skip this step** - Windows doesn't require the executable flag.

### 5. Set Up Birthmark Configuration Directory

Create a directory for Birthmark certificates:

#### Windows

1. Open File Explorer
2. In the address bar, type: `%USERPROFILE%`
3. Create a new folder named `.birthmark`
4. Final path: `C:\Users\YourUsername\.birthmark`

**Using Command Prompt:**
```cmd
mkdir %USERPROFILE%\.birthmark
```

#### Linux/macOS

```bash
mkdir ~/.birthmark
```

### 6. Install Software Certificates

Copy your provisioned software certificates into the `.birthmark` directory:

1. `software_certificate.pem`
2. `software_private_key.pem`

**Windows example:**
```
C:\Users\YourUsername\.birthmark\software_certificate.pem
C:\Users\YourUsername\.birthmark\software_private_key.pem
```

**Linux/macOS example:**
```
~/.birthmark/software_certificate.pem
~/.birthmark/software_private_key.pem
```

### 7. Configure Server URLs (Optional)

By default, the plugin expects:
- Aggregation server at `http://localhost:8000`
- SSA server at `http://localhost:8001`

If your servers are at different URLs, you'll need to edit the plugin file:

1. Open `birthmark_gimp_plugin.py` in a text editor
2. Find the configuration section near the top:
   ```python
   # Configuration
   AGGREGATION_SERVER_URL = "http://localhost:8000"
   SSA_SERVER_URL = "http://localhost:8001"
   ```
3. Update the URLs to match your setup
4. Save the file

### 8. Restart GIMP

Close GIMP completely and reopen it to load the plugin.

## Verify Installation

1. Open GIMP
2. Open any image (File → Open)
3. Look for a **Birthmark** menu in the main menu bar
4. The Birthmark menu should contain:
   - Initialize Tracking
   - Log Level 1 Operation
   - Log Level 2 Operation
   - Show Status
   - Export with Record

### Test the Plugin

1. With an image open, click **Birthmark → Show Status**
2. You should see a message: "Status: NOT INITIALIZED"
3. If you see this, the plugin is installed correctly!

## Troubleshooting

### Plugin doesn't appear in menu

**Check the Error Console:**
1. In GIMP, go to **Filters → Python-Fu → Console**
2. Look for any error messages related to the Birthmark plugin

**Common issues:**
- Plugin file is not in the correct directory
- Plugin file is not executable (Linux/macOS only)
- Python syntax errors (should not happen with provided code)

**Verify plugin path:**
Make sure the file is exactly at:
```
[GIMP plug-ins directory]/birthmark/birthmark_gimp_plugin.py
```

### Certificate not found error

When you run "Initialize Tracking" and see:
```
ERROR: Certificate not found at C:\Users\YourUsername\.birthmark\software_certificate.pem
```

**Solution:**
1. Make sure you've created the `.birthmark` directory
2. Copy the certificate files from SSA provisioning
3. Verify the filenames are exactly:
   - `software_certificate.pem`
   - `software_private_key.pem`

### Server connection errors

When you see errors like:
```
Software validation failed: [Errno 10061] Connection refused
```

**Solution:**
1. Make sure the SSA server is running at `http://localhost:8001`
2. Test with a browser: visit `http://localhost:8001/health`
3. If using different URLs, update the configuration in the plugin file

### Authentication check fails

When you see:
```
Authentication check failed: [Errno 10061] Connection refused
```

**Solution:**
1. Make sure the aggregation server is running at `http://localhost:8000`
2. Test with a browser: visit `http://localhost:8000/api/v1/health`
3. If using different URLs, update the configuration in the plugin file

## Uninstallation

To remove the plugin:

1. Delete the plugin directory:
   - Windows: Delete `%APPDATA%\GIMP\2.10\plug-ins\birthmark`
   - Linux/macOS: Delete `~/.config/GIMP/2.10/plug-ins/birthmark`

2. Optionally remove the certificate directory:
   - Windows: Delete `%USERPROFILE%\.birthmark`
   - Linux/macOS: Delete `~/.birthmark`

3. Restart GIMP

## Next Steps

Once installation is complete, see the [User Guide](user_guide.md) for instructions on using the plugin.

For information about which operations are classified as Level 1 vs Level 2, see the [Level Classification Guide](level_classification.md).

## Support

If you encounter issues not covered here, please:

1. Check the GIMP Python-Fu Console for detailed error messages
2. Verify that both the aggregation server and SSA server are running
3. Ensure the certificate files are correctly installed
4. Review the plugin code for any configuration mismatches

For development questions, refer to the main Birthmark documentation at:
- GitHub: https://github.com/Birthmark-Standard/Birthmark
- Phase 3 Plan: `docs/phase-plans/Birthmark_Phase_3_Plan_Image_Editor_Wrapper_SSA.md`
