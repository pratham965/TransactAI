import mysql.connector
import os
from dotenv import load_dotenv
import fastapi
import uvicorn
from pydantic import BaseModel

app = fastapi.FastAPI()
load_dotenv()

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_DB")
    )

class FraudReport(BaseModel):
    transaction_id: str
    reporting_entity_id: str
    fraud_details: str

@app.post("/report")
def report_fraud(report: FraudReport):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        INSERT INTO fraud_reporting (
            transaction_id, reporting_entity_id, fraud_details, is_fraud_reported
        ) VALUES (%s, %s, %s, %s)
        """
        
        values = (report.transaction_id, report.reporting_entity_id, report.fraud_details, True)
        cursor.execute(query, values)
        conn.commit()
        conn.close()
        
        return {"transaction_id": report.transaction_id, "reporting_acknowledged": True, "failure_code": 0}
    
    except Exception as e:
        return {"transaction_id": report.transaction_id, "reporting_acknowledged": False, "failure_code": 1}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8200)
