import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime, timedelta
import calendar
import hashlib
from io import BytesIO

# ReportLab is loaded lazily inside the PDF generator so the CRM can still start
# if a deployment has not installed the optional PDF dependency yet.

# ============================================================
# PRAGATI CRM - COMPLETE SERVICE & WORKFORCE SOFTWARE
# ============================================================

st.set_page_config(
    page_title="Pragati CRM",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB = "pragati_crm.db"


# ============================================================
# DATABASE
# ============================================================

def db():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def execute(sql, params=()):
    conn = db()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    result = cur.lastrowid
    conn.close()
    return result


def query(sql, params=()):
    conn = db()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def one(sql, params=()):
    conn = db()
    cur = conn.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()
    conn.close()
    return row


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def money(v):
    return f"₹{float(v or 0):,.2f}"


# ============================================================
# WHATSAPP CLOUD API
# ============================================================

def _setting_value(key, default=""):
    try:
        return settings[key] if settings and key in settings.keys() and settings[key] is not None else default
    except Exception:
        return default

def normalize_whatsapp_number(value):
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    # India-friendly default: 10 digit mobile -> 91XXXXXXXXXX
    if len(digits) == 10:
        digits = "91" + digits
    return digits

def whatsapp_configured():
    try:
        token = st.secrets.get("WHATSAPP_ACCESS_TOKEN", "")
    except Exception:
        token = ""
    token = token or _setting_value("whatsapp_access_token", "")
    phone_id = _setting_value("whatsapp_phone_number_id", "")
    enabled = int(_setting_value("whatsapp_enabled", 0) or 0) == 1
    return enabled and bool(token and phone_id), token, phone_id

def whatsapp_send_template(to, template_name, params=None, language=None):
    """Send an approved WhatsApp template. Returns (ok, message/error)."""
    configured, token, phone_id = whatsapp_configured()
    if not configured:
        return False, "WhatsApp is not configured/enabled."
    recipient = normalize_whatsapp_number(to)
    if not recipient:
        return False, "Recipient WhatsApp number is missing."
    if not template_name:
        return False, "WhatsApp template name is missing."
    try:
        import requests
        version = _setting_value("whatsapp_api_version", "v23.0") or "v23.0"
        if not str(version).startswith("v"):
            version = "v" + str(version)
        lang = language or _setting_value("whatsapp_language", "en_US") or "en_US"
        body_params = [{"type": "text", "text": str(x)} for x in (params or [])]
        template = {"name": str(template_name).strip(), "language": {"code": lang}}
        if body_params:
            template["components"] = [{"type": "body", "parameters": body_params}]
        url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": recipient,
                "type": "template",
                "template": template,
            },
            timeout=20,
        )
        data = response.json() if response.content else {}
        if response.ok:
            return True, data.get("messages", [{}])[0].get("id", "Sent")
        return False, data.get("error", {}).get("message", response.text[:300])
    except Exception as exc:
        return False, str(exc)

def whatsapp_notify(event_key, recipient, params=None):
    enabled_key = f"whatsapp_notify_{event_key}"
    if int(_setting_value(enabled_key, 1) or 0) != 1:
        return False, "Notification disabled."
    template_key = f"whatsapp_template_{event_key}"
    template = _setting_value(template_key, "")
    if not template:
        return False, f"Template not configured for {event_key}."
    return whatsapp_send_template(recipient, template, params=params)


# ============================================================
# PRINTABLE PDF HELPERS
# ============================================================

def _pdf_text(value):
    """Safe text for ReportLab; keep Indian currency printable everywhere."""
    if value is None:
        return ""
    text = str(value)
    return text.replace("₹", "Rs. ").replace("\n", "<br/>")


def _pdf_money(value):
    try:
        return f"Rs. {float(value or 0):,.2f}"
    except Exception:
        return "Rs. 0.00"


