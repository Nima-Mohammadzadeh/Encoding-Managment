import os
import math
from datetime import datetime

# Assuming epc_conversion.py is in the same utils folder or accessible
from .epc_conversion import generate_epc

def generate_roll_tracker_html(params):
    """
    Generates the HTML content for the roll tracker.
    
    Args:
        params (dict): A dictionary containing all necessary parameters:
            'upc', 'start_serial', 'adjusted_qty', 'lpr', 'qty_per_db',
            'job_ticket_number', 'customer_name', 'output_directory'
    
    Returns:
        str: The full path to the generated HTML file, or None on failure.
    """
    try:
        # Extract params for easier access
        upc = params['upc']
        start_serial = params['start_serial']
        adjusted_qty = params['adjusted_qty']
        lpr = params['lpr']
        qty_per_db = params['qty_per_db']
        job_ticket_number = params['job_ticket_number']
        customer_name = params['customer_name']
        output_directory = params['output_directory']

        roll_tracker_dir = os.path.join(output_directory, "roll tracker")
        os.makedirs(roll_tracker_dir, exist_ok=True)
        roll_tracker_filename = os.path.join(roll_tracker_dir, f"roll_tracker_{upc}.html")
        
        num_files = math.ceil(adjusted_qty / qty_per_db)
        
        db_pages_html, qc_rolls = _generate_roll_data(upc, start_serial, adjusted_qty, lpr, qty_per_db, job_ticket_number, customer_name, num_files)

        with open(roll_tracker_filename, "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>")
            f.write(f"<title>Roll Tracker - {customer_name} - {job_ticket_number}</title>")
            f.write(_get_html_style())
            f.write("</head><body>")
            
            # QC Page
            f.write(_get_qc_page_html(job_ticket_number, customer_name, upc, qc_rolls))
            
            # DB Pages
            for db_html_chunk in db_pages_html:
                f.write(db_html_chunk)
                
            f.write("</body></html>")

        return roll_tracker_filename

    except Exception as e:
        print(f"Error generating roll tracker HTML: {e}")
        return None

def generate_quality_control_sheet(job_data, output_path):
    """
    Generate a standalone HTML quality control sheet for printing based on job data.
    This is designed to be used during job creation automation.
    
    Args:
        job_data (dict): Complete job data from the wizard containing all job information
        output_path (str): Full path where the QC sheet HTML file should be saved
    
    Returns:
        str: The full path to the generated HTML file, or None on failure
    """
    try:
        # Extract job information
        customer = job_data.get('Customer', 'Unknown Customer')
        job_ticket = job_data.get('Job Ticket#', job_data.get('Ticket#', 'Unknown'))
        po_number = job_data.get('PO#', 'Unknown')
        part_number = job_data.get('Part#', 'Unknown')
        item = job_data.get('Item', 'Unknown')
        upc = job_data.get('UPC Number', '')
        quantity = int(job_data.get('Quantity', job_data.get('Qty', 0)))
        lpr = int(job_data.get('LPR', 100))
        inlay_type = job_data.get('Inlay Type', 'Unknown')
        label_size = job_data.get('Label Size', 'Unknown')
        due_date = job_data.get('Due Date', 'Unknown')
        
        # Handle serial number - could be from various sources
        start_serial = 1
        if 'Serial Range Start' in job_data:
            start_serial = int(job_data['Serial Range Start'])
        elif 'Serial Number' in job_data and job_data['Serial Number']:
            start_serial = int(job_data['Serial Number'])
        elif 'Start' in job_data and job_data['Start']:
            start_serial = int(job_data['Start'])
        
        # Calculate total quantity (may include buffers for EPC jobs)
        total_quantity = quantity
        if 'Total Quantity with Buffers' in job_data:
            total_quantity = int(job_data['Total Quantity with Buffers'])
        elif job_data.get('Enable EPC Generation', False):
            # Calculate with potential buffers
            from .epc_conversion import calculate_total_quantity_with_percentages
            include_2_percent = job_data.get('Include 2% Buffer', False)
            include_7_percent = job_data.get('Include 7% Buffer', False)
            total_quantity = calculate_total_quantity_with_percentages(
                quantity, include_2_percent, include_7_percent
            )
        
        # Calculate roll information
        num_rolls = math.ceil(total_quantity / lpr)
        rolls_data = []
        current_serial = start_serial
        
        for roll_num in range(1, num_rolls + 1):
            remaining_qty = total_quantity - (roll_num - 1) * lpr
            roll_qty = min(lpr, remaining_qty)
            
            roll_start_serial = current_serial
            roll_end_serial = current_serial + roll_qty - 1
            
            roll_info = {
                'roll_number': roll_num,
                'quantity': roll_qty,
                'start_serial': roll_start_serial,
                'end_serial': roll_end_serial,
                'start_epc': generate_epc(upc, roll_start_serial) if upc else 'N/A',
                'end_epc': generate_epc(upc, roll_end_serial) if upc else 'N/A'
            }
            rolls_data.append(roll_info)
            current_serial += roll_qty
        
        # Generate the HTML content
        html_content = _generate_qc_sheet_html(
            customer, job_ticket, po_number, part_number, item, upc,
            quantity, total_quantity, lpr, inlay_type, label_size, 
            due_date, rolls_data
        )
        
        # Write the HTML file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Quality control sheet generated: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error generating quality control sheet: {e}")
        return None

