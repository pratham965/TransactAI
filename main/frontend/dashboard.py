import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from sklearn.metrics import confusion_matrix, precision_score, recall_score
import io
import os
import threading
import time
import logging
from utils import filter_data, process_data, calculate_metrics, get_time_granularity
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Try to import functions from db_connector (direct database access)
try:
    from db_connector import has_new_data, reset_new_data_flag, update_transactions

    USE_DATABASE = True
    logger.info("Using MySQL database connection for real-time data")
except ImportError:
    # If db_connector fails, fall back to API functions
    try:
        from api import has_new_data, reset_new_data_flag

        USE_DATABASE = False
        logger.info("Using API for real-time data")
    except ImportError:
        # Define placeholder functions if both modules are not available
        def has_new_data():
            return False


        def reset_new_data_flag():
            pass


        def update_transactions():
            return False


        USE_DATABASE = False
        logger.warning("No real-time data source available")

# Set page configuration
st.set_page_config(
    page_title="Fraud Analysis Dashboard",
    page_icon="🔍",
    layout="wide"
)

# Constants
DATA_DIR = "data"
LATEST_DATA_FILE = os.path.join(DATA_DIR, "latest_transactions.csv")
HISTORY_FILE = os.path.join(DATA_DIR, "transaction_history.csv")

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize session state for filters and data
if 'data' not in st.session_state:
    st.session_state.data = None
if 'date_range' not in st.session_state:
    st.session_state.date_range = None
if 'payer_id' not in st.session_state:
    st.session_state.payer_id = None
if 'payee_id' not in st.session_state:
    st.session_state.payee_id = None
if 'transaction_id' not in st.session_state:
    st.session_state.transaction_id = ""
if 'metrics_date_range' not in st.session_state:
    st.session_state.metrics_date_range = None
if 'last_refresh_time' not in st.session_state:
    st.session_state.last_refresh_time = datetime.now()
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = True
if 'refresh_interval' not in st.session_state:
    st.session_state.refresh_interval = 5  # Default refresh interval in seconds


# Function to check for and load new data
def check_for_new_data():
    """Check if new data is available and load it if it is."""
    try:
        # If using database, proactively check for updates
        if USE_DATABASE:
            if update_transactions():
                # After updating data files, load the new data
                if os.path.exists(HISTORY_FILE):
                    new_data = pd.read_csv(HISTORY_FILE)
                    st.session_state.data = new_data
                    st.success("Real-time data updated successfully from database!")
                    return True

        # Otherwise check for updates via the flag
        elif has_new_data():
            # Load new data from the latest transactions file
            if os.path.exists(HISTORY_FILE):
                new_data = pd.read_csv(HISTORY_FILE)
                st.session_state.data = new_data
                st.success("Real-time data updated successfully!")

                # Reset the new data flag
                reset_new_data_flag()
                return True
    except Exception as e:
        st.error(f"Error loading new data: {str(e)}")
        logger.error(f"Error in check_for_new_data: {e}")
    return False


# Header
st.title("Fraud Analysis Dashboard")

# Try to load real-time data first if available
if st.session_state.data is None:
    # Try to update from database first
    if USE_DATABASE:
        try:
            logger.info("Attempting to load data from MySQL database")
            if update_transactions():
                logger.info("Successfully updated transactions from MySQL database")

                if os.path.exists(HISTORY_FILE):
                    data = pd.read_csv(HISTORY_FILE)
                    if not data.empty:
                        # Process data to ensure it has required columns
                        data = process_data(data)

                        # Store in session state
                        st.session_state.data = data

                        # Display success message
                        st.success(f"Successfully loaded {len(data)} transactions from MySQL database")
                else:
                    st.warning("Database connection successful but no data written to file")
            else:
                st.warning("Could not load data from MySQL database")
        except Exception as e:
            st.warning(f"Error connecting to MySQL database: {str(e)}")
            logger.error(f"Database connection error: {e}")

    # If database loading failed or not available, try loading from file
    if st.session_state.data is None and os.path.exists(HISTORY_FILE):
        try:
            data = pd.read_csv(HISTORY_FILE)
            if not data.empty:
                # Process data to ensure it has required columns
                data = process_data(data)

                # Store in session state
                st.session_state.data = data

                # Display success message
                st.success(f"Successfully loaded {len(data)} transactions from saved data file")
        except Exception as e:
            st.warning(f"Could not load real-time data: {str(e)}")
            logger.error(f"File loading error: {e}")