def make_printable_pdf(title, meta, sections, terms="", footer_note=""):
    """Create a clean A4 PDF that can be downloaded and printed."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PDF support is not installed. Add 'reportlab' to requirements.txt and reboot the Streamlit app."
        ) from exc

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14*mm,
        leftMargin=14*mm,
        topMargin=14*mm,
        bottomMargin=16*mm,
        title=title,
        author=str(settings["company_name"] if "settings" in globals() and settings else "Pragati CRM"),
    )

    styles = getSampleStyleSheet()
    company_style = ParagraphStyle(
        "Company", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=17, leading=20, alignment=TA_CENTER, spaceAfter=2*mm
    )
    title_style = ParagraphStyle(
        "DocTitle", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=13, leading=16, alignment=TA_CENTER, spaceAfter=4*mm
    )
    normal = ParagraphStyle(
        "NormalPDF", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=9.2, leading=12
    )
    small = ParagraphStyle(
        "SmallPDF", parent=normal, fontSize=8, leading=10
    )
    right = ParagraphStyle(
        "RightPDF", parent=normal, alignment=TA_RIGHT
    )

    story = []
    company = settings["company_name"] if "settings" in globals() and settings else "Pragati Enterprises"
    address = settings["address"] if "settings" in globals() and settings else ""
    phone = settings["phone"] if "settings" in globals() and settings else ""
    email = settings["email"] if "settings" in globals() and settings else ""
    gst_no = settings["gst"] if "settings" in globals() and settings else ""

    story.append(Paragraph(_pdf_text(company), company_style))
    contact_parts = [x for x in [address, phone, email, (f"GST: {gst_no}" if gst_no else "")] if x]
    if contact_parts:
        story.append(Paragraph(" | ".join(_pdf_text(x) for x in contact_parts), small))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(_pdf_text(title), title_style))

    if meta:
        rows = []
        for i in range(0, len(meta), 2):
            left = meta[i]
            right_item = meta[i+1] if i+1 < len(meta) else ("", "")
            rows.append([
                Paragraph(f"<b>{_pdf_text(left[0])}</b><br/>{_pdf_text(left[1])}", normal),
                Paragraph(f"<b>{_pdf_text(right_item[0])}</b><br/>{_pdf_text(right_item[1])}", normal),
            ])
        t=Table(rows, colWidths=[89*mm, 89*mm], hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BOX",(0,0),(-1,-1),0.6,colors.grey),
            ("INNERGRID",(0,0),(-1,-1),0.3,colors.lightgrey),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("LEFTPADDING",(0,0),(-1,-1),5),
            ("RIGHTPADDING",(0,0),(-1,-1),5),
            ("TOPPADDING",(0,0),(-1,-1),5),
            ("BOTTOMPADDING",(0,0),(-1,-1),5),
        ]))
        story.append(t)
        story.append(Spacer(1, 4*mm))

    for section_title, content in sections:
        if section_title:
            story.append(Paragraph(_pdf_text(section_title), ParagraphStyle(
                "Section", parent=styles["Heading3"], fontName="Helvetica-Bold",
                fontSize=10.5, leading=13, spaceBefore=2*mm, spaceAfter=1.5*mm
            )))
        if isinstance(content, list) and content and isinstance(content[0], (list, tuple)):
            data=[]
            for row in content:
                data.append([Paragraph(_pdf_text(cell), normal) for cell in row])
            col_count=max(len(r) for r in content)
            widths=[178*mm/col_count]*col_count
            t=Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
            t.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#eeeeee")),
                ("TEXTCOLOR",(0,0),(-1,0),colors.black),
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                ("GRID",(0,0),(-1,-1),0.45,colors.grey),
                ("VALIGN",(0,0),(-1,-1),"TOP"),
                ("LEFTPADDING",(0,0),(-1,-1),4),
                ("RIGHTPADDING",(0,0),(-1,-1),4),
                ("TOPPADDING",(0,0),(-1,-1),4),
                ("BOTTOMPADDING",(0,0),(-1,-1),4),
            ]))
            story.append(t)
        else:
            story.append(Paragraph(_pdf_text(content), normal))
        story.append(Spacer(1, 2*mm))

    if terms:
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph("Terms & Conditions", ParagraphStyle(
            "TC", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=10.5
        )))
        story.append(Paragraph(_pdf_text(terms), small))

    story.append(Spacer(1, 9*mm))
    sign = Table([["Prepared By", "Customer / Authorized Signatory"]], colWidths=[89*mm,89*mm])
    sign.setStyle(TableStyle([
        ("LINEABOVE",(0,0),(-1,0),0.5,colors.grey),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("TOPPADDING",(0,0),(-1,-1),4),
    ]))
    story.append(sign)
    if footer_note:
        story.append(Spacer(1, 3*mm))
        story.append(Paragraph(_pdf_text(footer_note), small))

    def footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(14*mm, 8*mm, _pdf_text(company))
        canvas.drawRightString(A4[0]-14*mm, 8*mm, f"Page {doc_obj.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


def service_call_pdf(row):
    return make_printable_pdf(
        "SERVICE REPORT",
        [("Report No.", row["call_no"]), ("Date", row["call_date"]),
         ("Client", row["client"]), ("Engineer", row["engineer"]),
         ("Site / Location", row["site"]), ("Visit Date", row["scheduled_date"])],
        [
            ("Service Details", [["Field", "Details"],
             ["Complaint / Requirement", row["complaint"]],
             ["Priority", row["priority"]], ["Status", row["status"]],
             ["Material Used", row["material"]], ["Remarks", row["remarks"]],
             ["Customer Feedback", row["customer_feedback"]]]),
        ],
        settings["service_terms"] if settings else "",
        "Service report generated from Pragati CRM."
    )


def quotation_pdf(row):
    taxable=float(row["subtotal"] or 0)-float(row["discount"] or 0)
    gst=float(row["gst"] or 0)
    return make_printable_pdf(
        "QUOTATION",
        [("Quotation No.", row["quotation_no"]), ("Date", row["quotation_date"]),
         ("Client", row["client"]), ("Status", row["status"])],
        [("Quotation Summary", [["Description", "Amount"],
          ["Subtotal", _pdf_money(row["subtotal"])],
          ["Discount", _pdf_money(row["discount"])],
          ["Taxable Amount", _pdf_money(taxable)],
          ["GST", _pdf_money(gst)],
          ["Grand Total", _pdf_money(row["total"])]]),
         ("Remarks", row["remarks"] or "")],
        row["terms"] or ""
    )


def challan_pdf(row):
    return make_printable_pdf(
        "DELIVERY CHALLAN",
        [("Challan No.", row["challan_no"]), ("Date", row["challan_date"]),
         ("Client", row["client"]), ("Status", row["status"])],
        [("Material Details", [["Material / Item", "Quantity", "Returnable"],
          [row["item"], row["quantity"], row["returnable"]]]),
         ("Remarks", row["remarks"] or "")],
        settings["challan_terms"] if settings else ""
    )


def invoice_pdf(row):
    taxable=float(row["subtotal"] or 0)-float(row["discount"] or 0)
    return make_printable_pdf(
        "TAX INVOICE",
        [("Invoice No.", row["invoice_no"]), ("Invoice Date", row["invoice_date"]),
         ("Client", row["client"]), ("Status", row["status"])],
        [("Invoice Summary", [["Description", "Amount"],
          ["Subtotal", _pdf_money(row["subtotal"])],
          ["Discount", _pdf_money(row["discount"])],
          ["Taxable Amount", _pdf_money(taxable)],
          ["GST", _pdf_money(row["gst"])],
          ["Grand Total", _pdf_money(row["total"])],
          ["Amount Received", _pdf_money(row["paid"])],
          ["Balance Due", _pdf_money(row["balance"])]]) ,
         ("Remarks", row["remarks"] or "")],
        row["terms"] or ""
    )


def salary_pdf(row):
    return make_printable_pdf(
        "SALARY SLIP",
        [("Salary Month", row["salary_month"]), ("Employee", row["engineer"]),
         ("Salary Type", row["salary_type"]), ("Status", row["status"])],
        [("Attendance & Salary", [["Particular", "Value"],
          ["Working Days", row["working_days"]], ["Present Days", row["present_days"]],
          ["Absent Days", row["absent_days"]], ["Total Working Hours", f"{float(row.get('total_hours', 0) or 0):.2f}"],
          ["OT Hours", f"{float(row['ot_hours'] or 0):.2f}"],
          ["OT Rate / Hour", _pdf_money(row.get('ot_rate', 0))],
          ["Basic Salary", _pdf_money(row["basic_salary"])],
          ["OT Amount", _pdf_money(row["ot_amount"])],
          ["Advance", _pdf_money(row["advance"])],
          ["Deduction", _pdf_money(row["deduction"])],
          ["Gross Salary", _pdf_money(row["gross_salary"])],
          ["Net Salary", _pdf_money(row["net_salary"])]] )],
        ""
    )


# ============================================================
# INITIAL DATABASE
# ============================================================

def init_db():

    conn = db()
    cur = conn.cursor()

    cur.executescript("""

    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY CHECK(id=1),
        company_name TEXT DEFAULT 'Pragati Enterprises',
        address TEXT,
        phone TEXT,
        email TEXT,
        gst TEXT,
        invoice_terms TEXT,
        quotation_terms TEXT,
        challan_terms TEXT,
        service_terms TEXT,
        whatsapp_enabled INTEGER DEFAULT 0,
        whatsapp_phone_number_id TEXT,
        whatsapp_access_token TEXT,
        whatsapp_api_version TEXT DEFAULT 'v23.0',
        whatsapp_language TEXT DEFAULT 'en_US',
        whatsapp_notify_punch INTEGER DEFAULT 1,
        whatsapp_notify_salary INTEGER DEFAULT 1,
        whatsapp_notify_service INTEGER DEFAULT 1,
        whatsapp_notify_invoice INTEGER DEFAULT 1,
        whatsapp_notify_amc INTEGER DEFAULT 1,
        whatsapp_template_punch_in TEXT DEFAULT 'attendance_in',
        whatsapp_template_punch_out TEXT DEFAULT 'attendance_out',
        whatsapp_template_salary TEXT DEFAULT 'salary_generated',
        whatsapp_template_service TEXT DEFAULT 'service_assigned',
        whatsapp_template_invoice TEXT DEFAULT 'invoice_generated',
        whatsapp_template_amc TEXT DEFAULT 'amc_reminder'
    );

    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        name TEXT,
        active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact TEXT,
        email TEXT,
        gst TEXT,
        address TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact TEXT,
        email TEXT,
        gst TEXT,
        address TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS engineers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        mobile TEXT,
        email TEXT,
        designation TEXT,
        salary_type TEXT DEFAULT 'Monthly',
        salary REAL DEFAULT 0,
        daily_rate REAL DEFAULT 0,
        working_days REAL DEFAULT 26,
        standard_hours REAL DEFAULT 8,
        ot_rate REAL DEFAULT 0,
        ot_multiplier REAL DEFAULT 1.5,
        joining_date TEXT,
        address TEXT,
        active INTEGER DEFAULT 1,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS service_calls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        call_no TEXT,
        client_id INTEGER,
        site TEXT,
        complaint TEXT,
        priority TEXT,
        engineer_id INTEGER,
        call_date TEXT,
        scheduled_date TEXT,
        status TEXT DEFAULT 'Open',
        material TEXT,
        remarks TEXT,
        customer_feedback TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        engineer_id INTEGER,
        attendance_date TEXT,
        in_time TEXT,
        out_time TEXT,
        status TEXT DEFAULT 'Present',
        hours REAL DEFAULT 0,
        remarks TEXT,
        UNIQUE(engineer_id, attendance_date)
    );

    CREATE TABLE IF NOT EXISTS amc (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        contract_no TEXT,
        start_date TEXT,
        end_date TEXT,
        amount REAL DEFAULT 0,
        visits INTEGER DEFAULT 0,
        next_service TEXT,
        status TEXT DEFAULT 'Active',
        remarks TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_code TEXT,
        item_name TEXT NOT NULL,
        category TEXT,
        unit TEXT,
        quantity REAL DEFAULT 0,
        min_stock REAL DEFAULT 0,
        purchase_rate REAL DEFAULT 0,
        selling_rate REAL DEFAULT 0,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS inventory_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER,
        transaction_type TEXT,
        quantity REAL,
        reference TEXT,
        transaction_date TEXT,
        remarks TEXT
    );

    CREATE TABLE IF NOT EXISTS quotations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quotation_no TEXT,
        client_id INTEGER,
        quotation_date TEXT,
        subtotal REAL DEFAULT 0,
        gst REAL DEFAULT 0,
        discount REAL DEFAULT 0,
        total REAL DEFAULT 0,
        status TEXT DEFAULT 'Draft',
        remarks TEXT,
        terms TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS challans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        challan_no TEXT,
        client_id INTEGER,
        challan_date TEXT,
        item TEXT,
        quantity REAL DEFAULT 0,
        returnable TEXT,
        status TEXT DEFAULT 'Delivered',
        remarks TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT,
        client_id INTEGER,
        invoice_date TEXT,
        subtotal REAL DEFAULT 0,
        gst REAL DEFAULT 0,
        discount REAL DEFAULT 0,
        total REAL DEFAULT 0,
        paid REAL DEFAULT 0,
        balance REAL DEFAULT 0,
        status TEXT DEFAULT 'Unpaid',
        remarks TEXT,
        terms TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        invoice_no TEXT,
        payment_date TEXT,
        amount REAL DEFAULT 0,
        mode TEXT,
        remarks TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS credit_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        credit_no TEXT,
        client_id INTEGER,
        invoice_no TEXT,
        credit_date TEXT,
        amount REAL DEFAULT 0,
        reason TEXT,
        adjusted REAL DEFAULT 0,
        balance REAL DEFAULT 0,
        status TEXT DEFAULT 'Open',
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS salary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        engineer_id INTEGER,
        salary_month TEXT,
        salary_type TEXT,
        basic_salary REAL DEFAULT 0,
        working_days REAL DEFAULT 0,
        present_days REAL DEFAULT 0,
        absent_days REAL DEFAULT 0,
        ot_hours REAL DEFAULT 0,
        ot_rate REAL DEFAULT 0,
        ot_amount REAL DEFAULT 0,
        total_hours REAL DEFAULT 0,
        advance REAL DEFAULT 0,
        deduction REAL DEFAULT 0,
        gross_salary REAL DEFAULT 0,
        net_salary REAL DEFAULT 0,
        status TEXT DEFAULT 'Pending',
        created_at TEXT
    );

    """)

    cur.execute("SELECT COUNT(*) FROM settings")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO settings
            (id, company_name, invoice_terms, quotation_terms,
             challan_terms, service_terms)
            VALUES
            (1, 'Pragati Enterprises',
             'Payment due as per agreed terms.',
             'Quotation valid for 30 days.',
             'Material received in good condition.',
             'Service subject to applicable terms and conditions.')
        """)

    # ========================================================
    # SCHEMA MIGRATIONS
    # CREATE TABLE IF NOT EXISTS does NOT add columns to an
    # existing SQLite table. These checks upgrade older DB files
    # without deleting existing data.
    # ========================================================

    def ensure_column(table, column, definition):
        existing = {
            row[1]
            for row in cur.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in existing:
            cur.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
            )

    migrations = {
        "settings": {
            "company_name": "TEXT DEFAULT 'Pragati Enterprises'",
            "address": "TEXT",
            "phone": "TEXT",
            "email": "TEXT",
            "gst": "TEXT",
            "invoice_terms": "TEXT",
            "quotation_terms": "TEXT",
            "challan_terms": "TEXT",
            "service_terms": "TEXT",
            "whatsapp_enabled": "INTEGER DEFAULT 0",
            "whatsapp_phone_number_id": "TEXT",
            "whatsapp_access_token": "TEXT",
            "whatsapp_api_version": "TEXT DEFAULT 'v23.0'",
            "whatsapp_language": "TEXT DEFAULT 'en_US'",
            "whatsapp_notify_punch": "INTEGER DEFAULT 1",
            "whatsapp_notify_salary": "INTEGER DEFAULT 1",
            "whatsapp_notify_service": "INTEGER DEFAULT 1",
            "whatsapp_notify_invoice": "INTEGER DEFAULT 1",
            "whatsapp_notify_amc": "INTEGER DEFAULT 1",
            "whatsapp_template_punch_in": "TEXT DEFAULT 'attendance_in'",
            "whatsapp_template_punch_out": "TEXT DEFAULT 'attendance_out'",
            "whatsapp_template_salary": "TEXT DEFAULT 'salary_generated'",
            "whatsapp_template_service": "TEXT DEFAULT 'service_assigned'",
            "whatsapp_template_invoice": "TEXT DEFAULT 'invoice_generated'",
            "whatsapp_template_amc": "TEXT DEFAULT 'amc_reminder'",
        },
        "admins": {
            "username": "TEXT",
            "password": "TEXT",
            "name": "TEXT",
            "active": "INTEGER DEFAULT 1",
        },
        "clients": {
            "name": "TEXT",
            "contact": "TEXT",
            "email": "TEXT",
            "gst": "TEXT",
            "address": "TEXT",
            "created_at": "TEXT",
        },
        "vendors": {
            "name": "TEXT",
            "contact": "TEXT",
            "email": "TEXT",
            "gst": "TEXT",
            "address": "TEXT",
            "created_at": "TEXT",
        },
        "engineers": {
            "name": "TEXT",
            "mobile": "TEXT",
            "email": "TEXT",
            "designation": "TEXT",
            "salary_type": "TEXT DEFAULT 'Monthly'",
            "salary": "REAL DEFAULT 0",
            "daily_rate": "REAL DEFAULT 0",
            "working_days": "REAL DEFAULT 26",
            "standard_hours": "REAL DEFAULT 8",
            "ot_rate": "REAL DEFAULT 0",
            "ot_multiplier": "REAL DEFAULT 1.5",
            "joining_date": "TEXT",
            "address": "TEXT",
            "active": "INTEGER DEFAULT 1",
            "created_at": "TEXT",
        },
        "service_calls": {
            "call_no": "TEXT",
            "client_id": "INTEGER",
            "site": "TEXT",
            "complaint": "TEXT",
            "priority": "TEXT",
            "engineer_id": "INTEGER",
            "call_date": "TEXT",
            "scheduled_date": "TEXT",
            "status": "TEXT DEFAULT 'Open'",
            "material": "TEXT",
            "remarks": "TEXT",
            "customer_feedback": "TEXT",
            "created_at": "TEXT",
        },
        "attendance": {
            "engineer_id": "INTEGER",
            "attendance_date": "TEXT",
            "in_time": "TEXT",
            "out_time": "TEXT",
            "status": "TEXT DEFAULT 'Present'",
            "hours": "REAL DEFAULT 0",
            "remarks": "TEXT",
        },
        "amc": {
            "client_id": "INTEGER",
            "contract_no": "TEXT",
            "start_date": "TEXT",
            "end_date": "TEXT",
            "amount": "REAL DEFAULT 0",
            "visits": "INTEGER DEFAULT 0",
            "next_service": "TEXT",
            "status": "TEXT DEFAULT 'Active'",
            "remarks": "TEXT",
            "created_at": "TEXT",
        },
        "inventory": {
            "item_code": "TEXT",
            "item_name": "TEXT",
            "category": "TEXT",
            "unit": "TEXT",
            "quantity": "REAL DEFAULT 0",
            "min_stock": "REAL DEFAULT 0",
            "purchase_rate": "REAL DEFAULT 0",
            "selling_rate": "REAL DEFAULT 0",
            "created_at": "TEXT",
        },
        "inventory_transactions": {
            "item_id": "INTEGER",
            "transaction_type": "TEXT",
            "quantity": "REAL",
            "reference": "TEXT",
            "transaction_date": "TEXT",
            "remarks": "TEXT",
        },
        "quotations": {
            "quotation_no": "TEXT",
            "client_id": "INTEGER",
            "quotation_date": "TEXT",
            "subtotal": "REAL DEFAULT 0",
            "gst": "REAL DEFAULT 0",
            "discount": "REAL DEFAULT 0",
            "total": "REAL DEFAULT 0",
            "status": "TEXT DEFAULT 'Draft'",
            "remarks": "TEXT",
            "terms": "TEXT",
            "created_at": "TEXT",
        },
        "challans": {
            "challan_no": "TEXT",
            "client_id": "INTEGER",
            "challan_date": "TEXT",
            "item": "TEXT",
            "quantity": "REAL DEFAULT 0",
            "returnable": "TEXT",
            "status": "TEXT DEFAULT 'Delivered'",
            "remarks": "TEXT",
            "created_at": "TEXT",
        },
        "invoices": {
            "invoice_no": "TEXT",
            "client_id": "INTEGER",
            "invoice_date": "TEXT",
            "subtotal": "REAL DEFAULT 0",
            "gst": "REAL DEFAULT 0",
            "discount": "REAL DEFAULT 0",
            "total": "REAL DEFAULT 0",
            "paid": "REAL DEFAULT 0",
            "balance": "REAL DEFAULT 0",
            "status": "TEXT DEFAULT 'Unpaid'",
            "remarks": "TEXT",
            "terms": "TEXT",
            "created_at": "TEXT",
        },
        "payments": {
            "client_id": "INTEGER",
            "invoice_no": "TEXT",
            "payment_date": "TEXT",
            "amount": "REAL DEFAULT 0",
            "mode": "TEXT",
            "remarks": "TEXT",
            "created_at": "TEXT",
        },
        "credit_notes": {
            "credit_no": "TEXT",
            "client_id": "INTEGER",
            "invoice_no": "TEXT",
            "credit_date": "TEXT",
            "amount": "REAL DEFAULT 0",
            "reason": "TEXT",
            "adjusted": "REAL DEFAULT 0",
            "balance": "REAL DEFAULT 0",
            "status": "TEXT DEFAULT 'Open'",
            "created_at": "TEXT",
        },
        "salary": {
            "engineer_id": "INTEGER",
            "salary_month": "TEXT",
            "salary_type": "TEXT",
            "basic_salary": "REAL DEFAULT 0",
            "working_days": "REAL DEFAULT 0",
            "present_days": "REAL DEFAULT 0",
            "absent_days": "REAL DEFAULT 0",
            "ot_hours": "REAL DEFAULT 0",
            "ot_rate": "REAL DEFAULT 0",
            "ot_amount": "REAL DEFAULT 0",
            "total_hours": "REAL DEFAULT 0",
            "advance": "REAL DEFAULT 0",
            "deduction": "REAL DEFAULT 0",
            "gross_salary": "REAL DEFAULT 0",
            "net_salary": "REAL DEFAULT 0",
            "status": "TEXT DEFAULT 'Pending'",
            "created_at": "TEXT",
        },
    }

    for table_name, columns in migrations.items():
        for column_name, definition in columns.items():
            ensure_column(table_name, column_name, definition)

    conn.commit()
    conn.close()


