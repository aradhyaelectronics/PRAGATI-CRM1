import streamlit as st
import sqlite3
from datetime import date, datetime, timedelta
import pandas as pd

# =========================================================
# PRAGATI CRM - SERVICE / AMC / INVENTORY / BILLING
# Single Page Streamlit Application
# =========================================================

st.set_page_config(
    page_title="Pragati CRM",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB = "pragati_crm.db"


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
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

    CREATE TABLE IF NOT EXISTS service_calls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        site TEXT,
        complaint TEXT,
        priority TEXT,
        technician TEXT,
        call_date TEXT,
        status TEXT DEFAULT 'Open',
        material TEXT,
        remarks TEXT,
        created_at TEXT
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
    """)

    conn.commit()
    conn.close()


init_db()


# =========================================================
# HELPERS
# =========================================================

def execute(query, params=()):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id


def fetchall(query, params=()):
    conn = get_db()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def fetchone(query, params=()):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(query, params)
    row = cur.fetchone()
    conn.close()
    return row


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def money(value):
    return f"₹{float(value or 0):,.2f}"


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("🏢 PRAGATI CRM")
st.sidebar.caption("Service & Business Management")

menu = st.sidebar.radio(
    "MAIN MENU",
    [
        "Dashboard",
        "Client Registration",
        "Vendor Registration",
        "Service Calls",
        "AMC Management",
        "Inventory",
        "Quotation",
        "Challan",
        "Bill / Invoice",
        "Credit Note",
        "Auto Adjustment",
        "Reports"
    ]
)

st.sidebar.divider()
st.sidebar.info("Pragati CRM")


# =========================================================
# DASHBOARD
# =========================================================

if menu == "Dashboard":

    st.title("📊 Pragati CRM Dashboard")

    clients = fetchone("SELECT COUNT(*) c FROM clients")["c"]
    vendors = fetchone("SELECT COUNT(*) c FROM vendors")["c"]
    services = fetchone(
        "SELECT COUNT(*) c FROM service_calls WHERE status != 'Completed'"
    )["c"]

    amc_expiring = fetchone("""
        SELECT COUNT(*) c
        FROM amc
        WHERE date(end_date) BETWEEN date('now') AND date('now', '+30 day')
    """)["c"]

    inventory_low = fetchone("""
        SELECT COUNT(*) c
        FROM inventory
        WHERE quantity <= min_stock
    """)["c"]

    quotation_pending = fetchone("""
        SELECT COUNT(*) c
        FROM quotations
        WHERE status IN ('Draft','Pending')
    """)["c"]

    outstanding = fetchone("""
        SELECT COALESCE(SUM(balance),0) total
        FROM invoices
        WHERE balance > 0
    """)["total"]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Clients", clients)
    c2.metric("Vendors", vendors)
    c3.metric("Open Service Calls", services)
    c4.metric("AMC Alert", amc_expiring)

    c5, c6, c7 = st.columns(3)

    c5.metric("Low Stock Items", inventory_low)
    c6.metric("Pending Quotations", quotation_pending)
    c7.metric("Outstanding", money(outstanding))

    st.divider()

    st.subheader("🔔 Alerts")

    alert_df = fetchall("""
        SELECT contract_no, end_date, status
        FROM amc
        WHERE date(end_date) BETWEEN date('now') AND date('now', '+30 day')
        ORDER BY date(end_date)
    """)

    if len(alert_df):
        st.warning("⚠️ AMC contracts expiring within 30 days")
        st.dataframe(alert_df, use_container_width=True)
    else:
        st.success("✅ No AMC expiry alerts")

    low_df = fetchall("""
        SELECT item_code, item_name, quantity, min_stock
        FROM inventory
        WHERE quantity <= min_stock
    """)

    if len(low_df):
        st.warning("⚠️ Low Inventory")
        st.dataframe(low_df, use_container_width=True)

    st.subheader("📌 Recent Service Calls")

    df = fetchall("""
        SELECT
            s.id,
            c.name AS client,
            s.site,
            s.complaint,
            s.priority,
            s.technician,
            s.call_date,
            s.status
        FROM service_calls s
        LEFT JOIN clients c ON s.client_id = c.id
        ORDER BY s.id DESC
        LIMIT 10
    """)

    st.dataframe(df, use_container_width=True)


# =========================================================
# CLIENT
# =========================================================

elif menu == "Client Registration":

    st.title("👤 Client Registration")

    with st.form("client_form"):

        c1, c2 = st.columns(2)

        name = c1.text_input("Client / Company Name *")
        contact = c1.text_input("Contact Number")
        email = c2.text_input("Email")
        gst = c2.text_input("GST Number")

        address = st.text_area("Address")

        submit = st.form_submit_button(
            "➕ Add Client",
            use_container_width=True
        )

        if submit:

            if not name:
                st.error("Client name is required.")
            else:

                execute("""
                    INSERT INTO clients
                    (name, contact, email, gst, address, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    name,
                    contact,
                    email,
                    gst,
                    address,
                    now()
                ))

                st.success("Client registered successfully.")
                st.rerun()

    st.divider()

    df = fetchall("""
        SELECT id, name, contact, email, gst, address
        FROM clients
        ORDER BY id DESC
    """)

    st.dataframe(df, use_container_width=True)