# Real-time data controls section
st.header("Real-time Data Controls")

# Create two columns for the real-time data controls
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    # Auto-refresh toggle
    auto_refresh = st.toggle("Auto-refresh", value=st.session_state.auto_refresh)
    if auto_refresh != st.session_state.auto_refresh:
        st.session_state.auto_refresh = auto_refresh

with col2:
    # Refresh interval selector
    refresh_interval = st.number_input(
        "Refresh interval (seconds)",
        min_value=1,
        max_value=60,
        value=st.session_state.refresh_interval,
        step=1
    )
    if refresh_interval != st.session_state.refresh_interval:
        st.session_state.refresh_interval = refresh_interval

with col3:
    # Manual refresh button and last refresh time
    col3a, col3b = st.columns(2)
    with col3a:
        if st.button("🔄 Refresh Now"):
            if check_for_new_data():
                st.rerun()
            else:
                st.info("No new data available")
    with col3b:
        st.text(f"Last refreshed: {st.session_state.last_refresh_time.strftime('%H:%M:%S')}")

# Auto-refresh logic
if st.session_state.auto_refresh:
    # Check if it's time to refresh based on the interval
    current_time = datetime.now()
    if (current_time - st.session_state.last_refresh_time).total_seconds() >= st.session_state.refresh_interval:
        # Update last refresh time
        st.session_state.last_refresh_time = current_time
        # Check for new data
        if check_for_new_data():
            st.rerun()