init_db()


# ============================================================
# ADMIN LOGIN
# ============================================================

def password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()


def create_default_admin():

    row = one("SELECT COUNT(*) c FROM admins")

    if row["c"] == 0:

        execute("""
            INSERT INTO admins(username,password,name)
            VALUES(?,?,?)
        """, (
            "admin",
            password_hash("admin123"),
            "Administrator"
        ))


create_default_admin()


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


if not st.session_state.logged_in:

    st.title("🏢 Pragati CRM")

    st.subheader("Admin Login")

    with st.form("login"):

        username = st.text_input("Username")
        password = st.text_input(
            "Password",
            type="password"
        )

        login = st.form_submit_button(
            "Login",
            use_container_width=True
        )

        if login:

            user = one("""
                SELECT *
                FROM admins
                WHERE username=? AND password=? AND active=1
            """, (
                username,
                password_hash(password)
            ))

            if user:

                st.session_state.logged_in = True
                st.session_state.admin_name = user["name"]
                st.rerun()

            else:
                st.error("Invalid username or password.")

    st.info(
        "First login: Username: admin | Password: admin123"
    )

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

settings = one("SELECT * FROM settings WHERE id=1")

st.sidebar.title("🏢 PRAGATI CRM")
st.sidebar.caption(settings["company_name"])

menu = st.sidebar.radio(
    "MENU",
    [
        "Dashboard",
        "Client Registration",
        "Vendor Registration",
        "Engineer / Technician",
        "Service Calls",
        "Attendance IN / OUT",
        "AMC Management",
        "Inventory",
        "Quotation",
        "Challan",
        "Bill / Invoice",
        "Credit Note",
        "Auto Adjustment",
        "Salary / Payroll",
        "Admin T&C",
        "Reports"
    ]
)

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()


# ============================================================
# DASHBOARD
# ============================================================

if menu == "Dashboard":

    st.title("📊 Dashboard")

    clients = one(
        "SELECT COUNT(*) c FROM clients"
    )["c"]

    vendors = one(
        "SELECT COUNT(*) c FROM vendors"
    )["c"]

    engineers = one(
        "SELECT COUNT(*) c FROM engineers WHERE active=1"
    )["c"]

    open_calls = one("""
        SELECT COUNT(*) c
        FROM service_calls
        WHERE status NOT IN ('Completed','Cancelled')
    """)["c"]

    amc_alert = one("""
        SELECT COUNT(*) c
        FROM amc
        WHERE date(end_date)
        BETWEEN date('now') AND date('now','+30 day')
    """)["c"]

    low_stock = one("""
        SELECT COUNT(*) c
        FROM inventory
        WHERE quantity <= min_stock
    """)["c"]

    outstanding = one("""
        SELECT COALESCE(SUM(balance),0) total
        FROM invoices
        WHERE balance > 0
    """)["total"]

    c1,c2,c3,c4 = st.columns(4)

    c1.metric("Clients", clients)
    c2.metric("Vendors", vendors)
    c3.metric("Engineers", engineers)
    c4.metric("Open Calls", open_calls)

    c5,c6,c7 = st.columns(3)

    c5.metric("AMC Alerts", amc_alert)
    c6.metric("Low Stock", low_stock)
    c7.metric("Outstanding", money(outstanding))

    st.divider()

    st.subheader("🔔 AMC Alerts")

    amc = query("""
        SELECT
            a.contract_no,
            c.name client,
            a.end_date,
            a.next_service,
            a.amount
        FROM amc a
        LEFT JOIN clients c
        ON a.client_id=c.id
        WHERE date(a.end_date)
        BETWEEN date('now') AND date('now','+30 day')
        ORDER BY date(a.end_date)
    """)

    if len(amc):
        st.warning("AMC expiry/service alert")
        st.dataframe(amc, use_container_width=True)
    else:
        st.success("No AMC alerts")

    st.subheader("🛠️ Pending Service Calls")

    calls = query("""
        SELECT
            s.call_no,
            c.name client,
            s.site,
            s.priority,
            e.name engineer,
            s.scheduled_date,
            s.status
        FROM service_calls s
        LEFT JOIN clients c ON s.client_id=c.id
        LEFT JOIN engineers e ON s.engineer_id=e.id
        WHERE s.status NOT IN ('Completed','Cancelled')
        ORDER BY s.id DESC
    """)

    st.dataframe(calls, use_container_width=True)


