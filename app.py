import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime, timedelta
import calendar
import hashlib

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
        service_terms TEXT
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
        ot_amount REAL DEFAULT 0,
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
            step=100.0
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
                     joining_date,address,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?)
                """, (
                    name,
                    mobile,
                    email,
                    designation,
                    salary_type,
                    salary,
                    daily_rate,
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

    st.dataframe(
        query("""
            SELECT
                q.quotation_no,
                c.name client,
                q.quotation_date,
                q.subtotal,
                q.discount,
                q.gst,
                q.total,
                q.status
            FROM quotations q
            LEFT JOIN clients c
                ON q.client_id=c.id
            ORDER BY q.id DESC
        """),
        use_container_width=True
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

    st.dataframe(
        query("""
            SELECT
                ch.challan_no,
                c.name client,
                ch.challan_date,
                ch.item,
                ch.quantity,
                ch.returnable,
                ch.status
            FROM challans ch
            LEFT JOIN clients c
                ON ch.client_id=c.id
            ORDER BY ch.id DESC
        """),
        use_container_width=True
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

    st.dataframe(
        query("""
            SELECT
                i.invoice_no,
                c.name client,
                i.invoice_date,
                i.total,
                i.paid,
                i.balance,
                i.status
            FROM invoices i
            LEFT JOIN clients c
                ON i.client_id=c.id
            ORDER BY i.id DESC
        """),
        use_container_width=True
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

    engineers = query("""
        SELECT
            id,
            name,
            salary_type,
            salary,
            daily_rate
        FROM engineers
        WHERE active=1
        ORDER BY name
    """)

    if len(engineers)==0:

        st.warning(
            "First add engineer."
        )

    else:

        engineer_map = dict(
            zip(engineers["name"],engineers["id"])
        )

        engineer_name = st.selectbox(
            "Engineer",
            list(engineer_map.keys())
        )

        engineer_id = engineer_map[engineer_name]

        eng = engineers[
            engineers["id"]==engineer_id
        ].iloc[0]

        salary_type = st.selectbox(
            "Salary Calculation",
            [
                "Monthly",
                "Daily"
            ]
        )

        salary_month = st.date_input(
            "Salary Month",
            date.today()
        )

        year = salary_month.year
        month = salary_month.month

        days_in_month = calendar.monthrange(
            year,
            month
        )[1]

        attendance = query("""
            SELECT
                attendance_date,
                hours,
                status
            FROM attendance
            WHERE engineer_id=?
            AND substr(attendance_date,1,7)=?
        """, (
            engineer_id,
            f"{year:04d}-{month:02d}"
        ))

        present_days = len(
            attendance[
                attendance["status"]=="Present"
            ]
        )

        absent_days = max(
            days_in_month-present_days,
            0
        )

        total_hours = (
            attendance["hours"]
            .fillna(0)
            .sum()
            if len(attendance)
            else 0
        )

        standard_hours = present_days * 8

        ot_hours = max(
            total_hours-standard_hours,
            0
        )

        if salary_type=="Daily":

            daily_rate = float(
                eng["daily_rate"] or 0
            )

            basic_salary = (
                present_days*daily_rate
            )

        else:

            monthly_salary = float(
                eng["salary"] or 0
            )

            basic_salary = (
                monthly_salary
                * present_days
                / days_in_month
            )

        ot_rate = st.number_input(
            "OT Rate / Hour",
            min_value=0.0,
            value=0.0
        )

        ot_amount = ot_hours*ot_rate

        advance = st.number_input(
            "Advance",
            min_value=0.0
        )

        deduction = st.number_input(
            "Other Deduction",
            min_value=0.0
        )

        gross_salary = (
            basic_salary+ot_amount
        )

        net_salary = max(
            gross_salary-
            advance-
            deduction,
            0
        )

        c1,c2,c3,c4 = st.columns(4)

        c1.metric(
            "Present",
            present_days
        )

        c2.metric(
            "Absent",
            absent_days
        )

        c3.metric(
            "OT Hours",
            f"{ot_hours:.2f}"
        )

        c4.metric(
            "Net Salary",
            money(net_salary)
        )

        st.info(
            f"Basic: {money(basic_salary)} | "
            f"OT: {money(ot_amount)} | "
            f"Advance: {money(advance)} | "
            f"Deduction: {money(deduction)}"
        )

        if st.button(
            "💾 Generate Salary",
            use_container_width=True
        ):

            execute("""
                INSERT INTO salary
                (engineer_id,salary_month,salary_type,
                 basic_salary,working_days,present_days,
                 absent_days,ot_hours,ot_amount,
                 advance,deduction,gross_salary,
                 net_salary,status,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                engineer_id,
                f"{year:04d}-{month:02d}",
                salary_type,
                basic_salary,
                days_in_month,
                present_days,
                absent_days,
                ot_hours,
                ot_amount,
                advance,
                deduction,
                gross_salary,
                net_salary,
                "Pending",
                now()
            ))

            st.success(
                f"Salary generated: {money(net_salary)}"
            )

            st.rerun()

    st.divider()

    st.subheader("Salary History")

    st.dataframe(
        query("""
            SELECT
                s.salary_month,
                e.name engineer,
                s.salary_type,
                s.present_days,
                s.absent_days,
                s.ot_hours,
                s.basic_salary,
                s.ot_amount,
                s.advance,
                s.deduction,
                s.net_salary,
                s.status
            FROM salary s
            LEFT JOIN engineers e
                ON s.engineer_id=e.id
            ORDER BY s.id DESC
        """),
        use_container_width=True
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
                service_terms=?
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
            service_terms
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
