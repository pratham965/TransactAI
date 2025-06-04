import streamlit as st
import requests
import json

API_URL = "http://127.0.0.1:8000/detect"

st.title("💳 Fraud Detection System")

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
    else:
        st.error("❌ Error connecting to API")
