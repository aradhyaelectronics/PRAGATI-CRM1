from pathlib import Path

source = Path("/mnt/data/Pasted text.txt")
output = Path("/mnt/data/app_fixed.py")
text = source.read_text(encoding="utf-8")

marker = "    conn.commit()\n    conn.close()\n\n\ninit_db()\n"
if marker not in text:
    raise RuntimeError("Could not find init_db ending marker.")

replacement = '''    # ========================================================
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
            "ot_amount": "REAL DEFAULT 0",
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
'''

fixed = text.replace(marker, replacement)
output.write_text(fixed, encoding="utf-8")

# Basic syntax validation before giving the file to the user.
import ast
ast.parse(fixed)

print(f"Fixed app created: {output}")
print(f"Lines: {len(fixed.splitlines())}")
print("Python syntax check: OK")