def _short_epc(e):
    return e[-5:] if len(e) >= 5 else e

def _generate_roll_data(upc, start_serial, adjusted_qty, lpr, qty_per_db, job_ticket_number, customer_name, num_files):
    db_pages_html = []
    rolls_for_qc = []
    total_roll_num = 1
    global_serial = start_serial
    
    for db_index in range(1, num_files + 1):
        db_label_count = min(qty_per_db, adjusted_qty - (db_index - 1) * qty_per_db)
        if db_label_count <= 0:
            break

        chunk = ["<div class='db-container'>"]
        chunk.append("<table>")
        chunk.append(f"<tr class='db-header'><td colspan='4'>Database {db_index}</td></tr>")
        chunk.append(f"<tr class='info-row'><td colspan='4'>")
        chunk.append(f"<span><b>Customer:</b> {customer_name}</span>")
        chunk.append(f"<span><b>Job #:</b> {job_ticket_number}</span>")
        chunk.append(f"<span><b>Printer:</b> ___________________</span>")
        chunk.append(f"</td></tr>")
        chunk.append("<tr><th>Roll #</th><th>Label Range</th><th>Start EPC</th><th>End EPC</th></tr>")

        db_remaining = db_label_count
        db_current_start_label = 1

        while db_remaining > 0:
            roll_count = min(lpr, db_remaining)
            roll_local_start = db_current_start_label
            roll_local_end = roll_local_start + roll_count - 1
            
            epc_start_serial = global_serial
            epc_end_serial = global_serial + roll_count - 1

            epc_start_val = generate_epc(upc, epc_start_serial)
            epc_end_val = generate_epc(upc, epc_end_serial)

            label_range_formatted = f"{roll_local_start:,} - {roll_local_end:,}"

            chunk.append(f"<tr><td>{total_roll_num}</td><td>{label_range_formatted}</td><td>{_short_epc(epc_start_val)}</td><td>{_short_epc(epc_end_val)}</td></tr>")

            # Notes Sub-row
            chunk.append("<tr class='sub-row'><td colspan='4'>")
            chunk.append("<div>Notes: ________________________________________________________________________________________________</div>")
            chunk.append("</td></tr>")

            rolls_for_qc.append({
                "roll_num": total_roll_num,
                "start_serial": epc_start_serial,
                "end_serial": epc_end_serial
            })

            db_current_start_label += roll_count
            db_remaining -= roll_count
            global_serial += roll_count
            total_roll_num += 1

        chunk.append("</table></div>")
        db_pages_html.append("\n".join(chunk))
        
    return db_pages_html, rolls_for_qc

