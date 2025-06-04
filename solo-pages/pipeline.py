import pandas as pd
import joblib
import numpy as np

def load_encodings():
    scaler = joblib.load("scaler.pkl")
    freq_encodings = joblib.load("freq_encodings.pkl")
    one_hot_columns = joblib.load("one_hot_columns.pkl")
    return scaler, freq_encodings, one_hot_columns

def preprocess_data(csv_path):
    # Load CSV
    df = pd.read_csv(csv_path)
    
    # Remove null rows
    df.dropna(inplace=True)
    
    # Drop unnecessary columns
    drop_cols = ['transaction_id_anonymous', 'payer_mobile_anonymous', 'is_fraud', 'transaction_date']
    df.drop(columns=drop_cols, inplace=True, errors='ignore')
    
    # Load encodings
    scaler, freq_encodings, one_hot_columns = load_encodings()
    
    # One-hot encoding
    df = pd.get_dummies(df, columns=['transaction_channel', 'transaction_payment_mode_anonymous'])
    
    # Ensure all expected one-hot columns exist
    for col in one_hot_columns:
        if col not in df.columns:
            df[col] = 0  # Add missing columns with default 0
    df = df[one_hot_columns]  # Keep only relevant one-hot columns
    
    # Frequency encoding
    freq_cols = ["payer_email_anonymous", "payee_ip_anonymous", "payee_id_anonymous", 
                 "payment_gateway_bank_anonymous", "payer_browser_anonymous"]
    
    for col, mapping_key in zip(freq_cols, freq_encodings.keys()):
        if col in df.columns:
            df[col] = df[col].map(freq_encodings[mapping_key]).fillna(0)
            df.rename(columns={col: col.replace("anonymous", "encoded")}, inplace=True)
    
    # MinMax scaling
    scale_cols = ['transaction_amount', 'payer_email_encoded', 'payer_ip_encoded', 
                  'payee_id_encoded', 'payment_gateway_bank_encoded', 'payer_browser_encoded']
    
    # Ensure columns exist before scaling
    missing_cols = [col for col in scale_cols if col not in df.columns]
    for col in missing_cols:
        df[col] = 0  # Add missing columns with default value 0
    
    if df.empty:
        raise ValueError("Processed DataFrame is empty after transformations. Check earlier steps.")
    
    df[scale_cols] = scaler.transform(df[scale_cols])
    
    return df

# Example usage
processed_data = preprocess_data("/home/manik/Downloads/transactions_train.csv")
processed_data.head()