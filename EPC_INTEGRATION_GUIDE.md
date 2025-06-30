# EPC Conversion Integration Guide

## Overview

I have successfully integrated the EPC conversion logic from your separate Python script into your workflow optimizer application. This integration provides seamless UPC-to-EPC conversion, enhanced directory structures, template management, and database generation capabilities directly within your existing workflow.

## What's Been Added

### 1. EPC Conversion Utilities Module (`src/utils/epc_conversion.py`)

This new module contains all the conversion logic from your original EPC script:

- **`generate_epc(upc, serial_number)`** - Converts UPC + serial number to EPC hex
- **`validate_upc(upc)`** - Validates 12-digit UPC format
- **`create_upc_folder_structure()`** - Creates enhanced folder structure with UPC subfolders
- **`generate_epc_database_files()`** - Generates Excel files with UPC/Serial/EPC data
- **`calculate_total_quantity_with_percentages()`** - Applies 2% and 7% buffers
- **Template management functions** for customer/label size directory structures

### 2. Enhanced New Job Wizard

The job creation wizard now includes a new **Step 3: EPC Database Generation** page with:

- **Enable/Disable EPC Generation** - Optional EPC database creation
- **Quantity per DB File** - Configurable records per database file (default: 1000)
- **Percentage Buffers** - Optional 2% and 7% quantity buffers
- **Live Preview** - Generate and view sample EPC data before creation
- **Template Status** - Shows if templates are available for the selected customer/label size

### 3. Enhanced Job Creation Logic

When creating jobs, the system now:

- Uses the **mm.dd.yy** date format (from your EPC script) instead of yy-mm-dd
- Creates **UPC subfolder structure**: `job_folder/upc/[data, print]/`
- **Copies template files** automatically to the `print` folder
- **Generates EPC database files** in the `data` folder when enabled
- **Maintains backward compatibility** with traditional folder structure for non-EPC jobs

### 4. Context Menu Enhancement

Right-click on any job with a valid UPC to access:

- **"Generate EPC Database..."** - Create EPC databases for existing jobs
- Configurable parameters (serial number, quantity, buffers)
- Automatic file placement in appropriate directories

### 5. Settings Page Integration

New settings option for:

- **Template Base Path** - Configure where your customer/label_size template structure is located
- Default points to `Z:\3 Encoding and Printing Files\Templates` (from your EPC script)

### 6. Updated Dependencies

Added required packages to `requirements.txt`:
- `pandas>=1.5.0` - For database file generation
- `openpyxl>=3.0.0` - For Excel file creation

## How to Use the New Features

### Creating Jobs with EPC Generation

1. **Start New Job Wizard** - Click "Add Job" button
2. **Fill Job Details** (Step 1) - Enter customer, part#, ticket#, etc.
3. **Enter Encoding Info** (Step 2) - Include UPC number and serial number
4. **Configure EPC Options** (Step 3) - NEW STEP
   - Check "Generate EPC Database Files" to enable
   - Set quantity per database file (default: 1000)
   - Add percentage buffers if needed
   - Click "Generate Preview" to see sample data
   - Template status shows if templates are available
5. **Select Save Location** (Step 4) - Choose where to create the job
6. **Finish** - Job created with enhanced structure and EPC databases

### Generated Folder Structure (EPC Enabled)

```
12.15.24 - PO12345 - TK67890/           # Job folder (mm.dd.yy format)
├── job_data.json                       # Job metadata
├── Customer-TK67890-PO12345-Checklist.pdf  # PDF checklist
└── 123456789012/                       # UPC subfolder
    ├── data/                           # EPC database files
    │   ├── 123456789012.DB1.1K-1K.xlsx
    │   └── 123456789012.DB2.2K-2K.xlsx
    └── print/                          # Template files
        └── 123456789012.btw            # Copied template
```

### Generating EPC Databases for Existing Jobs

1. **Right-click on job** with valid UPC in the jobs table
2. **Select "Generate EPC Database..."**
3. **Configure parameters** in the dialog:
   - Starting serial number
   - Total quantity
   - Quantity per database file
   - Optional percentage buffers
4. **Click OK** - EPC files generated and saved

### Configuring Template Path

1. **Go to Settings page**
2. **Find "Template Base Path"** in Directory Settings
3. **Set path** to your template directory structure
   - Should contain `Customer/LabelSize/Template LabelSize.btw` structure
   - Default: `Z:\3 Encoding and Printing Files\Templates`
4. **Save Directory Settings**

## EPC Database File Format

Generated Excel files contain three columns:
- **UPC** - The 12-digit UPC code
- **Serial #** - Sequential serial numbers
- **EPC** - Generated EPC hex values

Files are named: `{UPC}.DB{number}.{startK}-{endK}.xlsx`

Example: `123456789012.DB1.1K-1K.xlsx`

## Backward Compatibility

- **Existing jobs** continue to work unchanged
- **Traditional folder structure** still available for non-EPC jobs
- **All existing features** remain functional
- **EPC generation is optional** - can be disabled per job

## Testing the Integration

Run the test script to verify functionality:

```bash
python test_epc_conversion.py
```

This tests:
- EPC generation algorithms
- UPC validation
- Folder structure creation
- Database file generation
- Quantity calculations

## Configuration Files

### Updated Files:
- `src/config.py` - Added template base path settings
- `requirements.txt` - Added pandas and openpyxl dependencies
- `src/wizards/new_job_wizard.py` - Added EPC database generation page
- `src/tabs/job_page.py` - Enhanced job creation logic
- `src/tabs/settings_page.py` - Added template path configuration

### New Files:
- `src/utils/__init__.py` - Utils module initialization
- `src/utils/epc_conversion.py` - EPC conversion functionality
- `test_epc_conversion.py` - Test script
- `EPC_INTEGRATION_GUIDE.md` - This documentation

## Key Improvements Over Original Script

1. **Integrated Workflow** - No need to switch between applications
2. **Automatic Template Management** - Templates copied automatically
3. **Enhanced UI** - Preview functionality and validation
4. **Data Persistence** - Job data saved with EPC information
5. **Flexible Configuration** - Per-job EPC generation settings
6. **Better Error Handling** - User-friendly error messages
7. **File System Monitoring** - Automatic detection of new jobs

## Next Steps

1. **Install Dependencies**: Run `pip install pandas openpyxl` if not already installed
2. **Configure Template Path**: Set the template base path in Settings
3. **Test with Sample Job**: Create a test job with EPC generation enabled
4. **Verify Template Structure**: Ensure your templates follow the expected directory structure

The integration maintains all the powerful conversion logic from your original EPC script while providing a seamless, integrated user experience within your workflow optimizer application. 