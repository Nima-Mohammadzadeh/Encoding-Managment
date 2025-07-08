# Archive Page User Guide

## Overview
The Archive Page has been completely refined to provide a seamless, easy-to-use search experience for browsing through all archived jobs. The new design focuses on powerful search capabilities while maintaining the same double-click functionality as the active jobs table.

## Key Features

### 🔍 **Powerful Search Bar**
- **Location**: Prominent search bar at the top of the page
- **Functionality**: Searches across ALL job fields including:
  - Customer name
  - Part number
  - Ticket number
  - PO number
  - Inlay type
  - Label size
  - Quantity
  - Status
  - UPC number
  - Serial number
  - Due date
- **Real-time Results**: Search updates automatically as you type (with 300ms debouncing)
- **Case Insensitive**: Search works regardless of capitalization

### 📊 **Smart Stats Display**
- Shows total number of archived jobs
- Displays filtered results count when searching or filtering
- Example: "25 of 150 jobs found" or "150 archived jobs"

### 🎯 **Quick Filters**
- **Customer Filter**: Dropdown populated with all unique customers from archived jobs
- **Clear Button**: Instantly clear search and reset all filters
- **Removed**: Status filter (no longer needed since all archived jobs have archived status)

### 📅 **Advanced Date Filters (Optional)**
- **Toggle Button**: "Show Date Filters" / "Hide Date Filters"
- **Date Range**: Filter by archive date range (from/to)
- **Reset Button**: Reset dates to default range (last year to today)
- **Smart Design**: Date filters only apply when the advanced section is visible
- **Automatic Date Collection**: Archive dates are now automatically collected when jobs are moved to archive

### 📋 **Enhanced Results Table**
- **Column Headers**: Customer, Ticket#, PO#, Part#, Inlay, Size, Qty, Archived Date
- **Improved Layout**: Removed Status column and reordered columns for better space utilization
- **Customer Column**: Now properly visible with adequate space allocation
- **Sortable**: Click any column header to sort
- **Proper Formatting**: 
  - Quantities display with comma separators (e.g., "50,000")
  - Archived dates show in MM/DD/YYYY format for better readability
- **Auto-sizing**: Columns resize appropriately for content

### 🖱️ **Interaction Features**
- **Double-click**: Open job details dialog (same as active jobs table)
- **Right-click**: Context menu with "View Details" and "Delete Job" options
- **Read-only Details**: Archived job details are view-only (editing disabled)

## How to Use

### Basic Search
1. Type any text in the search bar
2. Results update automatically
3. Search finds matches across all job fields
4. Use the "Clear" button to reset

### Quick Filtering
1. Select a customer from the dropdown to filter by customer
2. Combine with search for more precise results
3. Use date filters for time-based searches

### Advanced Date Filtering
1. Click "Show Date Filters" button
2. Set your desired date range using the calendar pickers
3. Results will filter to only show jobs archived in that date range
4. Click "Reset Dates" to return to default range
5. Click "Hide Date Filters" to disable date filtering

### Viewing Job Details
1. **Double-click** any job row to open detailed view
2. **Right-click** for context menu options
3. Job details dialog shows all information but in read-only mode
4. Archive-specific actions (like editing) are disabled

### Search Examples
- Search for `"Peak"` to find all jobs for Peak Technologies
- Search for `"123456"` to find jobs with that PO number, ticket number, or any field containing that number
- Search for `"EOS-241"` to find all jobs using that inlay type
- Search for `"50000"` to find jobs with 50,000 quantity

## Tips for Efficient Use

### 🎯 **Search Strategy**
- Start with broad terms and narrow down as needed
- Use partial matches (e.g., "Peak" instead of "Peak Technologies")
- Search by any data point you remember (customer, numbers, dates, etc.)

### 🔧 **Filter Combinations**
- Combine search with customer filter for targeted results
- Use date filters when looking for jobs from specific time periods
- Filter by customer and then search within those results

### 📱 **Performance**
- Search is optimized with debouncing for smooth typing
- Results update quickly even with large archives
- Stats keep you informed of result counts

### 🗂️ **Organization**
- Sort by any column to organize results
- Use customer filter to focus on specific clients
- Date filters help with periodic reviews
- Archived Date column shows when jobs were moved to archive

## Technical Notes

### Data Sources
- Loads archived jobs from individual `job_data.json` files in archive folders
- Supports both old and new field naming conventions
- Handles data format changes gracefully

### Performance Features
- Debounced search prevents excessive filtering while typing
- Efficient in-memory filtering for fast results
- Smart loading only reads necessary data

### Compatibility
- Maintains backward compatibility with existing archive structure
- Works with jobs archived from the refined job system
- Handles various data field formats and naming conventions

## Troubleshooting

### No Results Found
- Check if search term is spelled correctly
- Try broader search terms
- Verify date filters aren't too restrictive
- Use "Clear" button to reset all filters

### Missing Jobs
- Ensure jobs were properly archived (not just deleted)
- Check that archive directory is accessible
- Verify job folders contain `job_data.json` files

### Slow Performance
- Large archives (1000+ jobs) may take a moment to load initially
- Search and filtering remain fast regardless of archive size
- Consider using filters to narrow results for better navigation

## Future Enhancements

The refined archive page provides a solid foundation for additional features such as:
- Export filtered results to CSV/Excel
- Bulk operations on selected jobs
- Advanced search with field-specific criteria
- Archive statistics and reporting
- Integration with external reporting tools 