# Template Integration Guide

## Overview

The application now automatically copies BarTender (.btw) template files to job folders during creation. This feature works for both traditional and EPC-enabled job structures, ensuring that the appropriate template files are available in each job's print folder.

## Template Directory Structure

Templates are organized by **label size only** under the **Template Base Path**, with template files containing customer and inlay type information in their filenames:

```
Template Base Path/
├── Label Size 1/
│   ├── Label Size 1 InlayType Customer Template.btw
│   └── Label Size 1 InlayType Customer2 Template.btw
└── Label Size 2/
    ├── Label Size 2 InlayType Customer Template.btw
    └── Label Size 2 InlayType Customer3 Template.btw
```

### Actual Structure
```
Z:\3 Encoding and Printing Files\Templates/
├── 0.910 x 1.85/
│   └── 0.910 x 1.85 261 NEL Insertion Phenix Template.btw
├── 1.76 x 0.71/
│   └── 1.76 x 0.71 241 Peak Template.btw
├── 1.85 x 0.91/
│   ├── 1.85 x 0.91 261 Insertion Phenix Template.btw
│   └── 1.85 x 0.91 261 Peak Template.btw
├── 2.126x1.339/
│   ├── 2.126x1.339 300 Peak Template.btw
│   └── 2.126x1.339 300 Smead Template.btw
└── 2.953 X 0.5905/
    └── 2.953 X 0.5905 430 Peak Template .btw
```

## Configuration

### Setting Template Base Path

1. **Open Settings Page** in the application
2. **Find "Template Base Path"** in the Directory Settings section
3. **Set the path** to your template directory root
   - Default: `Z:\3 Encoding and Printing Files\Templates`
4. **Click "Save Directory Settings"**

### Template Base Path Setting
The template base path is configured in:
- **Settings UI**: Settings page → Directory Settings → Template Base Path
- **Config File**: `src/config.py` → `TEMPLATE_BASE_PATH`
- **Registry/Settings**: Stored persistently using QSettings

## How Template Copying Works

### Job Creation Process

When creating a new job, the system:

1. **Identifies customer and label size** from job details
2. **Looks for template file** in the template directory structure
3. **Creates print folder** in the job directory
4. **Copies template file** to the print folder with appropriate filename
5. **Reports success or alternative template usage**

### Template Lookup Process

The system uses an intelligent matching process:

1. **Find Label Size Directory**: Look for directory matching the label size (case-insensitive)
2. **Score Template Files**: Use scoring system to find best match:
   - **Customer Match** (100 points): Template filename contains customer name
   - **Inlay Type Match** (50 points): Template filename contains inlay type
   - **Inlay Number Match** (25 points): Template filename contains inlay type numbers
3. **Select Best Match**: Return template with highest score
4. **Fallback**: If no scored matches, return first available .btw file

### Destination Filename Priority

Copied template files are renamed based on this priority:

1. **UPC Number** (if available): `123456789012.btw`
2. **Job Ticket Number**: `JT12345.btw`
3. **PO Number**: `PO67890.btw`

## Job Folder Structures

### Traditional Job Structure
```
25-01-07 - PO12345 - JT67890/
├── print/
│   └── JT67890.btw          # Copied template
├── Peak Technologies-JT67890-PO12345-Checklist.pdf
└── job_data.json
```

### EPC-Enabled Job Structure
```
01.07.25 - PO12345 - JT67890/
└── 123456789012/            # UPC folder
    ├── data/                # EPC database files
    │   ├── 123456789012.DB1.1K-1K.xlsx
    │   └── 123456789012.DB2.2K-2K.xlsx
    └── print/
        └── 123456789012.btw # Copied template (UPC filename)
```

## Integration Points

### New Job Wizard

- **Template Status Display**: Shows template availability on EPC Database page
- **Real-time Updates**: Template status updates when customer/label size changes
- **Alternative Template Detection**: Shows if alternative naming templates are found

### Job Creation Methods

Template copying is integrated into all job creation methods:

