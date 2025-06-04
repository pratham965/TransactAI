import os
import mysql.connector
import pandas as pd
from dotenv import load_dotenv
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

DATA_DIR = "data"
LATEST_FILE = os.path.join(DATA_DIR, "latest_transactions.csv")
HISTORY_FILE = os.path.join(DATA_DIR, "transaction_history.csv")

os.makedirs(DATA_DIR, exist_ok=True)
new_data_available = False

def get_db_connection():
    """
    Establish a connection to the MySQL database using environment variables.
    """
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USERNAME"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_DB")
        )
    except mysql.connector.Error as e:
        logger.error(f"Error connecting to MySQL database: {e}")
        return None


def fetch_transactions(limit=1000):
    """
    Fetch transactions from the MySQL database.

    Args:
        limit (int): Maximum number of transactions to fetch

    Returns:
        DataFrame: Pandas DataFrame with transaction data or None if error
    """
    try:
        conn = get_db_connection()
        if conn is None:
            return None

        # Query matches the exact columns from checker.py and transaction structure
        query = f"""
        SELECT 
            transaction_id_anonymous as Transaction_ID,
            payee_id_anonymous as Payee_ID,
            payer_email_anonymous as Payer_ID,
            transaction_amount as Amount,
            transaction_channel as Transaction_Channel,
            transaction_payment_mode_anonymous as Transaction_Payment_Mode,
            payment_gateway_bank_anonymous as Payment_Gateway_Bank,
            is_fraud_rule as is_fraud_rule,
            is_fraud_predict as is_fraud_predicted,
            transaction_date as Timestamp,
            payer_browser_anonymous,
            payee_ip_anonymous,
            payer_mobile_anonymous
        FROM transactions
        ORDER BY transaction_date DESC
        LIMIT {limit}
        """

        df = pd.read_sql(query, conn)
        conn.close()

        # Process data for the dashboard
        if not df.empty:
            # Map boolean columns
            df['is_fraud_predicted'] = df['is_fraud_predicted'].astype(bool)
            df['is_fraud_rule'] = df['is_fraud_rule'].astype(bool)

            # Ensure timestamp format is consistent
            df['Timestamp'] = pd.to_datetime(df['Timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')

            # Save to files for dashboard
            df.to_csv(LATEST_FILE, index=False)
            df.to_csv(HISTORY_FILE, index=False)

            # Set new data flag
            global new_data_available
            new_data_available = True

            return df
        else:
            logger.warning("No transactions found in database")
            return None

    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        return None


def has_new_data():
    """
    Check if new transaction data is available.

    Returns:
        bool: True if new data is available, False otherwise
    """
    global new_data_available
    return new_data_available


def reset_new_data_flag():
    """
    Reset the new data flag.

    This should be called after the new data has been processed.
    """
    global new_data_available
    new_data_available = False


def update_transactions():
    """
    Fetch new transactions and update the data files.

    Returns:
        bool: True if the update was successful, False otherwise
    """
    try:
        df = fetch_transactions()
        if df is not None and not df.empty:
            logger.info(f"Successfully updated transaction data with {len(df)} records")
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating transactions: {e}")
        return False