# =========================================================
# VENDOR
# =========================================================

elif menu == "Vendor Registration":

    st.title("🏭 Vendor Registration")

    with st.form("vendor_form"):

        c1, c2 = st.columns(2)

        name = c1.text_input("Vendor / Company Name *")
        contact = c1.text_input("Contact Number")
        email = c2.text_input("Email")
        gst = c2.text_input("GST Number")

        address = st.text_area("Address")

        submit = st.form_submit_button(
            "➕ Add Vendor",
            use_container_width=True
        )

        if submit:

            if not name:
                st.error("Vendor name is required.")
            else:

                execute("""
                    INSERT INTO vendors
                    (name, contact, email, gst, address, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    name,
                    contact,
                    email,
                    gst,
                    address,
                    now()
                ))

                st.success("Vendor added.")
                st.rerun()

    st.divider()

    df = fetchall("""
        SELECT id, name, contact, email, gst, address
        FROM vendors
        ORDER BY id DESC
    """)

    st.dataframe(df, use_container_width=True)


# =========================================================
# SERVICE CALL
# =========================================================

elif menu == "Service Calls":

    st.title("🛠️ Service Call Management")

    clients = fetchall("SELECT id, name FROM clients ORDER BY name")

    if len(clients) == 0:
        st.warning("Please register a client first.")
    else:

        client_map = dict(
            zip(clients["name"], clients["id"])
        )

        with st.form("service_form"):

            client_name = st.selectbox(
                "Client",
                list(client_map.keys())
            )

            c1, c2, c3 = st.columns(3)

            site = c1.text_input("Site / Location")
            priority = c2.selectbox(
                "Priority",
                ["Low", "Medium", "High", "Emergency"]
            )
            technician = c3.text_input("Technician / Engineer")

            complaint = st.text_area("Complaint / Service Requirement")

            c1, c2 = st.columns(2)

            call_date = c1.date_input("Call Date", date.today())

            status = c2.selectbox(
                "Status",
                ["Open", "Assigned", "In Progress", "Completed", "Cancelled"]
            )

            material = st.text_input("Material Used")
            remarks = st.text_area("Remarks")

            submit = st.form_submit_button(
                "➕ Create Service Call",
                use_container_width=True
            )

            if submit:

                execute("""
                    INSERT INTO service_calls
                    (client_id, site, complaint, priority,
                     technician, call_date, status, material,
                     remarks, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    client_map[client_name],
                    site,
                    complaint,
                    priority,
                    technician,
                    str(call_date),
                    status,
                    material,
                    remarks,
                    now()
                ))

                st.success("Service call created.")
                st.rerun()

    st.divider()

    df = fetchall("""
        SELECT
            s.id,
            c.name AS client,
            s.site,
            s.complaint,
            s.priority,
            s.technician,
            s.call_date,
            s.status
        FROM service_calls s
        LEFT JOIN clients c ON s.client_id = c.id
        ORDER BY s.id DESC
    """)

    st.dataframe(df, use_container_width=True)