def _get_qc_page_html(job_ticket, customer, upc, qc_rolls):
    html = ["<div class='qc-page'>"]
    html.append("<h1>Quality Control</h1>")
    html.append(f"<h2>Job Ticket #: {job_ticket}</h2>")
    html.append(f"<h2>Customer: {customer}</h2>")
    html.append(f"<h2>UPC: {upc}</h2>")
    html.append("<table>")
    html.append("<tr><th>Roll #</th><th>Start EPC</th><th>End EPC</th><th>QC Check</th></tr>")

    for roll_info in qc_rolls:
        epc_start = generate_epc(upc, roll_info["start_serial"])
        epc_end = generate_epc(upc, roll_info["end_serial"])
        html.append(f"<tr><td>{roll_info['roll_num']}</td><td>{_short_epc(epc_start)}</td><td>{_short_epc(epc_end)}</td><td></td></tr>")

    html.append("</table></div>")
    return "".join(html)

def _generate_qc_sheet_html(customer, job_ticket, po_number, part_number, item, upc,
                           quantity, total_quantity, lpr, inlay_type, label_size, 
                           due_date, rolls_data):
    """Generate the complete HTML content for the quality control sheet."""
    
    html = [
        '<!DOCTYPE html>',
        '<html lang="en">',
        '<head>',
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f'<title>Quality Control Sheet - {customer} - {job_ticket}</title>',
        _get_qc_sheet_style(),
        '</head>',
        '<body>',
        '<div class="qc-sheet">',
        
        # Header
        '<div class="header">',
        '<h1>QUALITY CONTROL</h1>',
        '</div>',
        
        # Combined Job Information Section
        '<div class="job-info-section">',
        '<h2>Job Information</h2>',
        '<div class="info-grid">',
        f'<div class="info-item"><span class="label">Customer:</span> <span class="value">{customer}</span></div>',
        f'<div class="info-item"><span class="label">Job Ticket #:</span> <span class="value">{job_ticket}</span></div>',
        f'<div class="info-item"><span class="label">PO #:</span> <span class="value">{po_number}</span></div>',
        f'<div class="info-item"><span class="label">Part #:</span> <span class="value">{part_number}</span></div>',
        f'<div class="info-item"><span class="label">Item:</span> <span class="value">{item}</span></div>',
        f'<div class="info-item"><span class="label">Due Date:</span> <span class="value">{due_date}</span></div>',
        f'<div class="info-item"><span class="label">UPC Number:</span> <span class="value">{upc if upc else "N/A"}</span></div>',
        f'<div class="info-item"><span class="label">Inlay Type:</span> <span class="value">{inlay_type}</span></div>',
        f'<div class="info-item"><span class="label">Label Size:</span> <span class="value">{label_size}</span></div>',
        f'<div class="info-item"><span class="label">Base Quantity:</span> <span class="value">{quantity:,}</span></div>',
        f'<div class="info-item"><span class="label">Total Quantity:</span> <span class="value">{total_quantity:,}</span></div>',
        f'<div class="info-item"><span class="label">Labels Per Roll:</span> <span class="value">{lpr:,}</span></div>',
        '</div>',
        '</div>',
        
        # Roll Tracking Table
        '<div class="roll-tracking-section">',
        '<h2>Roll Tracking & Quality Control</h2>',
        '<table class="roll-table">',
        '<thead>',
        '<tr>',
        '<th>Roll #</th>',
        '<th>Quantity</th>',
        '<th>Serial Range</th>',
    ]
    
    # Add EPC columns if UPC is available
    if upc:
        html.extend([
            '<th>Start EPC</th>',
            '<th>End EPC</th>',
        ])
    
    html.extend([
        '</tr>',
        '</thead>',
        '<tbody>',
    ])
    
    # Add roll data rows
    for roll in rolls_data:
        html.append('<tr>')
        html.append(f'<td class="roll-number">{roll["roll_number"]}</td>')
        html.append(f'<td class="quantity">{roll["quantity"]:,}</td>')
        html.append(f'<td class="serial-range">{roll["start_serial"]:,} - {roll["end_serial"]:,}</td>')
        
        if upc:
            html.append(f'<td class="epc">{_short_epc(roll["start_epc"])}</td>')
            html.append(f'<td class="epc">{_short_epc(roll["end_epc"])}</td>')
        
        html.append('</tr>')
    
    html.extend([
        '</tbody>',
        '</table>',
        '</div>',
        
        '</div>',
        '</body>',
        '</html>'
    ])
    
    return '\n'.join(html)

