import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os

st.set_page_config(page_title="Pragati Enterprises CRM", layout="wide")

DATA_FILE = "crm_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"clients": [], "bills": [], "engineers": [], "advance_logs": [], "travel_logs": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

st.title("⚡ Pragati Enterprises - Management Dashboard")

menu = st.sidebar.selectbox("Navigation Menu", [
    "Clients & Billing", 
    "Engineers & Pay Structure", 
    "Record Advance & Travel", 
    "Salary Slip Generator"
])

# ==================== CLIENTS & BILLING ====================
if menu == "Clients & Billing":
    st.header("📄 Billing & Service Reminders")
    
    tab1, tab2 = st.tabs(["+ Add Client / Create Bill", "View Existing Bills & Reminders"])
    
    with tab1:
        st.subheader("Client Selection")
        client_option = st.radio("Choose Action:", ["Select Existing Client", "Add New Client"])
        
        selected_client = None
        if client_option == "Select Existing Client" and data["clients"]:
            client_list = {f"{c['name']} ({c['city']})": c for c in data["clients"]}
            chosen_name = st.selectbox("Select Client:", list(client_list.keys()))
            selected_client = client_list[chosen_name]
        else:
            c_name = st.text_input("Client/Company Name")
            c_phone = st.text_input("Phone Number")
            c_city = st.text_input("City/Location")
            if st.button("Save New Client"):
                if c_name:
                    new_c = {"id": len(data["clients"]) + 1, "name": c_name, "phone": c_phone, "city": c_city}
                    data["clients"].append(new_c)
                    save_data(data)
                    st.success(f"Client {c_name} Added Successfully!")
                    st.rerun()

        st.divider()
        st.subheader("Billing & AMC Cycle")
        service = st.selectbox("Service Type", [
            "HD/IP CCTV Camera Installation", 
            "Biometric Attendance & Access Door Control", 
            "Audio/Video Intercom Systems", 
            "On-Grid / Off-Grid Solar Systems", 
            "Electrical Repair Services"
        ])
        amount = st.number_input("Total Amount (INR)", min_value=0.0, step=500.0)
        interval_choice = st.selectbox("AMC / Warranty Service Cycle", [
            "3 Months Interval (4 Services/Year)", 
            "4 Months Interval (3 Services/Year)"
        ])
        
        if st.button("Generate Bill & Reminders"):
            if selected_client and amount > 0:
                interval = 3 if "3 Months" in interval_choice else 4
                today = datetime.now()
                reminders = []
                for i in range(1, (12 // interval) + 1):
                    due_date = today + timedelta(days=30 * interval * i)
                    reminders.append({"service": f"Service #{i}", "due_date": due_date.strftime("%Y-%m-%d"), "status": "Pending"})
                
                bill = {
                    "bill_id": len(data["bills"]) + 1,
                    "client_id": selected_client["id"],
                    "client_name": selected_client["name"],
                    "service": service,
                    "amount": amount,
                    "date": today.strftime("%Y-%m-%d"),
                    "amc_schedule": reminders
                }
                data["bills"].append(bill)
                save_data(data)
                st.success("Bill generated and AMC reminders scheduled successfully!")
            else:
                st.error("Please select a valid client and enter amount.")

    with tab2:
        if data["bills"]:
            for b in data["bills"]:
                with st.expander(f"Bill #{b['bill_id']} - {b['client_name']} (Rs. {b['amount']})"):
                    st.write(f"**Service:** {b['service']}")
                    st.write(f"**Date:** {b['date']}")
                    st.write("**Scheduled Service Reminders:**")
                    st.table(pd.DataFrame(b['amc_schedule']))
        else:
            st.info("No bills recorded yet.")

# ==================== ENGINEERS & PAY STRUCTURE ====================
elif menu == "Engineers & Pay Structure":
    st.header("👷 Field Engineers Management")
    
    eng_name = st.text_input("Engineer Name")
    pay_type = st.radio("Salary Type", ["Monthly Base", "Daily Base"])
    rate = st.number_input("Pay Rate (INR)", min_value=0.0, step=100.0)
    
    if st.button("Add Engineer"):
        if eng_name and rate > 0:
            eng = {"id": len(data["engineers"]) + 1, "name": eng_name, "pay_type": pay_type.split()[0], "rate": rate}
            data["engineers"].append(eng)
            save_data(data)
            st.success(f"Engineer {eng_name} registered!")
            st.rerun()

    st.divider()
    if data["engineers"]:
        st.subheader("Registered Engineers")
        st.dataframe(pd.DataFrame(data["engineers"]))

# ==================== ADVANCE & TRAVEL ====================
elif menu == "Record Advance & Travel":
    st.header("💸 Daily Travel Expenses & Advance Payments")
    
    if data["engineers"]:
        eng_list = {e['name']: e['id'] for e in data["engineers"]}
        selected_eng = st.selectbox("Select Engineer", list(eng_list.keys()))
        eng_id = eng_list[selected_eng]
        
        entry_type = st.radio("Entry Type", ["Advance Taken", "Daily Travel Expense"])
        amt = st.number_input("Amount (INR)", min_value=0.0, step=50.0)
        entry_date = st.date_input("Date", datetime.now())
        
        if st.button("Save Entry"):
            if amt > 0:
                record = {"eng_id": eng_id, "amount": amt, "date": str(entry_date)}
                if entry_type == "Advance Taken":
                    data["advance_logs"].append(record)
                    st.success("Advance payment recorded!")
                else:
                    data["travel_logs"].append(record)
                    st.success("Travel expense recorded!")
                save_data(data)
            else:
                st.warning("Please enter a valid amount.")
    else:
        st.info("Please add engineers first.")

# ==================== SALARY SLIP ====================
elif menu == "Salary Slip Generator":
    st.header("🧾 Monthly Salary Slip Generator")
    
    if data["engineers"]:
        eng_list = {f"{e['name']} ({e['pay_type']})": e for e in data["engineers"]}
        selected_eng_key = st.selectbox("Select Engineer", list(eng_list.keys()))
        eng = eng_list[selected_eng_key]
        eid = eng["id"]
        
        days_worked = 30
        if eng["pay_type"] == "Daily":
            days_worked = st.number_input("Days Worked This Month", min_value=1, max_value=31, value=26)
            base_salary = eng["rate"] * days_worked
        else:
            base_salary = eng["rate"]
            
        total_advance = sum(x["amount"] for x in data["advance_logs"] if x["eng_id"] == eid)
        total_travel = sum(x["amount"] for x in data["travel_logs"] if x["eng_id"] == eid)
        net_payable = base_salary + total_travel - total_advance
        
        st.divider()
        st.markdown(f"""
        ### PRAGATI ENTERPRISES - SALARY SLIP
        * **Engineer Name:** {eng['name']}
        * **Pay Type:** {eng['pay_type']} Base
        * **Base Salary ({days_worked} days):** Rs. {base_salary:.2f}
        * **(+) Travel Allowance:** Rs. {total_travel:.2f}
        * **(-) Advance Deductions:** Rs. {total_advance:.2f}
        ---
        ### **NET PAYABLE AMOUNT: Rs. {net_payable:.2f}**
        """)
