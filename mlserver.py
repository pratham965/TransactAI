from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import uvicorn
import joblib
import tensorflow as tf
import numpy as np

app = FastAPI(title="TransactAI")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (change this in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_encodings():
    scaler = joblib.load("scaler.pkl")
    freq_encodings = joblib.load("freq_encodings.pkl")
    one_hot_columns = joblib.load("one_hot_columns.pkl")
    return scaler, freq_encodings, one_hot_columns

def preprocess_data(df):
    # Drop unnecessary columns
    drop_cols = ['transaction_id', 'payer_mobile', 'is_fraud', 'transaction_date']
    df.drop(columns=drop_cols, inplace=True, errors='ignore')
    
    # Load encodings
    scaler, freq_encodings, one_hot_columns = load_encodings()
    
    # One-hot encoding
    df = pd.get_dummies(df, columns=['transaction_channel', 'transaction_payment_mode'])
    
    # Ensure all expected one-hot columns exist
    for col in one_hot_columns:
        if col not in df.columns:
            df[col] = 0  # Add missing columns with default 0
    df = df[one_hot_columns]  # Keep only relevant one-hot columns
    
    # Frequency encoding
    freq_cols = ["payer_email", "payee_ip", "payee_id", 
                 "payment_gateway_bank", "payer_browser"]
    
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

def predict(df_fraud):
    model = tf.keras.models.load_model("model_best.keras")
    reconstruction_a = model.predict(df_fraud)
    reconstruction_a = np.array(reconstruction_a, dtype=np.float32)
    df_fraud = np.array(df_fraud, dtype=np.float32)
    test_loss = tf.keras.losses.mae(reconstruction_a, df_fraud)
    return tf.math.less(test_loss, 0.264895)

@app.post("/mlpredict")
async def ml_predict(api_data: dict = Body(...)):
    # Convert incoming JSON data to DataFrame
    df = pd.DataFrame([api_data])
    
    # Preprocess the data
    df_new = preprocess_data(df)
    
    # Make predictions
    output = predict(df_new)
    result = int(output.numpy()[0])  # Ensure it's in a serializable format
    result = result^1
    return {"transaction_id": api_data.get("transaction_id", ""), "is_fraud": result}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8100)