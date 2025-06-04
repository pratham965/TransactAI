import os
import json
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import pandas as pd
import threading

app = FastAPI(title="Fraud Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Consider restricting this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = "data"
LATEST_FILE = os.path.join(DATA_DIR, "latest_transactions.csv")
HISTORY_FILE = os.path.join(DATA_DIR, "transaction_history.csv")

os.makedirs(DATA_DIR, exist_ok=True)

new_data_available = False
new_data_lock = threading.Lock()

class Transaction(BaseModel):
    Transaction_ID: str
    Payer_ID: str
    Payee_ID: str
    Amount: float
    Transaction_Channel: str
    Transaction_Payment_Mode: str
    Payment_Gateway_Bank: str
    is_fraud_predicted: Optional[bool] = False
    is_fraud_rule: Optional[bool] = False
    Timestamp: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "Transaction_ID": "T12345",
                "Payer_ID": "P98765",
                "Payee_ID": "R54321",
                "Amount": 500.75,
                "Transaction_Channel": "Online",
                "Transaction_Payment_Mode": "Credit Card",
                "Payment_Gateway_Bank": "XYZ Bank",
                "is_fraud_predicted": False,
                "is_fraud_rule": False
            }
        }

def process_transaction(transaction: Transaction):
    global new_data_available

    if not transaction.Timestamp:
        transaction.Timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    transaction_df = pd.DataFrame([transaction.dict()])
    transaction_df.to_csv(LATEST_FILE, index=False)

    if os.path.exists(HISTORY_FILE):
        history_df = pd.read_csv(HISTORY_FILE)
        updated_history = pd.concat([history_df, transaction_df], ignore_index=True)
        updated_history.to_csv(HISTORY_FILE, index=False)
    else:
        transaction_df.to_csv(HISTORY_FILE, index=False)

    with new_data_lock:
        new_data_available = True

@app.post("/transactions/", status_code=202)
async def add_transaction(background_tasks: BackgroundTasks, transaction: Transaction):
    background_tasks.add_task(process_transaction, transaction)
    return {"status": "accepted", "message": "Transaction is being processed"}

@app.get("/health/")
async def healthcheck():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/transactions/")
async def get_transactions(limit: int = 100):
    if os.path.exists(HISTORY_FILE):
        try:
            df = pd.read_csv(HISTORY_FILE)
            if len(df) > limit:
                df = df.tail(limit)
            if 'is_fraud_predicted' in df.columns:
                df['is_fraud_predicted'] = df['is_fraud_predicted'].astype(bool)
            if 'is_fraud_rule' in df.columns:
                df['is_fraud_rule'] = df['is_fraud_rule'].astype(bool)
            transactions = df.to_dict(orient='records')
            return {"transactions": transactions, "count": len(transactions)}
        except Exception as e:
            return {"error": f"Failed to read transactions: {str(e)}"}
    return {"transactions": [], "count": 0}

def has_new_data():
    global new_data_available
    with new_data_lock:
        return new_data_available

def reset_new_data_flag():
    global new_data_available
    with new_data_lock:
        new_data_available = False