# ============================================================
# CLIENT
# ============================================================

elif menu == "Client Registration":

    st.title("👤 Client Registration")

    with st.form("client"):

        c1,c2 = st.columns(2)

        name = c1.text_input("Client / Company Name *")
        contact = c1.text_input("Mobile")
        email = c2.text_input("Email")
        gst = c2.text_input("GST")

        address = st.text_area("Address")

        save = st.form_submit_button(
            "Save Client",
            use_container_width=True
        )

        if save:

            if not name:
                st.error("Client name required.")
            else:

                execute("""
                    INSERT INTO clients
                    (name,contact,email,gst,address,created_at)
                    VALUES(?,?,?,?,?,?)
                """, (
                    name,contact,email,gst,address,now()
                ))

                st.success("Client added.")
                st.rerun()

    st.divider()

    st.dataframe(
        query("""
            SELECT id,name,contact,email,gst,address
            FROM clients
            ORDER BY id DESC
        """),
        use_container_width=True
    )


# ============================================================
# VENDOR
# ============================================================

elif menu == "Vendor Registration":

    st.title("🏭 Vendor Registration")

    with st.form("vendor"):

        c1,c2 = st.columns(2)

        name = c1.text_input("Vendor Name *")
        contact = c1.text_input("Mobile")
        email = c2.text_input("Email")
        gst = c2.text_input("GST")

        address = st.text_area("Address")

        save = st.form_submit_button(
            "Save Vendor",
            use_container_width=True
        )

        if save:

            if not name:
                st.error("Vendor name required.")
            else:

                execute("""
                    INSERT INTO vendors
                    (name,contact,email,gst,address,created_at)
                    VALUES(?,?,?,?,?,?)
                """, (
                    name,contact,email,gst,address,now()
                ))

                st.success("Vendor added.")
                st.rerun()

    st.divider()

    st.dataframe(
        query("""
            SELECT *
            FROM vendors
            ORDER BY id DESC
        """),
        use_container_width=True
    )


# ============================================================
# ENGINEER / TECHNICIAN
# ============================================================

elif menu == "Engineer / Technician":

    st.title("👷 Engineer / Technician Management")

    with st.form("engineer"):

        c1,c2,c3 = st.columns(3)

        name = c1.text_input("Engineer Name *")
        mobile = c2.text_input("Mobile")
        email = c3.text_input("Email")

        c1,c2,c3 = st.columns(3)

        designation = c1.text_input(
            "Designation",
            "Service Engineer"
        )

        salary_type = c2.selectbox(
            "Salary Type",
            [
                "Monthly",
                "Daily"
            ]
        )

        salary = c3.number_input(
            "Monthly Salary",
            min_value=0.0,
            step=500.0
        )

        daily_rate = st.number_input(
            "Daily Rate",
            min_value=0.0,
            step=100.0,
            help="Used when Salary Type is Daily."
        )

        c1,c2,c3 = st.columns(3)

        working_days = c1.number_input(
            "Salary Working Days / Month",
            min_value=1.0,
            max_value=31.0,
            value=26.0,
            step=1.0,
            help="For monthly salary calculation. Example: 26 working days."
        )

        standard_hours = c2.number_input(
            "Standard Hours / Day",
            min_value=1.0,
            max_value=24.0,
            value=8.0,
            step=0.5
        )

        ot_rate = c3.number_input(
            "OT Rate / Hour",
            min_value=0.0,
            value=0.0,
            step=10.0,
            help="Keep 0 for automatic 1.5x hourly rate."
        )

        ot_multiplier = st.number_input(
            "Automatic OT Multiplier",
            min_value=1.0,
            max_value=5.0,
            value=1.5,
            step=0.5,
            help="Used only when OT Rate / Hour is 0."
        )

        joining_date = st.date_input(
            "Joining Date",
            date.today()
        )

        address = st.text_area("Address")

        save = st.form_submit_button(
            "➕ Add Engineer",
            use_container_width=True
        )

        if save:

            if not name:
                st.error("Engineer name required.")
            else:

                execute("""
                    INSERT INTO engineers
                    (name,mobile,email,designation,
                     salary_type,salary,daily_rate,
                     working_days,standard_hours,ot_rate,ot_multiplier,
                     joining_date,address,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    name,
                    mobile,
                    email,
                    designation,
                    salary_type,
                    salary,
                    daily_rate,
                    working_days,
                    standard_hours,
                    ot_rate,
                    ot_multiplier,
                    str(joining_date),
                    address,
                    now()
                ))

                st.success("Engineer added.")
                st.rerun()

    st.divider()

    df = query("""
        SELECT
            id,
            name,
            mobile,
            designation,
            salary_type,
            salary,
            daily_rate,
            working_days,
            standard_hours,
            ot_rate,
            ot_multiplier,
            joining_date,
            CASE
                WHEN active=1 THEN 'Active'
                ELSE 'Inactive'
            END status
        FROM engineers
        ORDER BY id DESC
    """)

    st.dataframe(df, use_container_width=True)


# ============================================================
# SERVICE CALL + ASSIGN ENGINEER
# ============================================================

elif menu == "Service Calls":

    st.title("🛠️ Service Call Management")

    clients = query(
        "SELECT id,name FROM clients ORDER BY name"
    )

    engineers = query("""
        SELECT id,name
        FROM engineers
        WHERE active=1
        ORDER BY name
    """)

    if len(clients) == 0:
        st.warning("First register client.")
    elif len(engineers) == 0:
        st.warning("First register engineer.")
    else:

        client_map = dict(
            zip(clients["name"],clients["id"])
        )

        engineer_map = dict(
            zip(engineers["name"],engineers["id"])
        )

        with st.form("service_call"):

            call_no = st.text_input(
                "Call No.",
                f"CALL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            )

            c1,c2 = st.columns(2)

            client_name = c1.selectbox(
                "Client",
                list(client_map.keys())
            )

            engineer_name = c2.selectbox(
                "Assign Engineer",
                list(engineer_map.keys())
            )

            c1,c2,c3 = st.columns(3)

            site = c1.text_input("Site / Location")

            priority = c2.selectbox(
                "Priority",
                ["Low","Medium","High","Emergency"]
            )

            status = c3.selectbox(
                "Status",
                [
                    "Open",
                    "Assigned",
                    "In Progress",
                    "Completed",
                    "Cancelled"
                ]
            )

            complaint = st.text_area(
                "Complaint / Service Requirement"
            )

            c1,c2 = st.columns(2)

            call_date = c1.date_input(
                "Call Date",
                date.today()
            )

            scheduled_date = c2.date_input(
                "Visit / Schedule Date",
                date.today()
            )

            material = st.text_input(
                "Material Used"
            )

            remarks = st.text_area(
                "Remarks"
            )

            save = st.form_submit_button(
                "📌 Assign & Save Call",
                use_container_width=True
            )

            if save:

                execute("""
                    INSERT INTO service_calls
                    (call_no,client_id,site,complaint,
                     priority,engineer_id,call_date,
                     scheduled_date,status,material,
                     remarks,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    call_no,
                    client_map[client_name],
                    site,
                    complaint,
                    priority,
                    engineer_map[engineer_name],
                    str(call_date),
                    str(scheduled_date),
                    status,
                    material,
                    remarks,
                    now()
                ))

                st.success(
                    f"Call assigned to {engineer_name}"
                )

                st.rerun()

    st.divider()

    df = query("""
        SELECT
            s.id,
            s.call_no,
            c.name client,
            s.site,
            s.complaint,
            s.priority,
            e.name engineer,
            s.call_date,
            s.scheduled_date,
            s.status
        FROM service_calls s
        LEFT JOIN clients c
            ON s.client_id=c.id
        LEFT JOIN engineers e
            ON s.engineer_id=e.id
        ORDER BY s.id DESC
    """)

    st.dataframe(df, use_container_width=True)

    if len(df):
        st.subheader("🖨️ Printable Service Report PDF")
        service_options = [f"{r.call_no} | {r.client} | {r.call_date}" for _, r in df.iterrows()]
        service_selected = st.selectbox("Select service call to print", service_options, key="print_service_report")
        service_row = df.iloc[service_options.index(service_selected)]
        st.download_button(
            "🖨️ Download / Print Service Report PDF",
            service_call_pdf(service_row),
            f"service_report_{service_row['call_no']}.pdf",
            "application/pdf",
            use_container_width=True,
            key="download_service_report_pdf"
        )


# ============================================================
# ATTENDANCE IN / OUT
# ============================================================