1. **New Job Wizard** (`src/wizards/new_job_wizard.py`)
2. **Context Menu Folder Creation** (`src/tabs/job_page.py`)
3. **Job Details Dialog Folder Creation** (`src/widgets/job_details_dialog.py`)

### File Monitoring

- Created template files are automatically detected by the file system monitor
- Template files appear in job file listings with appropriate icons
- Template files can be opened directly from the job details dialog

## Error Handling

### Missing Templates

When templates are not found:
- **Job creation continues** without errors
- **Warning logged** to console: `"No template found for Customer - LabelSize"`
- **Job folder structure created** normally
- **Print folder created** but remains empty

### Template Path Issues

- **Invalid template base path**: Logged warning, no template copying attempted
- **Missing customer/label size folders**: Alternative naming attempted
- **Template file permissions**: Copy errors logged but don't block job creation

## Testing

Run the template copying test suite:

```bash
python test_template_copying.py
```

This tests:
- Template directory structure creation
- Template file lookup functionality
- Template copying with different filename priorities
- Alternative template naming conventions
- Error handling for missing templates

## Troubleshooting

### Templates Not Copying

1. **Check Template Base Path**:
   - Verify path in Settings → Directory Settings
   - Ensure path exists and is accessible
   - Check for proper folder permissions

2. **Verify Directory Structure**:
   - Customer name must match exactly (case-sensitive)
   - Label size must match exactly (case-sensitive)
   - Template file must follow naming convention

3. **Check Console Output**:
   - Look for template-related messages during job creation
   - Check for file path and permission errors

### Template Path Examples

**Template Directory Structure**:
```
Z:\3 Encoding and Printing Files\Templates\1.85 x 0.91\1.85 x 0.91 261 Peak Template.btw
```

**Example Lookups**:
- **Customer**: "Peak Technologies", **Label Size**: "1.85 x 0.91", **Inlay**: "261"
  - Matches: `1.85 x 0.91 261 Peak Template.btw` (Customer + Inlay match = 150 points)
- **Customer**: "Smead", **Label Size**: "2.126x1.339", **Inlay**: "300" 
  - Matches: `2.126x1.339 300 Smead Template.btw` (Customer + Inlay match = 150 points)
- **Customer**: "Unknown", **Label Size**: "1.76 x 0.71", **Inlay**: "241"
  - Matches: `1.76 x 0.71 241 Peak Template.btw` (Inlay match = 50 points)

## Migration from Manual Process

### Previous Workflow
1. Create job folder manually
2. Navigate to template directory
3. Find appropriate template
4. Copy template to print folder
5. Rename template file

### New Automated Workflow
1. Use New Job Wizard or context menu
2. **System automatically**:
   - Creates folder structure
   - Finds appropriate template
   - Copies and renames template
   - Reports template status

## Best Practices

### Template Organization

1. **Use consistent naming**: Follow the `Template LabelSize.btw` convention
2. **Organize by customer**: Keep customer-specific templates in dedicated folders
3. **Version control**: Consider backup strategies for template files
4. **Test templates**: Verify templates work in BarTender before deployment

### Filename Conventions

1. **Avoid special characters** in customer and label size names
2. **Use descriptive label sizes**: `2.9 x 0.47` instead of `small`
3. **Keep consistent spacing**: Match exactly what's in dropdown lists

### Performance Considerations

1. **Template file size**: Keep template files reasonable size for quick copying
2. **Network paths**: Ensure good network connectivity to template directories
3. **File permissions**: Maintain appropriate read permissions on template files

## Future Enhancements

Potential improvements for the template system:

1. **Template validation**: Check template compatibility before copying
2. **Multiple template support**: Allow multiple templates per customer/label size
3. **Template versioning**: Support for template version management
4. **Batch template operations**: Tools for managing multiple templates
5. **Template preview**: Show template preview in job wizard

---

*This template integration enhances workflow efficiency by automating the manual process of copying and renaming template files during job creation.* 