# Template Mapping Guide

This guide explains how to use the Template Mapping feature in the Encoding Manager application to explicitly map Customer + Label Size combinations to specific template files.

## Overview

The Template Mapping feature allows administrators to create explicit mappings between customer/label size pairs and specific BarTender template files. This provides more control over template selection compared to the automatic directory scanning approach.

## Benefits

- **Precise Control**: Explicitly define which template is used for each customer and label size combination
- **Shared Configuration**: Store mappings in a shared JSON file that all users can access
- **Override Automatic Selection**: Mappings take precedence over directory-based template discovery
- **Easy Management**: Edit mappings through the Settings UI without navigating file systems

## Configuration

### 1. Set the Template Mapping File Path

1. Open the application and go to **Settings**
2. In the **Directory Settings** section, find **Template Mapping File**
3. Click **Browse** and select or create a JSON file on your shared drive (e.g., `Z:\Templates\template_mappings.json`)
4. Click **Save Directory Settings**

### 2. Manage Template Mappings

1. In Settings, go to the **Job Wizard Dropdown Data** section
2. Click **Manage Template Mappings**
3. The Template Mapping Dialog will open

## Using the Template Mapping Dialog

### Adding a Mapping

1. Click **Add Mapping**
2. Select or enter a **Customer** name
3. Select or enter a **Label Size**
4. Browse for the template file (`.btw`)
5. Click **Add**

### Editing a Mapping

1. Find the mapping in the table
2. Click the **Edit** button in the Actions column
3. Browse for the new template file
4. The change is applied immediately

### Removing a Mapping

1. Find the mapping in the table
2. Click the **Remove** button in the Actions column
3. Confirm the removal

### Saving Changes

- Click **Save to File** to persist your changes to the JSON file
- Changes are shared with all users who access the same mapping file

## JSON File Format

The template mapping file uses a simple nested JSON structure:

```json
{
  "Customer Name": {
    "Label Size": "Path\\To\\Template.btw"
  }
}
```

Example:

```json
{
  "Peak Technologies": {
    "1.85 x 0.91": "Z:\\Templates\\Peak\\peak_small_label.btw",
    "2.126 x 1.339": "Z:\\Templates\\Peak\\peak_medium_label.btw",
    "4 x 6": "Z:\\Templates\\Peak\\peak_large_label.btw"
  },
  "Smead": {
    "2 x 1": "Z:\\Templates\\Smead\\smead_standard.btw",
    "3 x 2": "Z:\\Templates\\Smead\\smead_folder_label.btw"
  }
}
```

## Template Selection Priority

When creating a job, the system selects templates in this order:

1. **Template Mapping**: Check for an explicit mapping for the customer + label size
2. **Directory Scan**: If no mapping exists, scan the template base directory
3. **Fallback**: Use the first available template for the label size
4. **No Template**: Create the job without a template if none are found

## Best Practices

1. **Organize Templates**: Keep template files in a logical folder structure on the shared drive
2. **Consistent Naming**: Use descriptive template filenames that indicate customer and label size
3. **Regular Updates**: Review and update mappings when adding new customers or label sizes
4. **Backup**: Keep a backup of your template mapping file
5. **Permissions**: Ensure all users have read access to both the mapping file and template files

## Troubleshooting

### Templates Not Found
- Red text in the mapping dialog indicates the template file doesn't exist
- Verify the file path is correct and accessible
- Check network drive connections

### Mappings Not Loading
- Ensure the template mapping file path is correctly set in Settings
- Verify the JSON file is valid (no syntax errors)
- Check file permissions

### Changes Not Saving
- Ensure you have write permissions to the mapping file
- Click "Save to File" after making changes
- Check for file locks if multiple users are editing simultaneously

## Integration with Job Creation

During job creation:
1. The wizard displays the template status in real-time
2. Mapped templates show as "✓ Mapped template: [filename]"
3. Directory-found templates show as "✓ Template found: [filename]"
4. Missing templates show a warning but don't prevent job creation

The selected template is automatically copied to the job's print folder with an appropriate filename (UPC, Ticket#, or PO#). 