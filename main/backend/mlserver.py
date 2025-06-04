from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import uvicorn
import joblib
import tensorflow as tf
import numpy as np

app = FastAPI(title="TransactAI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    df.drop(columns=['transaction_id', 'payer_mobile', 'is_fraud', 'transaction_date'], inplace=True, errors='ignore')
    scaler, freq_encodings, one_hot_columns = load_encodings()

    df = pd.get_dummies(df, columns=['transaction_channel', 'transaction_payment_mode'])

    for col in one_hot_columns:
        if col not in df.columns:
            df[col] = 0
    df = df[one_hot_columns]

    freq_cols = ["payer_email", "payee_ip", "payee_id", "payment_gateway_bank", "payer_browser"]
    for col, mapping_key in zip(freq_cols, freq_encodings.keys()):
        if col in df.columns:
            df[col] = df[col].map(freq_encodings[mapping_key]).fillna(0)
            df.rename(columns={col: f"{col}_encoded"}, inplace=True)

    scale_cols = [
        'transaction_amount', 
        'payer_email_encoded', 
        'payee_ip_encoded', 
        'payee_id_encoded', 
        'payment_gateway_bank_encoded', 
        'payer_browser_encoded'
    ]
    for col in scale_cols:
        if col not in df.columns:
            df[col] = 0

    if df.empty:
        raise ValueError("Processed DataFrame is empty after transformations.")

    df[scale_cols] = scaler.transform(df[scale_cols])
    return df

def predict(df_input):
    model = tf.keras.models.load_model("model_best.keras")
    reconstructed = model.predict(df_input)
    loss = tf.keras.losses.mae(reconstructed.astype(np.float32), df_input.astype(np.float32))
    return tf.math.less(loss, 0.264895)

@app.post("/mlpredict")
async def ml_predict(api_data: dict = Body(...)):
    df = pd.DataFrame([api_data])
    processed = preprocess_data(df)
    prediction = predict(processed)
    result = int(prediction.numpy()[0]) ^ 1
    return {
        "transaction_id": api_data.get("transaction_id", ""),
        "is_fraud": result
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8100)

