import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.metrics import confusion_matrix, precision_score, recall_score


def process_data(data):
    """
    Process uploaded data to ensure it has the required columns and format.
    Handles common data formatting issues.

    Args:
        data (DataFrame): Raw uploaded data

    Returns:
        DataFrame: Processed data ready for analysis
    """
    required_columns = [
        'Transaction_ID',
        'Timestamp',
        'Payer_ID',
        'Payee_ID',
        'is_fraud_predicted',
        'is_fraud_rule',
        'Transaction_Channel',
        'Transaction_Payment_Mode',
        'Payment_Gateway_Bank',
        'Amount'
    ]

    # Check for required columns
    missing_columns = set(required_columns) - set(data.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    # Create a copy to avoid modifying the original
    processed_data = data.copy()

    # Convert timestamp to datetime if not already
    if not pd.api.types.is_datetime64_any_dtype(processed_data['Timestamp']):
        try:
            processed_data['Timestamp'] = pd.to_datetime(processed_data['Timestamp'])
        except Exception as e:
            raise ValueError(f"Error converting Timestamp column to datetime: {str(e)}")

    # Ensure boolean columns are properly formatted
    for col in ['is_fraud_predicted', 'is_fraud_rule']:
        if not pd.api.types.is_bool_dtype(processed_data[col]):
            # Try to convert various formats to boolean
            try:
                # Handle different representations (0/1, True/False, Yes/No, etc.)
                if processed_data[col].dtype == 'object':
                    processed_data[col] = processed_data[col].map({
                        'True': True, 'true': True, 'TRUE': True, 'T': True, 'Yes': True, 'yes': True, 'Y': True,
                        '1': True, 1: True,
                        'False': False, 'false': False, 'FALSE': False, 'F': False, 'No': False, 'no': False,
                        'N': False, '0': False, 0: False
                    })
                else:
                    processed_data[col] = processed_data[col].astype(bool)
            except Exception as e:
                raise ValueError(f"Error converting {col} to boolean: {str(e)}")

    # Ensure Amount is numeric
    if not pd.api.types.is_numeric_dtype(processed_data['Amount']):
        try:
            # Remove currency symbols and commas if present
            if processed_data['Amount'].dtype == 'object':
                processed_data['Amount'] = processed_data['Amount'].replace({
                    '[$,₹,€,£]': '',
                    ',': ''
                }, regex=True)
            processed_data['Amount'] = pd.to_numeric(processed_data['Amount'])
        except Exception as e:
            raise ValueError(f"Error converting Amount to numeric: {str(e)}")

    # Ensure IDs are strings for consistent handling
    for col in ['Transaction_ID', 'Payer_ID', 'Payee_ID']:
        processed_data[col] = processed_data[col].astype(str)

    # Fill any missing categorical values with 'Unknown'
    for col in ['Transaction_Channel', 'Transaction_Payment_Mode', 'Payment_Gateway_Bank']:
        processed_data[col] = processed_data[col].fillna('Unknown')

    return processed_data


def filter_data(data, date_range=None, payer_id=None, payee_id=None, transaction_id=None):
    """
    Filter data based on user-selected criteria

    Args:
        data (DataFrame): Data to filter
        date_range (tuple): Start and end date for filtering
        payer_id (list): List of Payer IDs to include
        payee_id (list): List of Payee IDs to include
        transaction_id (str): Transaction ID to search for

    Returns:
        DataFrame: Filtered data
    """
    filtered_data = data.copy()

    # Apply date range filter
    if date_range is not None and len(date_range) == 2:
        start_date, end_date = date_range
        filtered_data = filtered_data[
            (pd.to_datetime(filtered_data['Timestamp']).dt.date >= start_date) &
            (pd.to_datetime(filtered_data['Timestamp']).dt.date <= end_date)
            ]

    # Apply Payer ID filter
    if payer_id is not None and len(payer_id) > 0:
        filtered_data = filtered_data[filtered_data['Payer_ID'].isin(payer_id)]

    # Apply Payee ID filter
    if payee_id is not None and len(payee_id) > 0:
        filtered_data = filtered_data[filtered_data['Payee_ID'].isin(payee_id)]

    # Apply Transaction ID search
    if transaction_id is not None and transaction_id.strip() != "":
        filtered_data = filtered_data[
            filtered_data['Transaction_ID'].str.contains(transaction_id, case=False, na=False)]

    return filtered_data


def get_time_granularity(time_frame):
    """
    Determine the appropriate time granularity for the selected time frame

    Args:
        time_frame (str): Selected time frame

    Returns:
        str: Time granularity code ('H', 'D', 'W', or 'M')
    """
    if time_frame == "Last 7 days":
        return 'D'  # Daily
    elif time_frame == "Last 30 days":
        return 'D'  # Daily
    elif time_frame == "Last 90 days":
        return 'W'  # Weekly
    elif time_frame == "Last year":
        return 'M'  # Monthly
    else:  # All time
        return 'M'  # Monthly


def calculate_metrics(y_true, y_pred):
    """
    Calculate performance metrics for fraud prediction

    Args:
        y_true (array): Actual fraud labels
        y_pred (array): Predicted fraud labels

    Returns:
        dict: Dictionary containing performance metrics
    """
    # Calculate confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()

    # Calculate metrics
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (tp + tn) / (tp + tn + fp + fn)

    return {
        'confusion_matrix': cm,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'accuracy': accuracy,
        'true_positives': tp,
        'false_positives': fp,
        'true_negatives': tn,
        'false_negatives': fn
    }
