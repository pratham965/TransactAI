import subprocess
import threading
import time
import os
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)


def run_api_server():
    """Run the FastAPI server for real-time data handling."""
    logger.info("Starting API server...")
    api_process = subprocess.Popen(
        ["python", "server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Log output from the API server
    for line in api_process.stdout:
        logger.info(f"API: {line.strip()}")

    # Log any errors
    for line in api_process.stderr:
        logger.error(f"API Error: {line.strip()}")

    return api_process


def run_streamlit_dashboard():
    """Run the Streamlit dashboard."""
    logger.info("Starting Streamlit dashboard...")
    streamlit_process = subprocess.Popen(
        ["streamlit", "run", "app.py", "--server.port", "5000", "--server.address", "0.0.0.0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Log output from Streamlit
    for line in streamlit_process.stdout:
        logger.info(f"Streamlit: {line.strip()}")

    # Log any errors
    for line in streamlit_process.stderr:
        logger.error(f"Streamlit Error: {line.strip()}")

    return streamlit_process


def main():
    """Run both the API server and Streamlit dashboard."""
    logger.info("Starting Fraud Analysis System")

    # Start the API server in a separate thread
    api_thread = threading.Thread(target=run_api_server)
    api_thread.daemon = True
    api_thread.start()

    # Wait a moment for the API server to start
    time.sleep(2)

    # Start the Streamlit dashboard in the main thread
    streamlit_process = run_streamlit_dashboard()

    try:
        # Keep the main process running
        streamlit_process.wait()
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    main()