# Data Upload Section (alternative to real-time data)
st.header("Manual Data Upload")
st.markdown("If you don't have real-time data available, you can manually upload a file:")
uploaded_file = st.file_uploader("Upload your transaction data (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        # Load data based on file type
        if uploaded_file.name.endswith('.csv'):
            data = pd.read_csv(uploaded_file)
        else:
            data = pd.read_excel(uploaded_file)

        # Process data to ensure it has required columns
        data = process_data(data)

        # Store in session state
        st.session_state.data = data

        # Display success message
        st.success(f"Successfully loaded data with {len(data)} transactions")

    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.info(
            "Make sure your data contains the required columns: Transaction_ID, Timestamp, Payer_ID, Payee_ID, is_fraud_predicted, is_fraud_rule, Transaction_Channel, Transaction_Payment_Mode, Payment_Gateway_Bank, and Amount")

# Main dashboard content
if st.session_state.data is not None:
    data = st.session_state.data

    # Get min and max dates for filters
    min_date = pd.to_datetime(data['Timestamp']).min().date()
    max_date = pd.to_datetime(data['Timestamp']).max().date()

    # Sidebar for filters
    st.sidebar.header("Filters")

    # Date range filter
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    if len(date_range) == 2:
        st.session_state.date_range = date_range

    # Payer ID filter
    payer_ids = sorted(data['Payer_ID'].astype(str).unique().tolist())

    selected_payer = st.sidebar.multiselect(
        "Filter by Payer ID",
        options=payer_ids,
        default=None
    )
    st.session_state.payer_id = selected_payer if selected_payer else None

    # Payee ID filter
    payee_ids = sorted(data['Payee_ID'].astype(str).unique().tolist())
    selected_payee = st.sidebar.multiselect(
        "Filter by Payee ID",
        options=payee_ids,
        default=None
    )
    st.session_state.payee_id = selected_payee if selected_payee else None

    # Transaction ID search
    transaction_id = st.sidebar.text_input("Search by Transaction ID", value=st.session_state.transaction_id)
    st.session_state.transaction_id = transaction_id

    # Apply filters
    filtered_data = filter_data(
        data,
        date_range=st.session_state.date_range,
        payer_id=st.session_state.payer_id,
        payee_id=st.session_state.payee_id,
        transaction_id=st.session_state.transaction_id
    )

    # Stats overview
    st.header("Overview Statistics")

    # Create three columns for key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Transactions", len(filtered_data))

    with col2:
        predicted_fraud_count = filtered_data['is_fraud_predicted'].sum()
        predicted_fraud_pct = (predicted_fraud_count / len(filtered_data)) * 100 if len(filtered_data) > 0 else 0
        st.metric("Predicted Frauds", f"{predicted_fraud_count} ({predicted_fraud_pct:.2f}%)")

    with col3:
        reported_fraud_count = filtered_data['is_fraud_rule'].sum()
        reported_fraud_pct = (reported_fraud_count / len(filtered_data)) * 100 if len(filtered_data) > 0 else 0
        st.metric("Reported Frauds", f"{reported_fraud_count} ({reported_fraud_pct:.2f}%)")

    with col4:
        total_amount = filtered_data['Amount'].sum()
        st.metric("Total Transaction Amount", f"${total_amount:,.2f}")

    # Transaction data table
    st.header("Transaction Data")

    # Format data for display
    display_data = filtered_data.copy()
    display_data['Timestamp'] = pd.to_datetime(display_data['Timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
    display_data['Amount'] = display_data['Amount'].apply(lambda x: f"${x:,.2f}")
    display_data['is_fraud_predicted'] = display_data['is_fraud_predicted'].apply(lambda x: '✅' if x else '❌')
    display_data['is_fraud_rule'] = display_data['is_fraud_rule'].apply(lambda x: '✅' if x else '❌')

    # Display table with pagination
    st.dataframe(display_data, use_container_width=True)

    # Time Series Analysis
    st.header("Time Series Analysis")

    # Time frame selector
    time_frame = st.selectbox(
        "Select Time Frame",
        options=["Last 7 days", "Last 30 days", "Last 90 days", "Last year", "All time"],
        index=4  # Default to "All time"
    )

    # Calculate time series data based on selection
    if time_frame != "All time":
        if time_frame == "Last 7 days":
            cutoff_date = max_date - timedelta(days=7)
        elif time_frame == "Last 30 days":
            cutoff_date = max_date - timedelta(days=30)
        elif time_frame == "Last 90 days":
            cutoff_date = max_date - timedelta(days=90)
        else:  # Last year
            cutoff_date = max_date - timedelta(days=365)

        time_series_data = filtered_data[pd.to_datetime(filtered_data['Timestamp']).dt.date >= cutoff_date]
    else:
        time_series_data = filtered_data

    if len(time_series_data) > 0:
        # Determine time granularity based on time frame
        granularity = get_time_granularity(time_frame)

        # Group by time and count frauds
        time_series_data['Timestamp'] = pd.to_datetime(time_series_data['Timestamp'])

        if granularity == 'D':
            time_series_data['TimeBucket'] = time_series_data['Timestamp'].dt.date
            x_title = "Date"
        elif granularity == 'W':
            time_series_data['TimeBucket'] = time_series_data['Timestamp'].dt.to_period('W').apply(
                lambda x: x.start_time.date())
            x_title = "Week Starting"
        elif granularity == 'M':
            time_series_data['TimeBucket'] = time_series_data['Timestamp'].dt.to_period('M').apply(
                lambda x: x.start_time.date())
            x_title = "Month"
        else:  # 'H' - hourly
            time_series_data['TimeBucket'] = time_series_data['Timestamp'].dt.floor('H')
            x_title = "Hour"

        # Aggregate by time bucket
        time_agg = time_series_data.groupby('TimeBucket').agg(
            total_transactions=('Transaction_ID', 'count'),
            predicted_frauds=('is_fraud_predicted', 'sum'),
            reported_frauds=('is_fraud_rule', 'sum')
        ).reset_index()

        # Create time series plot
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=time_agg['TimeBucket'],
            y=time_agg['total_transactions'],
            mode='lines',
            name='Total Transactions',
            line=dict(color='blue', width=2)
        ))

        fig.add_trace(go.Scatter(
            x=time_agg['TimeBucket'],
            y=time_agg['predicted_frauds'],
            mode='lines',
            name='Predicted Frauds',
            line=dict(color='orange', width=2)
        ))

        fig.add_trace(go.Scatter(
            x=time_agg['TimeBucket'],
            y=time_agg['reported_frauds'],
            mode='lines',
            name='Reported Frauds',
            line=dict(color='red', width=2)
        ))

        fig.update_layout(
            title='Transaction and Fraud Trends Over Time',
            xaxis_title=x_title,
            yaxis_title='Count',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified"
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data available for the selected time frame.")

    # Fraud Comparison Graphs
    st.header("Fraud Pattern Analysis")

    # Create tabs for different comparisons
    tabs = st.tabs([
        "Transaction Channel",
        "Payment Mode",
        "Gateway Bank",
        "Payer Analysis",
        "Payee Analysis"
    ])

    # Tab 1: Transaction Channel Analysis
    with tabs[0]:
        if len(filtered_data) > 0:
            # Group by Transaction Channel
            channel_data = filtered_data.groupby('Transaction_Channel').agg(
                total=('Transaction_ID', 'count'),
                predicted_frauds=('is_fraud_predicted', 'sum'),
                reported_frauds=('is_fraud_rule', 'sum')
            ).reset_index()

            # Calculate percentages
            channel_data['predicted_fraud_pct'] = (
                        channel_data['predicted_frauds'] / channel_data['total'] * 100).round(2)
            channel_data['reported_fraud_pct'] = (channel_data['reported_frauds'] / channel_data['total'] * 100).round(
                2)

            # Create comparison bar chart
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=channel_data['Transaction_Channel'],
                y=channel_data['predicted_fraud_pct'],
                name='Predicted Fraud %',
                marker_color='orange'
            ))

            fig.add_trace(go.Bar(
                x=channel_data['Transaction_Channel'],
                y=channel_data['reported_fraud_pct'],
                name='Reported Fraud %',
                marker_color='red'
            ))

            fig.update_layout(
                title='Fraud Percentage by Transaction Channel',
                xaxis_title='Transaction Channel',
                yaxis_title='Percentage (%)',
                barmode='group',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

            # Display data table
            st.subheader("Transaction Channel Data")
            channel_display = channel_data.copy()
            channel_display['predicted_fraud_pct'] = channel_display['predicted_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            channel_display['reported_fraud_pct'] = channel_display['reported_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            st.dataframe(channel_display, use_container_width=True)
        else:
            st.warning("No data available for analysis.")

    # Tab 2: Payment Mode Analysis
    with tabs[1]:
        if len(filtered_data) > 0:
            # Group by Payment Mode
            payment_mode_data = filtered_data.groupby('Transaction_Payment_Mode').agg(
                total=('Transaction_ID', 'count'),
                predicted_frauds=('is_fraud_predicted', 'sum'),
                reported_frauds=('is_fraud_rule', 'sum')
            ).reset_index()

            # Calculate percentages
            payment_mode_data['predicted_fraud_pct'] = (
                        payment_mode_data['predicted_frauds'] / payment_mode_data['total'] * 100).round(2)
            payment_mode_data['reported_fraud_pct'] = (
                        payment_mode_data['reported_frauds'] / payment_mode_data['total'] * 100).round(2)

            # Create comparison bar chart
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=payment_mode_data['Transaction_Payment_Mode'],
                y=payment_mode_data['predicted_fraud_pct'],
                name='Predicted Fraud %',
                marker_color='orange'
            ))

            fig.add_trace(go.Bar(
                x=payment_mode_data['Transaction_Payment_Mode'],
                y=payment_mode_data['reported_fraud_pct'],
                name='Reported Fraud %',
                marker_color='red'
            ))

            fig.update_layout(
                title='Fraud Percentage by Payment Mode',
                xaxis_title='Payment Mode',
                yaxis_title='Percentage (%)',
                barmode='group',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

            # Display data table
            st.subheader("Payment Mode Data")
            payment_display = payment_mode_data.copy()
            payment_display['predicted_fraud_pct'] = payment_display['predicted_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            payment_display['reported_fraud_pct'] = payment_display['reported_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            st.dataframe(payment_display, use_container_width=True)
        else:
            st.warning("No data available for analysis.")

    # Tab 3: Gateway Bank Analysis
    with tabs[2]:
        if len(filtered_data) > 0:
            # Group by Gateway Bank
            bank_data = filtered_data.groupby('Payment_Gateway_Bank').agg(
                total=('Transaction_ID', 'count'),
                predicted_frauds=('is_fraud_predicted', 'sum'),
                reported_frauds=('is_fraud_rule', 'sum')
            ).reset_index()

            # Calculate percentages
            bank_data['predicted_fraud_pct'] = (bank_data['predicted_frauds'] / bank_data['total'] * 100).round(2)
            bank_data['reported_fraud_pct'] = (bank_data['reported_frauds'] / bank_data['total'] * 100).round(2)

            # Create comparison bar chart
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=bank_data['Payment_Gateway_Bank'],
                y=bank_data['predicted_fraud_pct'],
                name='Predicted Fraud %',
                marker_color='orange'
            ))

            fig.add_trace(go.Bar(
                x=bank_data['Payment_Gateway_Bank'],
                y=bank_data['reported_fraud_pct'],
                name='Reported Fraud %',
                marker_color='red'
            ))

            fig.update_layout(
                title='Fraud Percentage by Payment Gateway Bank',
                xaxis_title='Gateway Bank',
                yaxis_title='Percentage (%)',
                barmode='group',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

            # Display data table
            st.subheader("Gateway Bank Data")
            bank_display = bank_data.copy()
            bank_display['predicted_fraud_pct'] = bank_display['predicted_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            bank_display['reported_fraud_pct'] = bank_display['reported_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            st.dataframe(bank_display, use_container_width=True)
        else:
            st.warning("No data available for analysis.")

    # Tab 4: Payer Analysis
    with tabs[3]:
        if len(filtered_data) > 0:
            # Group by Payer ID
            payer_data = filtered_data.groupby('Payer_ID').agg(
                total=('Transaction_ID', 'count'),
                predicted_frauds=('is_fraud_predicted', 'sum'),
                reported_frauds=('is_fraud_rule', 'sum'),
                total_amount=('Amount', 'sum')
            ).reset_index()

            # Calculate percentages
            payer_data['predicted_fraud_pct'] = (payer_data['predicted_frauds'] / payer_data['total'] * 100).round(2)
            payer_data['reported_fraud_pct'] = (payer_data['reported_frauds'] / payer_data['total'] * 100).round(2)

            # Sort by total transactions
            payer_data = payer_data.sort_values('total', ascending=False).head(10)

            # Create comparison bar chart
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=payer_data['Payer_ID'],
                y=payer_data['predicted_fraud_pct'],
                name='Predicted Fraud %',
                marker_color='orange'
            ))

            fig.add_trace(go.Bar(
                x=payer_data['Payer_ID'],
                y=payer_data['reported_fraud_pct'],
                name='Reported Fraud %',
                marker_color='red'
            ))

            fig.update_layout(
                title='Fraud Percentage by Top 10 Payers (by transaction count)',
                xaxis_title='Payer ID',
                yaxis_title='Percentage (%)',
                barmode='group',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

            # Display data table
            st.subheader("Top Payer Data")
            payer_display = payer_data.copy()
            payer_display['predicted_fraud_pct'] = payer_display['predicted_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            payer_display['reported_fraud_pct'] = payer_display['reported_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            payer_display['total_amount'] = payer_display['total_amount'].apply(lambda x: f"${x:,.2f}")
            st.dataframe(payer_display, use_container_width=True)
        else:
            st.warning("No data available for analysis.")

    # Tab 5: Payee Analysis
    with tabs[4]:
        if len(filtered_data) > 0:
            # Group by Payee ID
            payee_data = filtered_data.groupby('Payee_ID').agg(
                total=('Transaction_ID', 'count'),
                predicted_frauds=('is_fraud_predicted', 'sum'),
                reported_frauds=('is_fraud_rule', 'sum'),
                total_amount=('Amount', 'sum')
            ).reset_index()

            # Calculate percentages
            payee_data['predicted_fraud_pct'] = (payee_data['predicted_frauds'] / payee_data['total'] * 100).round(2)
            payee_data['reported_fraud_pct'] = (payee_data['reported_frauds'] / payee_data['total'] * 100).round(2)

            # Sort by total transactions
            payee_data = payee_data.sort_values('total', ascending=False).head(10)

            # Create comparison bar chart
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=payee_data['Payee_ID'],
                y=payee_data['predicted_fraud_pct'],
                name='Predicted Fraud %',
                marker_color='orange'
            ))

            fig.add_trace(go.Bar(
                x=payee_data['Payee_ID'],
                y=payee_data['reported_fraud_pct'],
                name='Reported Fraud %',
                marker_color='red'
            ))

            fig.update_layout(
                title='Fraud Percentage by Top 10 Payees (by transaction count)',
                xaxis_title='Payee ID',
                yaxis_title='Percentage (%)',
                barmode='group',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

            # Display data table
            st.subheader("Top Payee Data")
            payee_display = payee_data.copy()
            payee_display['predicted_fraud_pct'] = payee_display['predicted_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            payee_display['reported_fraud_pct'] = payee_display['reported_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            payee_display['total_amount'] = payee_display['total_amount'].apply(lambda x: f"${x:,.2f}")
            st.dataframe(payee_display, use_container_width=True)
        else:
            st.warning("No data available for analysis.")

    # Evaluation Metrics Section
    st.header("Fraud Detection Evaluation Metrics")

    # Metrics date range filter
    st.subheader("Select Time Period for Metrics")
    metrics_date_range = st.date_input(
        "Metrics Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="metrics_date_range_selector"
    )

    if len(metrics_date_range) == 2:
        st.session_state.metrics_date_range = metrics_date_range

        # Filter data for metrics
        metrics_data = data.copy()
        if st.session_state.metrics_date_range is not None:
            start_date, end_date = st.session_state.metrics_date_range
            metrics_data = metrics_data[
                (pd.to_datetime(metrics_data['Timestamp']).dt.date >= start_date) &
                (pd.to_datetime(metrics_data['Timestamp']).dt.date <= end_date)
                ]

        if len(metrics_data) > 0:
            # Calculate metrics
            y_true = metrics_data['is_fraud_rule'].astype(int)
            y_pred = metrics_data['is_fraud_predicted'].astype(int)

            # Confusion matrix
            cm = confusion_matrix(y_true, y_pred)
            tn, fp, fn, tp = cm.ravel()

            # Create confusion matrix figure
            cm_fig = px.imshow(
                cm,
                labels=dict(x="Predicted", y="Actual", color="Count"),
                x=['Not Fraud', 'Fraud'],
                y=['Not Fraud', 'Fraud'],
                text_auto=True,
                color_continuous_scale='Reds'
            )

            cm_fig.update_layout(
                title='Confusion Matrix',
                xaxis_title='Predicted Label',
                yaxis_title='Actual Label'
            )

            # Calculate performance metrics
            precision = precision_score(y_true, y_pred, zero_division=0)
            recall = recall_score(y_true, y_pred, zero_division=0)
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            accuracy = (tp + tn) / (tp + tn + fp + fn)

            # Display metrics in two columns
            col1, col2 = st.columns(2)

            with col1:
                st.plotly_chart(cm_fig, use_container_width=True)

            with col2:
                st.subheader("Performance Metrics")
                metrics_df = pd.DataFrame({
                    'Metric': ['Accuracy', 'Precision', 'Recall', 'F1 Score'],
                    'Value': [accuracy, precision, recall, f1],
                    'Description': [
                        'Overall correct predictions',
                        'Percentage of predicted frauds that were actual frauds',
                        'Percentage of actual frauds that were correctly predicted',
                        'Harmonic mean of precision and recall'
                    ]
                })

                # Format metrics as percentages
                metrics_df['Value'] = metrics_df['Value'].apply(lambda x: f"{x * 100:.2f}%")

                st.dataframe(metrics_df, use_container_width=True, hide_index=True)

                # Detailed counts
                st.subheader("Detailed Counts")
                counts_df = pd.DataFrame({
                    'Metric': ['True Positives (TP)', 'False Positives (FP)', 'True Negatives (TN)',
                               'False Negatives (FN)'],
                    'Count': [tp, fp, tn, fn],
                    'Description': [
                        'Correctly predicted frauds',
                        'Incorrectly predicted as fraud',
                        'Correctly predicted as not fraud',
                        'Missed actual frauds'
                    ]
                })

                st.dataframe(counts_df, use_container_width=True, hide_index=True)
        else:
            st.warning("No data available for the selected time period.")

    # Download section
    st.header("Export Data")

    if len(filtered_data) > 0:
        # Create a download button for the filtered data
        csv = filtered_data.to_csv(index=False)

        st.download_button(
            label="Download Filtered Data as CSV",
            data=csv,
            file_name="fraud_analysis_data.csv",
            mime="text/csv"
        )
else:
    # Show welcome message and instructions when no data is loaded
    st.info("Welcome to the Fraud Analysis Dashboard. Please upload your transaction data to begin.")

    st.markdown("""
    ### Required Data Format

    Your data should include the following columns:
    - Transaction_ID: Unique identifier for each transaction
    - Timestamp: Date and time of the transaction
    - Payer_ID: ID of the entity making the payment
    - Payee_ID: ID of the entity receiving the payment
    - is_fraud_predicted: Boolean indicating if the system flagged the transaction as fraud (0 or 1)
    - is_fraud_rule: Boolean indicating if the transaction was actually reported as fraud (0 or 1)
    - Transaction_Channel: Channel used for the transaction (e.g., Mobile, Web, POS)
    - Transaction_Payment_Mode: Payment method (e.g., Credit Card, Debit Card, UPI)
    - Payment_Gateway_Bank: Bank processing the payment
    - Amount: Transaction amount

    Upload a CSV or Excel file with these columns to analyze your fraud detection performance.
    """)