# =========================================================
# AMC
# =========================================================

elif menu == "AMC Management":

    st.title("📅 AMC Management")

    clients = fetchall("SELECT id, name FROM clients ORDER BY name")

    if len(clients) == 0:
        st.warning("Please register a client first.")
    else:

        client_map = dict(zip(clients["name"], clients["id"]))

        with st.form("amc_form"):

            client_name = st.selectbox(
                "Client",
                list(client_map.keys())
            )

            c1, c2, c3 = st.columns(3)

            contract_no = c1.text_input("AMC Contract No.")
            start_date = c2.date_input(
                "Start Date",
                date.today()
            )
            end_date = c3.date_input(
                "End Date",
                date.today() + timedelta(days=365)
            )

            c1, c2 = st.columns(2)

            amount = c1.number_input(
                "AMC Amount",
                min_value=0.0,
                step=100.0
            )

            visits = c2.number_input(
                "No. of Visits",
                min_value=0,
                step=1
            )

            next_service = st.date_input(
                "Next Service Date",
                date.today() + timedelta(days=30)
            )

            remarks = st.text_area("Remarks")

            submit = st.form_submit_button(
                "➕ Add AMC",
                use_container_width=True
            )

            if submit:

                execute("""
                    INSERT INTO amc
                    (client_id, contract_no, start_date, end_date,
                     amount, visits, next_service, status,
                     remarks, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    client_map[client_name],
                    contract_no,
                    str(start_date),
                    str(end_date),
                    amount,
                    visits,
                    str(next_service),
                    "Active",
                    remarks,
                    now()
                ))

                st.success("AMC created successfully.")
                st.rerun()

    st.divider()

    df = fetchall("""
        SELECT
            a.id,
            c.name AS client,
            a.contract_no,
            a.start_date,
            a.end_date,
            a.amount,
            a.visits,
            a.next_service,
            CASE
                WHEN date(a.end_date) < date('now')
                    THEN 'Expired'
                WHEN date(a.end_date) <= date('now', '+30 day')
                    THEN 'Expiring Soon'
                ELSE a.status
            END AS alert
        FROM amc a
        LEFT JOIN clients c ON a.client_id = c.id
        ORDER BY date(a.end_date)
    """)

    st.dataframe(df, use_container_width=True)


# =========================================================
# INVENTORY
# =========================================================

elif menu == "Inventory":

    st.title("📦 Inventory Management")

    with st.form("inventory_form"):

        c1, c2, c3 = st.columns(3)

        item_code = c1.text_input("Item Code")
        item_name = c2.text_input("Item Name *")
        category = c3.text_input("Category")

        c1, c2, c3, c4 = st.columns(4)

        unit = c1.text_input("Unit", "Nos")
        quantity = c2.number_input(
            "Opening Quantity",
            min_value=0.0,
            step=1.0
        )
        min_stock = c3.number_input(
            "Minimum Stock",
            min_value=0.0,
            step=1.0
        )
        purchase_rate = c4.number_input(
            "Purchase Rate",
            min_value=0.0,
            step=1.0
        )

        selling_rate = st.number_input(
            "Selling Rate",
            min_value=0.0,
            step=1.0
        )

        submit = st.form_submit_button(
            "➕ Add Inventory Item",
            use_container_width=True
        )

        if submit:

            if not item_name:
                st.error("Item name is required.")
            else:

                execute("""
                    INSERT INTO inventory
                    (item_code, item_name, category, unit,
                     quantity, min_stock, purchase_rate,
                     selling_rate, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item_code,
                    item_name,
                    category,
                    unit,
                    quantity,
                    min_stock,
                    purchase_rate,
                    selling_rate,
                    now()
                ))

                st.success("Inventory item added.")
                st.rerun()

    st.divider()

    df = fetchall("""
        SELECT
            id,
            item_code,
            item_name,
            category,
            unit,
            quantity,
            min_stock,
            purchase_rate,
            selling_rate,
            CASE
                WHEN quantity <= min_stock THEN 'LOW STOCK'
                ELSE 'OK'
            END AS stock_status
        FROM inventory
        ORDER BY item_name
    """)

    st.dataframe(df, use_container_width=True)


