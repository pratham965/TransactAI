import streamlit as st
import requests
import json
import os
import sys
import subprocess
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="TransactAI",
    layout="wide"
)

# Admin credentials (hardcoded as requested)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"


# Function to run external Streamlit scripts
def run_streamlit_script(script_path):
    try:
        # Run the script in a subprocess
        process = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # Wait for process to complete (or set a timeout)
        return f"Running {script_path}"
    except Exception as e:
        return f"Error running {script_path}: {str(e)}"


# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'active_view' not in st.session_state:
    st.session_state.active_view = "home"

# Handle logout
if st.sidebar.button("Logout") and st.session_state.logged_in:
    st.session_state.logged_in = False
    st.session_state.active_view = "home"
    st.rerun()

# Sidebar navigation
st.sidebar.title("Navigation")

if not st.session_state.logged_in:
    nav_selection = st.sidebar.radio("Go to:", ["Home", "Payment Processing", "Admin Login"])
else:
    nav_selection = st.sidebar.radio("Go to:", ["Home", "Payment Processing", "Admin Dashboard", "Rule Management"])

# Update active view based on navigation
if nav_selection == "Home":
    st.session_state.active_view = "home"
elif nav_selection == "Payment Processing":
    st.session_state.active_view = "payment"
elif nav_selection == "Admin Login":
    st.session_state.active_view = "admin_login"
elif nav_selection == "Admin Dashboard" and st.session_state.logged_in:
    st.session_state.active_view = "dashboard"
elif nav_selection == "Rule Management" and st.session_state.logged_in:
    st.session_state.active_view = "rules"

# Main content based on active view
if st.session_state.active_view == "home":
    st.title(" TransactAI")
    st.write("""
    ### Welcome to a secure Payment Platform

  Secure. Intelligent. Scalable.

    """)

    col1, col2 = st.columns(2)
    with col1:
        st.info("👥 **Users**")
    with col2:
        st.warning(" **Admins**")

elif st.session_state.active_view == "payment":
    st.title(" Payment Processing")

    # Payment processing form
    transaction_id = st.text_input("Transaction ID")
    transaction_date = st.date_input("Transaction Date")    
    transaction_amount = st.number_input("Transaction Amount", min_value=0.0, step=0.01)
    transaction_channel = st.selectbox("Transaction Channel", ["Web", "Mobile"])
    transaction_payment_mode = st.selectbox("Payment Mode", ["Card", "UPI", "NEFT"])
    payment_gateway_bank = st.text_input("Payment Gateway/Bank")
    payer_email = st.text_input("Payer Email")
    payer_mobile = st.text_input("Payer Mobile")
    payer_card_brand = st.text_input("Payer Card Brand")
    payer_ip = st.text_input("Payer Device")
    payer_browser = st.text_input("Payer Browser")
    payee_id = st.text_input("Payee ID")

    if st.button("Check for Fraud"):
        transaction_data = {
            "transaction_amount": transaction_amount,
            "transaction_date": str(transaction_date),
            "transaction_channel": transaction_channel,
            "transaction_payment_mode": transaction_payment_mode,
            "payment_gateway_bank": payment_gateway_bank,
            "payer_browser": payer_browser,
            "payer_email": payer_email,
            "payer_device": payer_ip,
            "payer_mobile": payer_mobile,
            "transaction_id": transaction_id,
            "payee_id": payee_id,
            "payer_card_brand": payer_card_brand
        }

        # Send request to FastAPI backend
        try:
            API_URL = "http://127.0.0.1:8000/detect"

            try:
                response = requests.post(API_URL, json=transaction_data)

                if response.status_code == 200:
                    result = response.json()
                    if result["is_fraud_rule"]:
                        st.error(f"🚨 Fraud Detected via Rule Engine!\nReasons: {', '.join(result['fraud_reasons'])}")
                    else:
                        st.success("✅ Transaction is NOT Fraudulent Rule wise!")
                    if result["is_fraud_predicted"]:
                        st.error(f"🚨 Fraud Detected via AI!")
                    else:
                        st.success("✅ Transaction is NOT Fraudulent via AI!")
                    if result["is_fraud_rule"] or result["is_fraud_predicted"]:
                        st.warning("Fraud Reported",icon="⚠️")
                
                else:
                    st.warning("⚠️ API connection error: Using simulation mode")
                    # Simulate a fraud check response (demo only)
                    amount = transaction_data["transaction_amount"]
                    is_fraud = amount > 5000  # Example rule for demo
                    if is_fraud:
                        st.error("🚨 Fraud Detected! (Simulation)\nReasons: Amount exceeds threshold")
                    else:
                        st.success("✅ Transaction is NOT Fraudulent! (Simulation)")
            except requests.exceptions.RequestException:
                st.warning("⚠️ API connection error: Using simulation mode")
                # Simulate a fraud check response (demo only)
                amount = transaction_data["transaction_amount"]
                is_fraud = amount > 5000  # Example rule for demo
                if is_fraud:
                    st.error("🚨 Fraud Detected! (Simulation)\nReasons: Amount exceeds threshold")
                else:
                    st.success("✅ Transaction is NOT Fraudulent! (Simulation)")
        except Exception as e:
            st.error(f"❌ Error processing transaction: {str(e)}")

