# Serial Number Integration Guide

## Overview

This document explains how serial number management is integrated with job creation, EPC generation, and PDF checklist creation to ensure proper serial number allocation and tracking.

## Serial Number Flow

### 1. **Job Creation Process**

When a user creates a job through the wizard:

1. **Wizard Input**: User enters job details including quantity
2. **Serial Allocation**: System automatically allocates serial numbers from centralized source
3. **Range Calculation**: System calculates start and end serials based on quantity
4. **Database Generation**: If EPC enabled, creates database files with allocated serials
5. **PDF Generation**: Creates checklist PDF with serial range information
6. **Source Update**: Updates centralized serial source for next job

### 2. **Serial Range Calculation**

#### For EPC Jobs (with buffers):
```
Base Quantity: 50,000
2% Buffer: 1,000 (if enabled)
7% Buffer: 3,500 (if enabled)
Total Quantity: 54,500

Serial Allocation:
- Start Serial: 1
- End Serial: 54,500 (start + total - 1)
- Next Available: 54,501 (start + total)
```

#### For Traditional Jobs (no buffers):
```
Base Quantity: 50,000
Total Quantity: 50,000

Serial Allocation:
- Start Serial: 1
- End Serial: 50,000 (start + quantity - 1)
- Next Available: 50,001 (start + quantity)
```

### 3. **PDF Field Population**

The generated PDF checklist automatically populates these fields:

| PDF Field | Source | Example Value |
|-----------|--------|---------------|
| Start | job_data["Start"] | 1,000 |
| End | job_data["End"] | 50,000 |
| Qty | job_data["Quantity"] | 50,000 |
| Customer | job_data["Customer"] | Peak Technologies |

## Technical Implementation

### 1. **Centralized Serial Manager**

```python
# Location: src/utils/serial_manager.py
def allocate_serials_for_job(quantity, job_data):
    """
    Allocates serial range and updates centralized source
    Returns: (start_serial, end_serial)
    """
    manager = get_serial_manager()
    return manager.allocate_serials(quantity, job_info)
```

#### Daily Serial Files:
- **Location**: `{configured_path}/serials_YYYY-MM-DD.json`
- **Example**: `Z:\3 Encoding and Printing Files\Serial Numbers\serials_2025-01-08.json`
- **Structure**:
```json
{
  "current_serial": 50001,
  "usage_log": [
    {
      "timestamp": "2025-01-08T10:30:00",
      "start_serial": 1,
      "end_serial": 50000,
      "quantity": 50000,
      "customer": "Peak Technologies",
      "po_number": "TEST123",
      "ticket_number": "TKT001"
    }
  ]
}
```

### 2. **Job Data Enhancement**

During job creation, the system adds serial range information:

```python
# EPC Jobs
job_data["Start"] = str(start_serial)           # "1"
job_data["End"] = str(end_serial)               # "54500"
job_data["Serial Range Start"] = start_serial   # 1
job_data["Serial Range End"] = end_serial       # 54500
job_data["Total Quantity with Buffers"] = total_qty  # 54500

# Traditional Jobs  
job_data["Start"] = str(start_serial)           # "1"
job_data["End"] = str(end_serial)               # "50000"
job_data["Serial Range Start"] = start_serial   # 1
job_data["Serial Range End"] = end_serial       # 50000
```

### 3. **PDF Generation Integration**

The PDF worker automatically formats and populates serial fields:

```python
elif data_key == "Start":
    # Format start serial number with commas
    start_value = self.job_data.get("Start", "")
    if start_value and str(start_value).replace(',', '').isdigit():
        clean_start = str(start_value).replace(',', '')
        value = f"{int(clean_start):,}"  # "1,000"
        
elif data_key == "End":
    # Format end serial number with commas  
    end_value = self.job_data.get("End", "")
    if end_value and str(end_value).replace(',', '').isdigit():
        clean_end = str(end_value).replace(',', '')
        value = f"{int(clean_end):,}"  # "50,000"
```

## Manual vs Automatic Serial Allocation

