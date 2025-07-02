import os
import math

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