elif st.session_state.active_view == "admin_login":
    st.title("🔐 Admin Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            st.session_state.logged_in = True
            st.success("Login successful!")
            time.sleep(1)  # Brief pause before redirecting
            st.session_state.active_view = "dashboard"
            st.rerun()
        else:
            st.error("Invalid username or password")

elif st.session_state.active_view == "dashboard" and st.session_state.logged_in:
    st.title("📊 Fraud Analysis Dashboard")

    st.write("Loading dashboard...")
    run_streamlit_script("dashboard.py")
    st.write("Dashboard Loaded")
    # Add simplified dashboard content di

elif st.session_state.active_view == "rules" and st.session_state.logged_in:
    st.title("⚙️ Fraud Detection Rule Management")

    # Import rule management functions
    import mysql.connector
    import pandas as pd


    # ---- MySQL Connection ----
    def get_db_connection():
        return mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USERNAME"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_DB")
        )


    # ---- Function to Fetch Rules ----
    def fetch_rules():
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM fraud_rules WHERE is_active = 1")
            rules = cursor.fetchall()
            conn.close()
            return pd.DataFrame(rules) if rules else pd.DataFrame()
        except Exception as e:
            st.error(f"Error fetching rules: {str(e)}")
            return pd.DataFrame()


    # ---- Function to Add a Rule ----
    def add_rule(rule_type, value):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            if rule_type == "Threshold Value":
                cursor.execute(
                    """INSERT INTO fraud_rules (rule_type, threshold, is_active) 
                    VALUES (%s, %s, 1)""", (rule_type, value)
                )
            elif rule_type == "Blocked IP":
                cursor.execute(
                    """INSERT INTO fraud_rules (rule_type, blocked_ip, is_active) 
                    VALUES (%s, %s, 1)""", (rule_type, value)
                )
            elif rule_type == "Blocked Payment Gateway":
                cursor.execute(
                    """INSERT INTO fraud_rules (rule_type, blocked_payment_gateway, is_active) 
                    VALUES (%s, %s, 1)""", (rule_type, value)
                )
            elif rule_type == "Blocked Browser":
                cursor.execute(
                    """INSERT INTO fraud_rules (rule_type, blocked_payer_browser, is_active) 
                    VALUES (%s, %s, 1)""", (rule_type, value)
                )
            elif rule_type == "Blocked Email":
                cursor.execute(
                    """INSERT INTO fraud_rules (rule_type, blocked_email, is_active) 
                    VALUES (%s, %s, 1)""", (rule_type, value)
                )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            st.error(f"Error adding rule: {str(e)}")
            return False


    def delete_rule(rule_id):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM fraud_rules WHERE id = %s", (rule_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            st.error(f"Error deleting rule: {str(e)}")
            return False


    # ---- Streamlit UI ----
    st.subheader("Active Fraud Rules")
    rules_df = fetch_rules()

    if not rules_df.empty:
        st.dataframe(rules_df, height=300)
    else:
        st.info("No active rules found. Add some rules below.")

    # ➕ Add New Rule
    st.subheader("Manage Rules")
    with st.expander("Add New Rule"):
        rule_type = st.selectbox("Rule Type", [
            "Threshold Value",
            "Blocked IP",
            "Blocked Payment Gateway",
            "Blocked Browser",
            "Blocked Email"
        ])

        if rule_type == "Threshold Value":
            value = st.number_input("Enter Maximum Threshold Value", min_value=0.0)
        else:
            value = st.text_input(f"Enter {rule_type.replace('Blocked ', '')} to Block")

        if st.button("Add Rule"):
            if value:
                if add_rule(rule_type, value):
                    st.success("Rule Added Successfully!")
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("Please enter a value for the rule")

    st.subheader("Delete Rule")
    with st.expander("Delete Rule"):
        if not rules_df.empty:
            rule_id = st.number_input("Enter Rule ID to Delete", min_value=1, step=1)
            if st.button("Delete Rule"):
                if delete_rule(rule_id):
                    st.warning("Rule Deleted Successfully!")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("No rules to delete")

else:
    st.error("Access denied. Please login as an admin.")