### Automatic Mode (Default)
- **Source**: Centralized serial manager
- **Benefits**: Prevents duplicates across all users
- **Location**: Network drive or configured path
- **Fallback**: If centralized source unavailable, uses wizard input

### Manual Override Mode
- **Source**: User-entered serial number in wizard
- **When to Use**: Special cases, testing, or when centralized system unavailable
- **Warning**: User responsible for ensuring no duplicates

## Example Scenarios

### Scenario 1: EPC Job with Buffers
```
User Input:
- Customer: Peak Technologies
- Quantity: 50,000
- 2% Buffer: Enabled
- 7% Buffer: Enabled

System Calculation:
- Base Qty: 50,000
- Total with Buffers: 54,500
- Allocated Range: 1 - 54,500
- Next Available: 54,501

PDF Output:
- Start: 1
- End: 54,500
- Qty: 50,000

Database Files:
- 55 files (1,000 records each)
- Last file: 500 records
```

### Scenario 2: Traditional Job
```
User Input:
- Customer: ACME Corp
- Quantity: 25,000
- No buffers

System Calculation:
- Total: 25,000
- Allocated Range: 54,501 - 79,500
- Next Available: 79,501

PDF Output:
- Start: 54,501
- End: 79,500
- Qty: 25,000
```

## Debugging and Troubleshooting

### Console Output
The system provides detailed logging:

```
=== PDF Generation Debug ===
Available Start value: 1
Available End value: 54500
Job data keys: ['Customer', 'Part#', 'Ticket#', 'PO#', 'Quantity', 'Start', 'End', ...]

PDF: Set Start field to 1
PDF: Set End field to 54,500
```

### Verification Steps

1. **Check Serial Source**: Verify centralized serial file is accessible
2. **Monitor Console**: Look for allocation success messages
3. **Verify PDF**: Check that Start/End fields are populated
4. **Database Check**: Ensure EPC files use correct serial range

### Common Issues

#### PDF Fields Not Populated
- **Cause**: Serial range not calculated before PDF generation
- **Solution**: Check console for allocation errors
- **Debug**: Look for "PDF Generation Debug" output

#### Serial Duplicates  
- **Cause**: Multiple users accessing serial source simultaneously
- **Solution**: File locking prevents this (automatic)
- **Fallback**: Use manual override if needed

#### Network Drive Issues
- **Cause**: Z: drive not accessible
- **Solution**: Configure local serial path in settings
- **Alternative**: Use manual serial override

## Configuration

### Serial Numbers Path
```python
# In src/config.py
SERIAL_NUMBERS_PATH = "Z:\\3 Encoding and Printing Files\\Serial Numbers"

# Can be changed in settings to:
SERIAL_NUMBERS_PATH = "C:\\Local\\Serial Numbers"  # Local fallback
```

### PDF Template Fields
The PDF template must have these field names:
- `start` - for starting serial number
- `end` - for ending serial number  
- `qty` - for quantity
- Other standard job fields

## Multi-User Considerations

### File Locking
- **Windows**: Uses `msvcrt.locking()` for exclusive access
- **Cross-Platform**: Automatic fallback for other systems
- **Thread Safety**: Internal threading locks prevent conflicts

### Performance
- **Atomic Operations**: Serial allocation is atomic (all-or-nothing)
- **Quick Operations**: Allocation typically takes <100ms
- **Network Resilience**: Automatic retry on temporary network issues

### Best Practices
1. **Use Automatic Mode**: Let system manage serials centrally
2. **Monitor Daily Files**: Check for proper allocation logging
3. **Regular Cleanup**: Archive old daily serial files periodically
4. **Backup Serial Data**: Include serial files in backup procedures

---

## Integration Points

This serial number system integrates with:
- **Job Creation Wizard** (`new_job_wizard.py`)
- **EPC Generation** (`epc_conversion.py`)
- **PDF Generation** (`job_details_dialog.py`)
- **Job Management** (`job_page.py`)
- **Configuration** (`config.py`)

All components work together to ensure consistent, unique serial number allocation across the entire workflow. 