elif menu == "Attendance IN / OUT":

    st.title("🕘 Engineer Attendance")

    engineers = query("""
        SELECT id,name
        FROM engineers
        WHERE active=1
        ORDER BY name
    """)

    if len(engineers) == 0:

        st.warning("No active engineers.")

    else:

        engineer_map = dict(
            zip(engineers["name"], engineers["id"])
        )

        selected = st.selectbox(
            "Engineer",
            list(engineer_map.keys())
        )

        engineer_id = engineer_map[selected]

        attendance_date = st.date_input(
            "Attendance Date",
            date.today()
        )

        existing = one("""
            SELECT *
            FROM attendance
            WHERE engineer_id=?
            AND attendance_date=?
        """, (
            engineer_id,
            str(attendance_date)
        ))

        if existing:

            c1,c2,c3 = st.columns(3)

            c1.metric(
                "IN",
                existing["in_time"] or "-"
            )

            c2.metric(
                "OUT",
                existing["out_time"] or "-"
            )

            c3.metric(
                "Hours",
                f"{existing['hours'] or 0:.2f}"
            )

        st.divider()

        c1,c2 = st.columns(2)

        if c1.button(
            "🟢 IN PUNCH",
            use_container_width=True
        ):

            current_time = datetime.now().strftime(
                "%H:%M:%S"
            )

            if existing:

                execute("""
                    UPDATE attendance
                    SET in_time=?, status='Present'
                    WHERE id=?
                """, (
                    current_time,
                    existing["id"]
                ))

            else:

                execute("""
                    INSERT INTO attendance
                    (engineer_id,attendance_date,
                     in_time,status)
                    VALUES(?,?,?,'Present')
                """, (
                    engineer_id,
                    str(attendance_date),
                    current_time
                ))

            st.success(
                f"IN Punch: {current_time}"
            )
            eng = one("SELECT name,mobile FROM engineers WHERE id=?", (engineer_id,))
            if eng and eng["mobile"]:
                ok, msg = whatsapp_notify("punch_in", eng["mobile"], [eng["name"], str(attendance_date), current_time])
                if ok:
                    st.info("WhatsApp IN notification sent.")
                elif whatsapp_configured()[0] and "Template not configured" not in msg:
                    st.warning(f"WhatsApp notification: {msg}")

            st.rerun()

        if c2.button(
            "🔴 OUT PUNCH",
            use_container_width=True
        ):

            current_time = datetime.now().strftime(
                "%H:%M:%S"
            )

            record = one("""
                SELECT *
                FROM attendance
                WHERE engineer_id=?
                AND attendance_date=?
            """, (
                engineer_id,
                str(attendance_date)
            ))

            if not record or not record["in_time"]:

                st.error(
                    "First perform IN Punch."
                )

            else:

                in_dt = datetime.strptime(
                    record["in_time"],
                    "%H:%M:%S"
                )

                out_dt = datetime.strptime(
                    current_time,
                    "%H:%M:%S"
                )

                seconds = (
                    out_dt - in_dt
                ).total_seconds()

                if seconds < 0:
                    seconds += 86400

                hours = seconds / 3600

                execute("""
                    UPDATE attendance
                    SET out_time=?, hours=?
                    WHERE id=?
                """, (
                    current_time,
                    hours,
                    record["id"]
                ))

                st.success(
                    f"OUT Punch: {current_time} | "
                    f"Working Hours: {hours:.2f}"
                )
                eng = one("SELECT name,mobile FROM engineers WHERE id=?", (engineer_id,))
                if eng and eng["mobile"]:
                    ok, msg = whatsapp_notify("punch_out", eng["mobile"], [eng["name"], str(attendance_date), current_time, f"{hours:.2f}"])
                    if ok:
                        st.info("WhatsApp OUT notification sent.")
                    elif whatsapp_configured()[0] and "Template not configured" not in msg:
                        st.warning(f"WhatsApp notification: {msg}")

                st.rerun()

    st.divider()

    df = query("""
        SELECT
            a.attendance_date,
            e.name engineer,
            a.in_time,
            a.out_time,
            a.hours,
            a.status,
            a.remarks
        FROM attendance a
        LEFT JOIN engineers e
            ON a.engineer_id=e.id
        ORDER BY a.attendance_date DESC
    """)

    st.dataframe(df, use_container_width=True)


# ============================================================
# AMC
# ============================================================

elif menu == "AMC Management":

    st.title("📅 AMC Management")

    clients = query(
        "SELECT id,name FROM clients ORDER BY name"
    )

    if len(clients) == 0:

        st.warning("First register client.")

    else:

        client_map = dict(
            zip(clients["name"],clients["id"])
        )

        with st.form("amc"):

            client_name = st.selectbox(
                "Client",
                list(client_map.keys())
            )

            c1,c2,c3 = st.columns(3)

            contract_no = c1.text_input(
                "AMC Contract No."
            )

            start = c2.date_input(
                "Start Date",
                date.today()
            )

            end = c3.date_input(
                "End Date",
                date.today()+timedelta(days=365)
            )

            amount = st.number_input(
                "AMC Amount",
                min_value=0.0,
                step=500.0
            )

            visits = st.number_input(
                "No. of Visits",
                min_value=0,
                step=1
            )

            next_service = st.date_input(
                "Next Service",
                date.today()+timedelta(days=30)
            )

            remarks = st.text_area("Remarks")

            save = st.form_submit_button(
                "Save AMC",
                use_container_width=True
            )

            if save:

                execute("""
                    INSERT INTO amc
                    (client_id,contract_no,start_date,end_date,
                     amount,visits,next_service,status,
                     remarks,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?)
                """, (
                    client_map[client_name],
                    contract_no,
                    str(start),
                    str(end),
                    amount,
                    visits,
                    str(next_service),
                    "Active",
                    remarks,
                    now()
                ))

                st.success("AMC saved.")
                st.rerun()

    st.divider()

    st.dataframe(
        query("""
            SELECT
                a.contract_no,
                c.name client,
                a.start_date,
                a.end_date,
                a.amount,
                a.visits,
                a.next_service,
                CASE
                    WHEN date(a.end_date)<date('now')
                        THEN 'EXPIRED'
                    WHEN date(a.end_date)
                        <=date('now','+30 day')
                        THEN 'EXPIRING SOON'
                    ELSE 'ACTIVE'
                END alert
            FROM amc a
            LEFT JOIN clients c
                ON a.client_id=c.id
            ORDER BY date(a.end_date)
        """),
        use_container_width=True
    )


# ============================================================
# INVENTORY
# ============================================================

elif menu == "Inventory":

    st.title("📦 Inventory Management")

    tab1,tab2 = st.tabs([
        "Add Item",
        "Stock Transaction"
    ])

    with tab1:

        with st.form("inventory"):

            c1,c2,c3 = st.columns(3)

            code = c1.text_input("Item Code")
            name = c2.text_input("Item Name *")
            category = c3.text_input("Category")

            c1,c2,c3,c4 = st.columns(4)

            unit = c1.text_input("Unit","Nos")

            qty = c2.number_input(
                "Opening Stock",
                min_value=0.0
            )

            min_stock = c3.number_input(
                "Minimum Stock",
                min_value=0.0
            )

            purchase = c4.number_input(
                "Purchase Rate",
                min_value=0.0
            )

            selling = st.number_input(
                "Selling Rate",
                min_value=0.0
            )

            save = st.form_submit_button(
                "Add Item",
                use_container_width=True
            )

            if save:

                if not name:
                    st.error("Item name required.")
                else:

                    item_id = execute("""
                        INSERT INTO inventory
                        (item_code,item_name,category,unit,
                         quantity,min_stock,purchase_rate,
                         selling_rate,created_at)
                        VALUES(?,?,?,?,?,?,?,?,?)
                    """, (
                        code,name,category,unit,
                        qty,min_stock,purchase,
                        selling,now()
                    ))

                    if qty > 0:

                        execute("""
                            INSERT INTO inventory_transactions
                            (item_id,transaction_type,quantity,
                             reference,transaction_date,remarks)
                            VALUES(?,?,?,?,?,?)
                        """, (
                            item_id,
                            "OPENING",
                            qty,
                            "Opening Stock",
                            str(date.today()),
                            ""
                        ))

                    st.success("Item added.")
                    st.rerun()

    with tab2:

        items = query(
            "SELECT id,item_name,quantity FROM inventory ORDER BY item_name"
        )

        if len(items):

            item_map = dict(
                zip(items["item_name"],items["id"])
            )

            item_name = st.selectbox(
                "Item",
                list(item_map.keys())
            )

            item_id = item_map[item_name]

            current_qty = float(
                items[
                    items["id"] == item_id
                ]["quantity"].iloc[0]
            )

            st.info(
                f"Current Stock: {current_qty}"
            )

            trans_type = st.selectbox(
                "Transaction",
                [
                    "PURCHASE",
                    "ISSUE",
                    "RETURN",
                    "DAMAGE",
                    "ADJUSTMENT"
                ]
            )

            trans_qty = st.number_input(
                "Quantity",
                min_value=0.0,
                step=1.0
            )

            reference = st.text_input(
                "Reference"
            )

            if st.button(
                "Update Stock",
                use_container_width=True
            ):

                if trans_type in ["PURCHASE","RETURN"]:
                    new_qty = current_qty + trans_qty
                else:
                    new_qty = current_qty - trans_qty

                if new_qty < 0:

                    st.error(
                        "Insufficient stock."
                    )

                else:

                    execute("""
                        UPDATE inventory
                        SET quantity=?
                        WHERE id=?
                    """, (
                        new_qty,
                        item_id
                    ))

                    execute("""
                        INSERT INTO inventory_transactions
                        (item_id,transaction_type,quantity,
                         reference,transaction_date)
                        VALUES(?,?,?,?,?)
                    """, (
                        item_id,
                        trans_type,
                        trans_qty,
                        reference,
                        str(date.today())
                    ))

                    st.success(
                        f"Stock updated: {new_qty}"
                    )

                    st.rerun()

    st.divider()

    st.dataframe(
        query("""
            SELECT
                item_code,
                item_name,
                category,
                unit,
                quantity,
                min_stock,
                purchase_rate,
                selling_rate,
                CASE
                    WHEN quantity<=min_stock
                    THEN 'LOW STOCK'
                    ELSE 'OK'
                END status
            FROM inventory
            ORDER BY item_name
        """),
        use_container_width=True
    )


# ============================================================
# QUOTATION
# ============================================================