def _get_qc_sheet_style():
    """Return CSS styles optimized for printing quality control sheets."""
    return '''
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            font-size: 12pt;
            line-height: 1.4;
            color: #333;
            background: white;
        }
        
        .qc-sheet {
            width: 100%;
            max-width: none;
            margin: 0 auto;
            padding: 0.3in;
            background: white;
        }
        
        .header {
            text-align: center;
            margin-bottom: 0.1in;
            border-bottom: 3px solid #333;
            padding-bottom: 0.1in;
        }
        
        .header h1 {
            font-size: 24pt;
            font-weight: bold;
            color: #333;
            margin-bottom: 0.1in;
        }
        

        
        .job-info-section, .roll-tracking-section {
            margin-bottom: 0.3in;
        }
        
        h2 {
            font-size: 16pt;
            font-weight: bold;
            color: #333;
            margin-bottom: 0.15in;
            border-bottom: 1px solid #ccc;
            padding-bottom: 0.05in;
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 0.1in;
            margin-bottom: 0.2in;
        }
        
        .info-item {
            display: flex;
            padding: 0.05in 0;
        }
        
        .label {
            font-weight: bold;
            width: 1.5in;
            flex-shrink: 0;
        }
        
        .value {
            border-bottom: 1px dotted #999;
            flex-grow: 1;
            min-height: 1.2em;
        }
        
        .roll-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 11pt;
            margin-bottom: 0.2in;
        }
        
        .roll-table th,
        .roll-table td {
            border: 1px solid #333;
            padding: 0.08in;
            text-align: center;
            vertical-align: middle;
        }
        
        .roll-table th {
            background-color: #f5f5f5;
            font-weight: bold;
            font-size: 10pt;
        }
        
        .roll-number {
            font-weight: bold;
            background-color: #fafafa;
        }
        
        .serial-range {
            font-family: 'Courier New', monospace;
            font-size: 10pt;
        }
        
        .epc {
            font-family: 'Courier New', monospace;
            font-size: 9pt;
        }
        

        
        /* Print-specific styles */
        @page {
            size: letter;
            margin: 0.5in;
        }
        
        @media print {
            body {
                font-size: 11pt;
            }
            
            .qc-sheet {
                max-width: none;
                margin: 0;
                padding: 0;
            }
            
            .header h1 {
                font-size: 20pt;
            }
            
            h2 {
                font-size: 14pt;
            }
            
            .roll-table {
                font-size: 10pt;
            }
            
            .roll-table th {
                font-size: 9pt;
            }
            
            /* Ensure table doesn't break across pages poorly */
            .roll-table {
                page-break-inside: avoid;
            }
            
            .roll-tracking-section {
                page-break-inside: avoid;
            }
        }
    </style>
    '''

def _get_html_style():
    return """
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 20px; color: #333; }
        .qc-page, .db-container { page-break-after: always; }
        .qc-page:last-child, .db-container:last-child { page-break-after: auto; }
        h1, h2 { text-align: center; }
        h1 { font-size: 24px; }
        h2 { font-size: 18px; color: #555; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; font-size: 14px; page-break-inside: avoid; }
        th, td { border: 1px solid #ccc; padding: 8px 10px; text-align: center; }
        th { background-color: #f2f2f2; font-weight: 600; }
        .db-header { background-color: #e9ecef; font-weight: bold; font-size: 18px; }
        .info-row td { text-align: left; border-top: 2px solid #333; border-bottom: 2px solid #333;}
        .info-row span { margin-right: 40px; }
        .sub-row td { border: none; text-align: left; padding: 5px 15px; font-size: 12px; }
        .sub-row div { border-top: 1px dotted #aaa; padding-top: 5px; }
        @page { size: A4; margin: 20mm; }
        @media print {
            body { margin: 0; font-size: 12pt; }
            .qc-page, .db-container { page-break-after: always !important; }
            h1 { font-size: 22pt; } h2 { font-size: 16pt; }
        }
    </style>
    """ 