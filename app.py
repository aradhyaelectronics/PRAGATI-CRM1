import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os

st.set_page_config(page_title="Pragati Enterprises CRM & ERP", layout="wide")

DATA_FILE = "pragati_erp_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "clients": [], "vendors": [], "inventory": [], "categories": ["CCTV Surveillance", "Biometric & Access", "Intercom & EPABX", "Solar Systems", "Electrical Work"],
        "inquiries": [], "calls": [], "work_details": [], "engineers": [], "advance_logs": [], "travel_logs": [],
        "quotations": [], "challans": [], "purchase_orders": [], "credit_notes": [],
        "terms": "1. 50% Advance at the time of order.\n2. Warranty covers manufacturing defects only.\n3. Taxes extra as applicable."
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

st.title("⚡ Pragati Enterprises - Management Portal")
st.caption("Palghar | CCTV, Biometric, Solar, Intercom & Electrical Services")

menu = st.sidebar.selectbox("Navigation Menu", [
    "Dashboard", "Service Categories", "Inventory & Vendors", "Leads & Inquiries",
    "Calls & Work Status", "Engineers & Salary", "Quotations & Documents", "Terms & Conditions"
])

# 1. DASHBOARD
if menu == "Dashboard":
    st.header("📌 System Overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Clients", len(data["clients"]))
    col2.metric("Total Inquiries", len(data["inquiries"]))
    col3.metric("Pending Calls", len([c for c in data["calls"] if c['status'] != 'Completed']))
    col4.metric("Inventory Items", len(data["inventory"]))

# 2. SERVICE CATEGORIES
elif menu == "Service Categories":
    st.header("🏷️ Service Categories")
    new_cat = st.text_input("Add New Category Name")
    if st.button("Add Category"):
        if new_cat and new_cat not in data["categories"]:
            data["categories"].append(new_cat)
            save_data(data)
            st.success(f"Category '{new_cat}' Added!")
    st.write("Current Categories:", data["categories"])

# 3. INVENTORY & VENDORS
elif menu == "Inventory & Vendors":
    tab1, tab2 = st.tabs(["📦 Inventory Management", "🏬 Vendor Management"])
    with tab1:
        st.subheader("Add Stock / Item")
        item = st.text_input("Item Name (e.g. 2MP IP Camera)")
        cat = st.selectbox("Category", data["categories"])
        qty = st.number_input("Quantity", min_value=1)
        rate = st.number_input("Purchase Rate", min_value=0.0)
        if st.button("Save Item"):
            data["inventory"].append({"item": item, "category": cat, "qty": qty, "rate": rate})
            save_data(data)
            st.success("Item Added to Stock!")
        st.dataframe(pd.DataFrame(data["inventory"]))
    
    with tab2:
        st.subheader("Add New Vendor")
        vname = st.text_input("Vendor Company Name")
        vphone = st.text_input("Contact Number")
        vmat = st.text_input("Material Supplied")
        if st.button("Save Vendor"):
            data["vendors"].append({"name": vname, "phone": vphone, "material": vmat})
            save_data(data)
            st.success("Vendor Registered!")
        st.dataframe(pd.DataFrame(data["vendors"]))

# 4. LEADS & INQUIRIES
elif menu == "Leads & Inquiries":
    st.header("📞 New Inquiries & Lead Management")
    cname = st.text_input("Client/Company Name")
    cphone = st.text_input("Phone Number")
    cloc = st.text_input("Location / City")
    req = st.selectbox("Requirement Category", data["categories"])
    notes = st.text_area("Requirement Details")
    if st.button("Save Lead"):
        data["inquiries"].append({"client": cname, "phone": cphone, "location": cloc, "category": req, "notes": notes, "date": str(datetime.now().date())})
        save_data(data)
        st.success("Inquiry Logged Successfully!")
    st.dataframe(pd.DataFrame(data["inquiries"]))

# 5. CALLS & WORK STATUS
elif menu == "Calls & Work Status":
    st.header("⚙️ Service Calls & Field Work Logs")
    tab1, tab2 = st.tabs(["Create Call", "Engineer Work Status Updates"])
    
    with tab1:
        client = st.text_input("Client Name")
        call_type = st.selectbox("Type", ["New Installation", "AMC Service", "Fault Repair"])
        status = st.selectbox("Status", ["Scheduled", "In Progress", "Completed", "Pending Material"])
        if st.button("Create Call"):
            data["calls"].append({"client": client, "type": call_type, "status": status, "date": str(datetime.now().date())})
            save_data(data)
            st.success("Call Created!")
            
    with tab2:
        eng_name = st.text_input("Engineer Name")
        work_done = st.text_area("Work Details / Parts Replaced")
        travel_exp = st.number_input("Daily Travel Expense (₹)", min_value=0.0)
        if st.button("Submit Daily Report"):
            data["work_details"].append({"engineer": eng_name, "work": work_done, "travel": travel_exp, "date": str(datetime.now().date())})
            save_data(data)
            st.success("Work Log Saved!")

# 6. ENGINEERS & SALARY
elif menu == "Engineers & Salary":
    st.header("👷 Engineers & Payroll Management")
    ename = st.text_input("Engineer Name")
    ptype = st.selectbox("Pay Type", ["Monthly", "Daily Base"])
    rate = st.number_input("Base Pay Rate (₹)", min_value=0.0)
    if st.button("Add Engineer"):
        data["engineers"].append({"name": ename, "pay_type": ptype, "rate": rate})
        save_data(data)
        st.success("Engineer Onboarded!")
    st.dataframe(pd.DataFrame(data["engineers"]))

# 7. QUOTATIONS & DOCUMENTS
elif menu == "Quotations & Documents":
    st.header("📄 Billing & Document Generation")
    doc_type = st.selectbox("Select Document Type", ["Quotation", "Delivery Challan", "Purchase Order (PO)", "Credit Note"])
    client_name = st.text_input("Client / Vendor Name")
    item_desc = st.text_area("Itemization / Scope of Work")
    amount = st.number_input("Total Amount (₹)", min_value=0.0)
    
    st.subheader("Terms & Conditions Included:")
    st.info(data["terms"])
    
    if st.button("Generate Document"):
        doc_entry = {"type": doc_type, "party": client_name, "details": item_desc, "amount": amount, "date": str(datetime.now().date())}
        data["quotations"].append(doc_entry)
        save_data(data)
        st.success(f"{doc_type} Generated Successfully!")

# 8. TERMS & CONDITIONS
elif menu == "Terms & Conditions":
    st.header("📝 Global Terms & Conditions Setup")
    updated_terms = st.text_area("Edit Master Terms & Conditions", data["terms"], height=200)
    if st.button("Update Terms"):
        data["terms"] = updated_terms
        save_data(data)
        st.success("Terms & Conditions Updated!")