elif menu == "Quotation":

    st.title("🧾 Quotation")

    clients = query(
        "SELECT id,name FROM clients ORDER BY name"
    )

    if len(clients):

        client_map = dict(
            zip(clients["name"],clients["id"])
        )

        with st.form("quotation"):

            quotation_no = st.text_input(
                "Quotation No.",
                f"QT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            )

            client = st.selectbox(
                "Client",
                list(client_map.keys())
            )

            quotation_date = st.date_input(
                "Date",
                date.today()
            )

            c1,c2,c3 = st.columns(3)

            subtotal = c1.number_input(
                "Subtotal",
                min_value=0.0
            )

            discount = c2.number_input(
                "Discount",
                min_value=0.0
            )

            gst_rate = c3.number_input(
                "GST %",
                value=18.0
            )

            taxable = max(
                subtotal-discount,
                0
            )

            gst = taxable*gst_rate/100
            total = taxable+gst

            st.success(
                f"Taxable: {money(taxable)} | "
                f"GST: {money(gst)} | "
                f"Total: {money(total)}"
            )

            status = st.selectbox(
                "Status",
                [
                    "Draft",
                    "Pending",
                    "Approved",
                    "Rejected",
                    "Converted"
                ]
            )

            terms = st.text_area(
                "Quotation T&C",
                settings["quotation_terms"]
            )

            save = st.form_submit_button(
                "Save Quotation",
                use_container_width=True
            )

            if save:

                execute("""
                    INSERT INTO quotations
                    (quotation_no,client_id,quotation_date,
                     subtotal,gst,discount,total,status,
                     remarks,terms,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    quotation_no,
                    client_map[client],
                    str(quotation_date),
                    subtotal,
                    gst,
                    discount,
                    total,
                    status,
                    "",
                    terms,
                    now()
                ))

                st.success("Quotation saved.")
                st.rerun()

    st.divider()

    quotation_list = query("""
        SELECT q.*, c.name client
        FROM quotations q
        LEFT JOIN clients c ON q.client_id=c.id
        ORDER BY q.id DESC
    """)

    st.dataframe(quotation_list[[
        "quotation_no", "client", "quotation_date", "subtotal",
        "discount", "gst", "total", "status"
    ]] if len(quotation_list) else quotation_list, use_container_width=True)

    if len(quotation_list):
        st.subheader("🖨️ Printable Quotation PDF")
        q_options = [f"{r.quotation_no} | {r.client} | {r.quotation_date}" for _, r in quotation_list.iterrows()]
        q_selected = st.selectbox("Select quotation to print", q_options, key="print_quotation")
        q_row = quotation_list.iloc[q_options.index(q_selected)]
        st.download_button(
            "🖨️ Download / Print Quotation PDF",
            quotation_pdf(q_row),
            f"quotation_{q_row['quotation_no']}.pdf",
            "application/pdf",
            use_container_width=True,
            key="download_quotation_pdf"
        )


# ============================================================
# CHALLAN
# ============================================================

elif menu == "Challan":

    st.title("🚚 Delivery Challan")

    clients = query(
        "SELECT id,name FROM clients ORDER BY name"
    )

    if len(clients):

        client_map = dict(
            zip(clients["name"],clients["id"])
        )

        with st.form("challan"):

            challan_no = st.text_input(
                "Challan No.",
                f"DC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            )

            client = st.selectbox(
                "Client",
                list(client_map.keys())
            )

            challan_date = st.date_input(
                "Date",
                date.today()
            )

            item = st.text_input(
                "Material / Item"
            )

            qty = st.number_input(
                "Quantity",
                min_value=0.0
            )

            returnable = st.selectbox(
                "Returnable",
                ["No","Yes"]
            )

            status = st.selectbox(
                "Status",
                [
                    "Delivered",
                    "Pending Return",
                    "Returned"
                ]
            )

            remarks = st.text_area("Remarks")

            save = st.form_submit_button(
                "Create Challan",
                use_container_width=True
            )

            if save:

                execute("""
                    INSERT INTO challans
                    (challan_no,client_id,challan_date,
                     item,quantity,returnable,status,
                     remarks,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?)
                """, (
                    challan_no,
                    client_map[client],
                    str(challan_date),
                    item,
                    qty,
                    returnable,
                    status,
                    remarks,
                    now()
                ))

                st.success("Challan created.")
                st.rerun()

    st.divider()

    challan_list = query("""
        SELECT ch.*, c.name client
        FROM challans ch
        LEFT JOIN clients c ON ch.client_id=c.id
        ORDER BY ch.id DESC
    """)

    st.dataframe(challan_list[[
        "challan_no", "client", "challan_date", "item",
        "quantity", "returnable", "status"
    ]] if len(challan_list) else challan_list, use_container_width=True)

    if len(challan_list):
        st.subheader("🖨️ Printable Delivery Challan PDF")
        ch_options = [f"{r.challan_no} | {r.client} | {r.challan_date}" for _, r in challan_list.iterrows()]
        ch_selected = st.selectbox("Select challan to print", ch_options, key="print_challan")
        ch_row = challan_list.iloc[ch_options.index(ch_selected)]
        st.download_button(
            "🖨️ Download / Print Challan PDF",
            challan_pdf(ch_row),
            f"challan_{ch_row['challan_no']}.pdf",
            "application/pdf",
            use_container_width=True,
            key="download_challan_pdf"
        )


# ============================================================
# INVOICE
# ============================================================

elif menu == "Bill / Invoice":

    st.title("💰 Bill / Invoice")

    clients = query(
        "SELECT id,name FROM clients ORDER BY name"
    )

    if len(clients):

        client_map = dict(
            zip(clients["name"],clients["id"])
        )

        with st.form("invoice"):

            invoice_no = st.text_input(
                "Invoice No.",
                f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            )

            client = st.selectbox(
                "Client",
                list(client_map.keys())
            )

            invoice_date = st.date_input(
                "Invoice Date",
                date.today()
            )

            c1,c2,c3 = st.columns(3)

            subtotal = c1.number_input(
                "Subtotal",
                min_value=0.0
            )

            discount = c2.number_input(
                "Discount",
                min_value=0.0
            )

            gst_rate = c3.number_input(
                "GST %",
                value=18.0
            )

            paid = st.number_input(
                "Amount Received",
                min_value=0.0
            )

            taxable = max(
                subtotal-discount,
                0
            )

            gst = taxable*gst_rate/100
            total = taxable+gst
            balance = max(total-paid,0)

            if balance == 0:
                status = "Paid"
            elif paid > 0:
                status = "Partially Paid"
            else:
                status = "Unpaid"

            st.info(
                f"Total: {money(total)} | "
                f"Paid: {money(paid)} | "
                f"Balance: {money(balance)}"
            )

            terms = st.text_area(
                "Invoice T&C",
                settings["invoice_terms"]
            )

            save = st.form_submit_button(
                "Save Invoice",
                use_container_width=True
            )

            if save:

                execute("""
                    INSERT INTO invoices
                    (invoice_no,client_id,invoice_date,
                     subtotal,gst,discount,total,
                     paid,balance,status,
                     remarks,terms,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    invoice_no,
                    client_map[client],
                    str(invoice_date),
                    subtotal,
                    gst,
                    discount,
                    total,
                    paid,
                    balance,
                    status,
                    "",
                    terms,
                    now()
                ))

                if paid > 0:

                    execute("""
                        INSERT INTO payments
                        (client_id,invoice_no,payment_date,
                         amount,mode,remarks,created_at)
                        VALUES(?,?,?,?,?,?,?)
                    """, (
                        client_map[client],
                        invoice_no,
                        str(invoice_date),
                        paid,
                        "Cash/Bank/UPI",
                        "Initial Payment",
                        now()
                    ))

                st.success("Invoice saved.")
                st.rerun()

    st.divider()

    invoice_list = query("""
        SELECT i.*, c.name client
        FROM invoices i
        LEFT JOIN clients c ON i.client_id=c.id
        ORDER BY i.id DESC
    """)

    st.dataframe(invoice_list[[
        "invoice_no", "client", "invoice_date", "total",
        "paid", "balance", "status"
    ]] if len(invoice_list) else invoice_list, use_container_width=True)

    if len(invoice_list):
        st.subheader("🖨️ Printable Bill / Invoice PDF")
        inv_options = [f"{r.invoice_no} | {r.client} | {r.invoice_date}" for _, r in invoice_list.iterrows()]
        inv_selected = st.selectbox("Select invoice to print", inv_options, key="print_invoice")
        inv_row = invoice_list.iloc[inv_options.index(inv_selected)]
        st.download_button(
            "🖨️ Download / Print Bill PDF",
            invoice_pdf(inv_row),
            f"invoice_{inv_row['invoice_no']}.pdf",
            "application/pdf",
            use_container_width=True,
            key="download_invoice_pdf"
        )


# ============================================================
# CREDIT NOTE
# ============================================================

elif menu == "Credit Note":

    st.title("↩️ Credit Note")

    clients = query(
        "SELECT id,name FROM clients ORDER BY name"
    )

    if len(clients):

        client_map = dict(
            zip(clients["name"],clients["id"])
        )

        with st.form("credit"):

            credit_no = st.text_input(
                "Credit Note No.",
                f"CN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            )

            client = st.selectbox(
                "Client",
                list(client_map.keys())
            )

            invoice_no = st.text_input(
                "Against Invoice"
            )

            credit_date = st.date_input(
                "Date",
                date.today()
            )

            amount = st.number_input(
                "Credit Amount",
                min_value=0.0
            )

            reason = st.text_area(
                "Reason"
            )

            save = st.form_submit_button(
                "Create Credit Note",
                use_container_width=True
            )

            if save:

                execute("""
                    INSERT INTO credit_notes
                    (credit_no,client_id,invoice_no,
                     credit_date,amount,reason,
                     adjusted,balance,status,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?)
                """, (
                    credit_no,
                    client_map[client],
                    invoice_no,
                    str(credit_date),
                    amount,
                    reason,
                    0,
                    amount,
                    "Open",
                    now()
                ))

                st.success("Credit Note created.")
                st.rerun()

    st.divider()

    st.dataframe(
        query("""
            SELECT
                cn.credit_no,
                c.name client,
                cn.invoice_no,
                cn.credit_date,
                cn.amount,
                cn.adjusted,
                cn.balance,
                cn.status
            FROM credit_notes cn
            LEFT JOIN clients c
                ON cn.client_id=c.id
            ORDER BY cn.id DESC
        """),
        use_container_width=True
    )


# ============================================================
# AUTO ADJUSTMENT
# ============================================================

elif menu == "Auto Adjustment":

    st.title("🔄 Automatic Adjustment")

    invoices = query("""
        SELECT
            i.id,
            i.invoice_no,
            c.name client,
            i.balance
        FROM invoices i
        LEFT JOIN clients c
            ON i.client_id=c.id
        WHERE i.balance>0
        ORDER BY i.id
    """)

    credits = query("""
        SELECT
            cn.id,
            cn.credit_no,
            c.name client,
            cn.balance
        FROM credit_notes cn
        LEFT JOIN clients c
            ON cn.client_id=c.id
        WHERE cn.balance>0
        ORDER BY cn.id
    """)

    if len(invoices)==0:

        st.success(
            "No outstanding invoice."
        )

    elif len(credits)==0:

        st.success(
            "No open credit note."
        )

    else:

        invoice_options = [
            f"{r.invoice_no} | {r.client} | ₹{r.balance:,.2f}"
            for _,r in invoices.iterrows()
        ]

        credit_options = [
            f"{r.credit_no} | {r.client} | ₹{r.balance:,.2f}"
            for _,r in credits.iterrows()
        ]

        selected_invoice = st.selectbox(
            "Invoice",
            invoice_options
        )

        selected_credit = st.selectbox(
            "Credit Note",
            credit_options
        )

        inv = invoices.iloc[
            invoice_options.index(selected_invoice)
        ]

        cr = credits.iloc[
            credit_options.index(selected_credit)
        ]

        max_amount = min(
            float(inv["balance"]),
            float(cr["balance"])
        )

        adjustment = st.number_input(
            "Adjustment Amount",
            min_value=0.0,
            max_value=max_amount,
            value=max_amount
        )

        if st.button(
            "🔄 AUTO ADJUST",
            type="primary",
            use_container_width=True
        ):

            invoice_balance = (
                float(inv["balance"]) -
                adjustment
            )

            credit_balance = (
                float(cr["balance"]) -
                adjustment
            )

            invoice_status = (
                "Paid"
                if invoice_balance <= 0
                else "Partially Paid"
            )

            credit_status = (
                "Adjusted"
                if credit_balance <= 0
                else "Partially Adjusted"
            )

            execute("""
                UPDATE invoices
                SET balance=?,status=?
                WHERE id=?
            """, (
                invoice_balance,
                invoice_status,
                int(inv["id"])
            ))

            execute("""
                UPDATE credit_notes
                SET adjusted=adjusted+?,
                    balance=?,
                    status=?
                WHERE id=?
            """, (
                adjustment,
                credit_balance,
                credit_status,
                int(cr["id"])
            ))

            st.success(
                f"{money(adjustment)} automatically adjusted."
            )

            st.rerun()


# ============================================================
# SALARY / PAYROLL
# ============================================================

elif menu == "Salary / Payroll":

    st.title("💵 Salary / Payroll")
    st.caption("Automatic salary from IN/OUT attendance, present days and daily OT.")

    engineers = query("""
        SELECT
            id,name,salary_type,salary,daily_rate,
            working_days,standard_hours,ot_rate,ot_multiplier
        FROM engineers
        WHERE active=1
        ORDER BY name
    """)

    if len(engineers) == 0:
        st.warning("First add engineer.")
    else:
        engineer_map = dict(zip(engineers["name"], engineers["id"]))
        engineer_name = st.selectbox("Engineer", list(engineer_map.keys()))
        engineer_id = engineer_map[engineer_name]
        eng = engineers[engineers["id"] == engineer_id].iloc[0]

        c1,c2 = st.columns(2)
        salary_type = c1.selectbox(
            "Salary Calculation",
            ["Monthly", "Daily"],
            index=0 if str(eng["salary_type"] or "Monthly") == "Monthly" else 1
        )
        salary_month = c2.date_input("Salary Month", date.today())

        year, month = salary_month.year, salary_month.month
        days_in_month = calendar.monthrange(year, month)[1]

        configured_working_days = float(eng["working_days"] or 26)
        standard_hours = float(eng["standard_hours"] or 8)
        stored_ot_rate = float(eng["ot_rate"] or 0)
        ot_multiplier = float(eng["ot_multiplier"] or 1.5)

        c1,c2,c3,c4 = st.columns(4)
        working_day_basis = c1.number_input(
            "Working Days Basis",
            min_value=1.0,
            max_value=float(days_in_month),
            value=min(configured_working_days, float(days_in_month)),
            step=1.0,
            help="Monthly salary is prorated against this number of working days."
        )
        day_hours = c2.number_input(
            "Standard Hours / Day",
            min_value=1.0,
            max_value=24.0,
            value=standard_hours,
            step=0.5
        )
        ot_rate = c3.number_input(
            "OT Rate / Hour",
            min_value=0.0,
            value=stored_ot_rate,
            step=10.0,
            help="0 = automatic hourly rate × OT multiplier."
        )
        ot_mult = c4.number_input(
            "OT Multiplier",
            min_value=1.0,
            max_value=5.0,
            value=ot_multiplier,
            step=0.5
        )

        attendance = query("""
            SELECT attendance_date,in_time,out_time,hours,status,remarks
            FROM attendance
            WHERE engineer_id=?
              AND substr(attendance_date,1,7)=?
            ORDER BY attendance_date
        """, (engineer_id, f"{year:04d}-{month:02d}"))

        present_days = int((attendance["status"] == "Present").sum()) if len(attendance) else 0
        total_hours = float(attendance["hours"].fillna(0).sum()) if len(attendance) else 0.0

        # OT is calculated day-by-day, so a short day cannot cancel OT from another day.
        ot_hours = 0.0
        if len(attendance):
            for _, a in attendance.iterrows():
                if str(a.get("status", "")) == "Present":
                    ot_hours += max(float(a.get("hours", 0) or 0) - day_hours, 0.0)

        absent_days = max(working_day_basis - present_days, 0.0)

        if salary_type == "Daily":
            daily_rate = float(eng["daily_rate"] or 0)
            basic_salary = present_days * daily_rate
            salary_basis_text = f"{present_days} × {money(daily_rate)}"
        else:
            monthly_salary = float(eng["salary"] or 0)
            basic_salary = monthly_salary * min(present_days, working_day_basis) / working_day_basis
            salary_basis_text = f"{money(monthly_salary)} ÷ {working_day_basis:g} × {present_days}"

        if ot_rate > 0:
            effective_ot_rate = ot_rate
            ot_source = "Fixed OT rate"
        else:
            hourly_base = (basic_salary / max(present_days * day_hours, 1)) if salary_type == "Daily" else (float(eng["salary"] or 0) / max(working_day_basis * day_hours, 1))
            effective_ot_rate = hourly_base * ot_mult
            ot_source = f"Automatic {ot_mult:g}× hourly rate"

        ot_amount = ot_hours * effective_ot_rate

        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Present", present_days)
        c2.metric("Absent", f"{absent_days:g}")
        c3.metric("Total Hours", f"{total_hours:.2f}")
        c4.metric("OT Hours", f"{ot_hours:.2f}")
        c5.metric("OT Amount", money(ot_amount))

        st.info(
            f"Salary basis: {salary_basis_text} | "
            f"OT: {money(effective_ot_rate)}/hour ({ot_source})"
        )

        # Attendance details for verification before salary generation.
        with st.expander("📋 Attendance details", expanded=False):
            if len(attendance):
                view = attendance.copy()
                view["OT Hours"] = view.apply(
                    lambda r: max(float(r["hours"] or 0) - day_hours, 0.0) if r["status"] == "Present" else 0.0,
                    axis=1
                )
                st.dataframe(view, use_container_width=True)
            else:
                st.warning("No attendance punch found for this month.")

        advance = st.number_input("Advance", min_value=0.0, step=100.0)
        deduction = st.number_input("Other Deduction", min_value=0.0, step=100.0)

        gross_salary = basic_salary + ot_amount
        net_salary = max(gross_salary - advance - deduction, 0.0)

        c1,c2,c3 = st.columns(3)
        c1.metric("Basic Salary", money(basic_salary))
        c2.metric("Gross Salary", money(gross_salary))
        c3.metric("Net Salary", money(net_salary))

        if st.button("💾 Generate / Update Salary", type="primary", use_container_width=True):
            existing_salary = one("""
                SELECT id FROM salary
                WHERE engineer_id=? AND salary_month=?
                ORDER BY id DESC LIMIT 1
            """, (engineer_id, f"{year:04d}-{month:02d}"))

            values = (
                salary_type, basic_salary, working_day_basis, present_days,
                absent_days, ot_hours, effective_ot_rate, ot_amount, total_hours,
                advance, deduction, gross_salary, net_salary, "Pending"
            )

            if existing_salary:
                execute("""
                    UPDATE salary SET
                        salary_type=?, basic_salary=?, working_days=?, present_days=?,
                        absent_days=?, ot_hours=?, ot_rate=?, ot_amount=?, total_hours=?,
                        advance=?, deduction=?, gross_salary=?, net_salary=?, status=?, created_at=?
                    WHERE id=?
                """, values + (now(), int(existing_salary["id"])))
                st.success(f"Salary updated: {money(net_salary)}")
            else:
                execute("""
                    INSERT INTO salary
                    (engineer_id,salary_month,salary_type,basic_salary,working_days,
                     present_days,absent_days,ot_hours,ot_rate,ot_amount,total_hours,
                     advance,deduction,gross_salary,net_salary,status,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (engineer_id, f"{year:04d}-{month:02d}") + values + (now(),))
                st.success(f"Salary generated: {money(net_salary)}")
            eng_phone = one("SELECT name,mobile FROM engineers WHERE id=?", (engineer_id,))
            if eng_phone and eng_phone["mobile"]:
                ok, msg = whatsapp_notify(
                    "salary", eng_phone["mobile"],
                    [eng_phone["name"], f"{year:04d}-{month:02d}", f"{present_days:g}", f"{ot_hours:.2f}", f"{net_salary:.2f}"]
                )
                if ok:
                    st.info("WhatsApp salary notification sent.")
                elif whatsapp_configured()[0] and "Template not configured" not in msg:
                    st.warning(f"WhatsApp notification: {msg}")
            st.rerun()

    st.divider()
    st.subheader("Salary History")

    salary_history = query("""
        SELECT s.*, e.name engineer
        FROM salary s
        LEFT JOIN engineers e ON s.engineer_id=e.id
        ORDER BY s.id DESC
    """)

    st.dataframe(salary_history[[
        "salary_month", "engineer", "salary_type", "working_days", "present_days",
        "absent_days", "total_hours", "ot_hours", "ot_rate", "basic_salary", "ot_amount",
        "advance", "deduction", "gross_salary", "net_salary", "status"
    ]] if len(salary_history) else salary_history, use_container_width=True)

    if len(salary_history):
        st.subheader("🖨️ Printable Salary Slip PDF")
        sal_options = [f"{r.salary_month} | {r.engineer} | {money(r.net_salary)}" for _, r in salary_history.iterrows()]
        sal_selected = st.selectbox("Select salary slip to print", sal_options, key="print_salary")
        sal_row = salary_history.iloc[sal_options.index(sal_selected)]
        st.download_button(
            "🖨️ Download / Print Salary Slip PDF",
            salary_pdf(sal_row),
            f"salary_slip_{sal_row['engineer']}_{sal_row['salary_month']}.pdf",
            "application/pdf",
            use_container_width=True,
            key="download_salary_pdf"
        )


# ============================================================
# ADMIN T&C
# ============================================================

elif menu == "Admin T&C":

    st.title("⚙️ Admin Settings & T&C")

    st.info(
        "Yahan se administrator company details aur "
        "Quotation / Invoice / Challan / Service ke T&C "
        "khud change kar sakta hai."
    )

    company_name = st.text_input(
        "Company Name",
        settings["company_name"] or ""
    )

    address = st.text_area(
        "Company Address",
        settings["address"] or ""
    )

    c1,c2,c3 = st.columns(3)

    phone = c1.text_input(
        "Phone",
        settings["phone"] or ""
    )

    email = c2.text_input(
        "Email",
        settings["email"] or ""
    )

    gst = c3.text_input(
        "GST",
        settings["gst"] or ""
    )

    st.subheader("Quotation T&C")

    quotation_terms = st.text_area(
        "Quotation Terms",
        settings["quotation_terms"] or "",
        height=150
    )

    st.subheader("Invoice T&C")

    invoice_terms = st.text_area(
        "Invoice Terms",
        settings["invoice_terms"] or "",
        height=150
    )

    st.subheader("Challan T&C")

    challan_terms = st.text_area(
        "Challan Terms",
        settings["challan_terms"] or "",
        height=150
    )

    st.subheader("Service T&C")

    service_terms = st.text_area(
        "Service Terms",
        settings["service_terms"] or "",
        height=150
    )

    st.divider()
    st.subheader("📲 WhatsApp Cloud API Notifications")
    st.caption("Use an approved Meta WhatsApp template for business-initiated notifications. Keep the access token in Streamlit Secrets when possible.")
    wa_enabled = st.checkbox("Enable WhatsApp notifications", value=bool(_setting_value("whatsapp_enabled", 0)))
    c1,c2,c3 = st.columns(3)
    wa_phone_id = c1.text_input("Phone Number ID", _setting_value("whatsapp_phone_number_id", ""))
    wa_api_version = c2.text_input("Graph API Version", _setting_value("whatsapp_api_version", "v23.0"))
    wa_language = c3.text_input("Template Language", _setting_value("whatsapp_language", "en_US"))
    wa_token = st.text_input("Access Token (prefer Streamlit Secrets)", _setting_value("whatsapp_access_token", ""), type="password")
    if wa_enabled and not wa_token:
        st.info("Recommended: add WHATSAPP_ACCESS_TOKEN in Streamlit Cloud → Settings → Secrets.")
    st.markdown("**Notification templates** (these names must match approved WhatsApp templates)")
    c1,c2 = st.columns(2)
    wa_t_in = c1.text_input("IN Punch template", _setting_value("whatsapp_template_punch_in", "attendance_in"))
    wa_t_out = c2.text_input("OUT Punch template", _setting_value("whatsapp_template_punch_out", "attendance_out"))
    c1,c2 = st.columns(2)
    wa_t_salary = c1.text_input("Salary template", _setting_value("whatsapp_template_salary", "salary_generated"))
    wa_t_service = c2.text_input("Service Call template", _setting_value("whatsapp_template_service", "service_assigned"))
    c1,c2 = st.columns(2)
    wa_t_invoice = c1.text_input("Invoice template", _setting_value("whatsapp_template_invoice", "invoice_generated"))
    wa_t_amc = c2.text_input("AMC template", _setting_value("whatsapp_template_amc", "amc_reminder"))
    c1,c2,c3,c4,c5 = st.columns(5)
    wa_n_punch = c1.checkbox("Punch", value=bool(_setting_value("whatsapp_notify_punch", 1)))
    wa_n_salary = c2.checkbox("Salary", value=bool(_setting_value("whatsapp_notify_salary", 1)))
    wa_n_service = c3.checkbox("Service", value=bool(_setting_value("whatsapp_notify_service", 1)))
    wa_n_invoice = c4.checkbox("Invoice", value=bool(_setting_value("whatsapp_notify_invoice", 1)))
    wa_n_amc = c5.checkbox("AMC", value=bool(_setting_value("whatsapp_notify_amc", 1)))

    test_number = st.text_input("Test WhatsApp number", placeholder="10-digit Indian mobile or full country code")
    if st.button("📲 SEND TEST WHATSAPP", use_container_width=True):
        ok, msg = whatsapp_send_template(
            test_number, wa_t_in or "hello_world",
            ["Test Employee", str(date.today()), datetime.now().strftime("%H:%M:%S")]
        )
        if ok:
            st.success("Test WhatsApp message sent successfully.")
        else:
            st.error(f"WhatsApp test failed: {msg}")

    if st.button(
        "💾 SAVE ADMIN SETTINGS",
        type="primary",
        use_container_width=True
    ):

        execute("""
            UPDATE settings
            SET company_name=?,
                address=?,
                phone=?,
                email=?,
                gst=?,
                invoice_terms=?,
                quotation_terms=?,
                challan_terms=?,
                service_terms=?,
                whatsapp_enabled=?,
                whatsapp_phone_number_id=?,
                whatsapp_access_token=?,
                whatsapp_api_version=?,
                whatsapp_language=?,
                whatsapp_notify_punch=?,
                whatsapp_notify_salary=?,
                whatsapp_notify_service=?,
                whatsapp_notify_invoice=?,
                whatsapp_notify_amc=?,
                whatsapp_template_punch_in=?,
                whatsapp_template_punch_out=?,
                whatsapp_template_salary=?,
                whatsapp_template_service=?,
                whatsapp_template_invoice=?,
                whatsapp_template_amc=?
            WHERE id=1
        """, (
            company_name,
            address,
            phone,
            email,
            gst,
            invoice_terms,
            quotation_terms,
            challan_terms,
            service_terms,
            int(wa_enabled), wa_phone_id, wa_token, wa_api_version, wa_language,
            int(wa_n_punch), int(wa_n_salary), int(wa_n_service), int(wa_n_invoice), int(wa_n_amc),
            wa_t_in, wa_t_out, wa_t_salary, wa_t_service, wa_t_invoice, wa_t_amc
        ))

        st.success(
            "Admin settings & T&C updated."
        )

        st.rerun()


# ============================================================
# REPORTS
# ============================================================

elif menu == "Reports":

    st.title("📈 Reports")

    report = st.selectbox(
        "Report",
        [
            "Clients",
            "Vendors",
            "Engineers",
            "Service Calls",
            "Attendance",
            "AMC",
            "Inventory",
            "Inventory Transactions",
            "Quotations",
            "Challans",
            "Invoices",
            "Payments",
            "Credit Notes",
            "Salary"
        ]
    )

    reports = {

        "Clients":
        "SELECT * FROM clients ORDER BY id DESC",

        "Vendors":
        "SELECT * FROM vendors ORDER BY id DESC",

        "Engineers":
        "SELECT * FROM engineers ORDER BY id DESC",

        "Service Calls":
        """
        SELECT
            s.*,
            c.name client,
            e.name engineer
        FROM service_calls s
        LEFT JOIN clients c ON s.client_id=c.id
        LEFT JOIN engineers e ON s.engineer_id=e.id
        ORDER BY s.id DESC
        """,

        "Attendance":
        """
        SELECT
            a.*,
            e.name engineer
        FROM attendance a
        LEFT JOIN engineers e ON a.engineer_id=e.id
        ORDER BY a.attendance_date DESC
        """,

        "AMC":
        """
        SELECT
            a.*,
            c.name client
        FROM amc a
        LEFT JOIN clients c ON a.client_id=c.id
        ORDER BY a.id DESC
        """,

        "Inventory":
        "SELECT * FROM inventory ORDER BY id DESC",

        "Inventory Transactions":
        "SELECT * FROM inventory_transactions ORDER BY id DESC",

        "Quotations":
        """
        SELECT
            q.*,
            c.name client
        FROM quotations q
        LEFT JOIN clients c ON q.client_id=c.id
        ORDER BY q.id DESC
        """,

        "Challans":
        """
        SELECT
            ch.*,
            c.name client
        FROM challans ch
        LEFT JOIN clients c ON ch.client_id=c.id
        ORDER BY ch.id DESC
        """,

        "Invoices":
        """
        SELECT
            i.*,
            c.name client
        FROM invoices i
        LEFT JOIN clients c ON i.client_id=c.id
        ORDER BY i.id DESC
        """,

        "Payments":
        """
        SELECT
            p.*,
            c.name client
        FROM payments p
        LEFT JOIN clients c ON p.client_id=c.id
        ORDER BY p.id DESC
        """,

        "Credit Notes":
        """
        SELECT
            cn.*,
            c.name client
        FROM credit_notes cn
        LEFT JOIN clients c ON cn.client_id=c.id
        ORDER BY cn.id DESC
        """,

        "Salary":
        """
        SELECT
            s.*,
            e.name engineer
        FROM salary s
        LEFT JOIN engineers e ON s.engineer_id=e.id
        ORDER BY s.id DESC
        """
    }

    df = query(reports[report])

    st.dataframe(
        df,
        use_container_width=True,
        height=550
    )

    if len(df):

        csv = df.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "⬇️ Download CSV",
            csv,
            f"{report.lower().replace(' ','_')}.csv",
            "text/csv",
            use_container_width=True
        )


# ============================================================
# FOOTER
# ============================================================

st.sidebar.divider()

st.sidebar.caption(
    f"{settings['company_name']} | "
    f"{date.today().strftime('%d-%m-%Y')}"
)