# =========================================================
# QUOTATION
# =========================================================

elif menu == "Quotation":

    st.title("🧾 Quotation Management")

    clients = fetchall("SELECT id, name FROM clients ORDER BY name")

    if len(clients) == 0:
        st.warning("Please register a client first.")
    else:

        client_map = dict(zip(clients["name"], clients["id"]))

        with st.form("quotation_form"):

            c1, c2 = st.columns(2)

            quotation_no = c1.text_input(
                "Quotation No.",
                f"QT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            )

            client_name = c2.selectbox(
                "Client",
                list(client_map.keys())
            )

            quotation_date = st.date_input(
                "Quotation Date",
                date.today()
            )

            c1, c2, c3 = st.columns(3)

            subtotal = c1.number_input(
                "Subtotal",
                min_value=0.0,
                step=100.0
            )

            discount = c2.number_input(
                "Discount",
                min_value=0.0,
                step=100.0
            )

            gst_rate = c3.number_input(
                "GST %",
                min_value=0.0,
                value=18.0,
                step=1.0
            )

            taxable = max(subtotal - discount, 0)
            gst = taxable * gst_rate / 100
            total = taxable + gst

            st.info(
                f"Taxable: {money(taxable)} | "
                f"GST: {money(gst)} | "
                f"Total: {money(total)}"
            )

            status = st.selectbox(
                "Status",
                ["Draft", "Pending", "Approved", "Rejected", "Converted"]
            )

            remarks = st.text_area("Terms / Remarks")

            submit = st.form_submit_button(
                "💾 Save Quotation",
                use_container_width=True
            )

            if submit:

                execute("""
                    INSERT INTO quotations
                    (quotation_no, client_id, quotation_date,
                     subtotal, gst, discount, total,
                     status, remarks, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    quotation_no,
                    client_map[client_name],
                    str(quotation_date),
                    subtotal,
                    gst,
                    discount,
                    total,
                    status,
                    remarks,
                    now()
                ))

                st.success("Quotation saved.")
                st.rerun()

    st.divider()

    df = fetchall("""
        SELECT
            q.id,
            q.quotation_no,
            c.name AS client,
            q.quotation_date,
            q.subtotal,
            q.discount,
            q.gst,
            q.total,
            q.status
        FROM quotations q
        LEFT JOIN clients c ON q.client_id = c.id
        ORDER BY q.id DESC
    """)

    st.dataframe(df, use_container_width=True)


# =========================================================
# CHALLAN
# =========================================================

elif menu == "Challan":

    st.title("🚚 Delivery Challan")

    clients = fetchall("SELECT id, name FROM clients ORDER BY name")

    if len(clients) == 0:
        st.warning("Please register a client first.")
    else:

        client_map = dict(zip(clients["name"], clients["id"]))

        with st.form("challan_form"):

            c1, c2 = st.columns(2)

            challan_no = c1.text_input(
                "Challan No.",
                f"DC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            )

            client_name = c2.selectbox(
                "Client",
                list(client_map.keys())
            )

            challan_date = st.date_input(
                "Challan Date",
                date.today()
            )

            c1, c2, c3 = st.columns(3)

            item = c1.text_input("Item / Material")
            quantity = c2.number_input(
                "Quantity",
                min_value=0.0,
                step=1.0
            )
            returnable = c3.selectbox(
                "Returnable?",
                ["No", "Yes"]
            )

            status = st.selectbox(
                "Status",
                ["Delivered", "Returned", "Pending Return"]
            )

            remarks = st.text_area("Remarks")

            submit = st.form_submit_button(
                "💾 Create Challan",
                use_container_width=True
            )

            if submit:

                execute("""
                    INSERT INTO challans
                    (challan_no, client_id, challan_date,
                     item, quantity, returnable, status,
                     remarks, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    challan_no,
                    client_map[client_name],
                    str(challan_date),
                    item,
                    quantity,
                    returnable,
                    status,
                    remarks,
                    now()
                ))

                st.success("Challan created.")
                st.rerun()

    st.divider()

    df = fetchall("""
        SELECT
            ch.id,
            ch.challan_no,
            c.name AS client,
            ch.challan_date,
            ch.item,
            ch.quantity,
            ch.returnable,
            ch.status
        FROM challans ch
        LEFT JOIN clients c ON ch.client_id = c.id
        ORDER BY ch.id DESC
    """)

    st.dataframe(df, use_container_width=True)


# =========================================================
# BILL / INVOICE
# =========================================================

elif menu == "Bill / Invoice":

    st.title("💰 Bill / Invoice")

    clients = fetchall("SELECT id, name FROM clients ORDER BY name")

    if len(clients) == 0:
        st.warning("Please register a client first.")
    else:

        client_map = dict(zip(clients["name"], clients["id"]))

        with st.form("invoice_form"):

            c1, c2 = st.columns(2)

            invoice_no = c1.text_input(
                "Invoice No.",
                f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            )

            client_name = c2.selectbox(
                "Client",
                list(client_map.keys())
            )

            invoice_date = st.date_input(
                "Invoice Date",
                date.today()
            )

            c1, c2, c3 = st.columns(3)

            subtotal = c1.number_input(
                "Subtotal",
                min_value=0.0,
                step=100.0
            )

            discount = c2.number_input(
                "Discount",
                min_value=0.0,
                step=100.0
            )

            gst_rate = c3.number_input(
                "GST %",
                min_value=0.0,
                value=18.0,
                step=1.0
            )

            paid = st.number_input(
                "Amount Received",
                min_value=0.0,
                step=100.0
            )

            taxable = max(subtotal - discount, 0)
            gst = taxable * gst_rate / 100
            total = taxable + gst
            balance = max(total - paid, 0)

            if balance == 0:
                invoice_status = "Paid"
            elif paid > 0:
                invoice_status = "Partially Paid"
            else:
                invoice_status = "Unpaid"

            st.info(
                f"Total: {money(total)} | "
                f"Paid: {money(paid)} | "
                f"Balance: {money(balance)}"
            )

            remarks = st.text_area("Remarks")

            submit = st.form_submit_button(
                "💾 Save Invoice",
                use_container_width=True
            )

            if submit:

                execute("""
                    INSERT INTO invoices
                    (invoice_no, client_id, invoice_date,
                     subtotal, gst, discount, total,
                     paid, balance, status,
                     remarks, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    invoice_no,
                    client_map[client_name],
                    str(invoice_date),
                    subtotal,
                    gst,
                    discount,
                    total,
                    paid,
                    balance,
                    invoice_status,
                    remarks,
                    now()
                ))

                if paid > 0:

                    execute("""
                        INSERT INTO payments
                        (client_id, invoice_no, payment_date,
                         amount, mode, remarks, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        client_map[client_name],
                        invoice_no,
                        str(invoice_date),
                        paid,
                        "Cash/Bank/UPI",
                        "Initial invoice payment",
                        now()
                    ))

                st.success("Invoice saved successfully.")
                st.rerun()

    st.divider()

    df = fetchall("""
        SELECT
            i.id,
            i.invoice_no,
            c.name AS client,
            i.invoice_date,
            i.total,
            i.paid,
            i.balance,
            i.status
        FROM invoices i
        LEFT JOIN clients c ON i.client_id = c.id
        ORDER BY i.id DESC
    """)

    st.dataframe(df, use_container_width=True)


# =========================================================
# CREDIT NOTE
# =========================================================

elif menu == "Credit Note":

    st.title("↩️ Credit Note")

    clients = fetchall("SELECT id, name FROM clients ORDER BY name")

    if len(clients) == 0:
        st.warning("Please register a client first.")
    else:

        client_map = dict(zip(clients["name"], clients["id"]))

        with st.form("credit_form"):

            c1, c2 = st.columns(2)

            credit_no = c1.text_input(
                "Credit Note No.",
                f"CN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            )

            client_name = c2.selectbox(
                "Client",
                list(client_map.keys())
            )

            invoice_no = st.text_input(
                "Against Invoice No."
            )

            credit_date = st.date_input(
                "Credit Date",
                date.today()
            )

            amount = st.number_input(
                "Credit Amount",
                min_value=0.0,
                step=100.0
            )

            reason = st.text_area("Reason")

            submit = st.form_submit_button(
                "💾 Create Credit Note",
                use_container_width=True
            )

            if submit:

                execute("""
                    INSERT INTO credit_notes
                    (credit_no, client_id, invoice_no,
                     credit_date, amount, reason,
                     adjusted, balance, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    credit_no,
                    client_map[client_name],
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

    df = fetchall("""
        SELECT
            cn.id,
            cn.credit_no,
            c.name AS client,
            cn.invoice_no,
            cn.credit_date,
            cn.amount,
            cn.adjusted,
            cn.balance,
            cn.status
        FROM credit_notes cn
        LEFT JOIN clients c ON cn.client_id = c.id
        ORDER BY cn.id DESC
    """)

    st.dataframe(df, use_container_width=True)


# =========================================================
# AUTO ADJUSTMENT
# =========================================================

elif menu == "Auto Adjustment":

    st.title("🔄 Auto Adjustment")

    st.info(
        "Credit Note ko outstanding invoice ke against automatically adjust karein."
    )

    invoices = fetchall("""
        SELECT
            i.id,
            i.invoice_no,
            c.name AS client,
            i.balance
        FROM invoices i
        LEFT JOIN clients c ON i.client_id = c.id
        WHERE i.balance > 0
        ORDER BY i.id
    """)

    credits = fetchall("""
        SELECT
            cn.id,
            cn.credit_no,
            c.name AS client,
            cn.balance
        FROM credit_notes cn
        LEFT JOIN clients c ON cn.client_id = c.id
        WHERE cn.balance > 0
        ORDER BY cn.id
    """)

    if len(invoices) == 0:
        st.success("No outstanding invoices.")
    elif len(credits) == 0:
        st.success("No open credit notes.")
    else:

        invoice_options = [
            f"{r.invoice_no} | {r.client} | Balance ₹{r.balance:,.2f}"
            for _, r in invoices.iterrows()
        ]

        credit_options = [
            f"{r.credit_no} | {r.client} | Credit ₹{r.balance:,.2f}"
            for _, r in credits.iterrows()
        ]

        selected_invoice = st.selectbox(
            "Select Invoice",
            invoice_options
        )

        selected_credit = st.selectbox(
            "Select Credit Note",
            credit_options
        )

        inv_index = invoice_options.index(selected_invoice)
        cr_index = credit_options.index(selected_credit)

        invoice = invoices.iloc[inv_index]
        credit = credits.iloc[cr_index]

        max_adjust = min(
            float(invoice["balance"]),
            float(credit["balance"])
        )

        adjustment = st.number_input(
            "Adjustment Amount",
            min_value=0.0,
            max_value=max_adjust,
            value=max_adjust,
            step=100.0
        )

        if st.button(
            "🔄 Auto Adjust",
            use_container_width=True,
            type="primary"
        ):

            new_invoice_balance = (
                float(invoice["balance"]) - adjustment
            )

            new_credit_balance = (
                float(credit["balance"]) - adjustment
            )

            invoice_status = (
                "Paid"
                if new_invoice_balance <= 0
                else "Partially Paid"
            )

            credit_status = (
                "Adjusted"
                if new_credit_balance <= 0
                else "Partially Adjusted"
            )

            execute("""
                UPDATE invoices
                SET balance = ?, status = ?
                WHERE id = ?
            """, (
                new_invoice_balance,
                invoice_status,
                int(invoice["id"])
            ))

            execute("""
                UPDATE credit_notes
                SET adjusted = adjusted + ?,
                    balance = ?,
                    status = ?
                WHERE id = ?
            """, (
                adjustment,
                new_credit_balance,
                credit_status,
                int(credit["id"])
            ))

            st.success(
                f"{money(adjustment)} successfully adjusted."
            )

            st.rerun()


# =========================================================
# REPORTS
# =========================================================

elif menu == "Reports":

    st.title("📈 Reports")

    report = st.selectbox(
        "Select Report",
        [
            "Clients",
            "Vendors",
            "Service Calls",
            "AMC",
            "Inventory",
            "Quotations",
            "Challans",
            "Invoices",
            "Credit Notes",
            "Payments"
        ]
    )

    queries = {

        "Clients": """
            SELECT * FROM clients ORDER BY id DESC
        """,

        "Vendors": """
            SELECT * FROM vendors ORDER BY id DESC
        """,

        "Service Calls": """
            SELECT
                s.*,
                c.name AS client_name
            FROM service_calls s
            LEFT JOIN clients c ON s.client_id = c.id
            ORDER BY s.id DESC
        """,

        "AMC": """
            SELECT
                a.*,
                c.name AS client_name
            FROM amc a
            LEFT JOIN clients c ON a.client_id = c.id
            ORDER BY a.id DESC
        """,

        "Inventory": """
            SELECT * FROM inventory ORDER BY id DESC
        """,

        "Quotations": """
            SELECT
                q.*,
                c.name AS client_name
            FROM quotations q
            LEFT JOIN clients c ON q.client_id = c.id
            ORDER BY q.id DESC
        """,

        "Challans": """
            SELECT
                ch.*,
                c.name AS client_name
            FROM challans ch
            LEFT JOIN clients c ON ch.client_id = c.id
            ORDER BY ch.id DESC
        """,

        "Invoices": """
            SELECT
                i.*,
                c.name AS client_name
            FROM invoices i
            LEFT JOIN clients c ON i.client_id = c.id
            ORDER BY i.id DESC
        """,

        "Credit Notes": """
            SELECT
                cn.*,
                c.name AS client_name
            FROM credit_notes cn
            LEFT JOIN clients c ON cn.client_id = c.id
            ORDER BY cn.id DESC
        """,

        "Payments": """
            SELECT
                p.*,
                c.name AS client_name
            FROM payments p
            LEFT JOIN clients c ON p.client_id = c.id
            ORDER BY p.id DESC
        """
    }

    df = fetchall(queries[report])

    st.dataframe(
        df,
        use_container_width=True,
        height=500
    )

    if len(df):

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "⬇️ Export Excel/CSV",
            csv,
            f"{report.lower().replace(' ', '_')}.csv",
            "text/csv",
            use_container_width=True
        )


# =========================================================
# FOOTER
# =========================================================

st.sidebar.divider()
st.sidebar.caption(
    f"Pragati CRM • {datetime.now().strftime('%d-%m-%Y')}"
)
