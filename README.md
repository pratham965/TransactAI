# TransactAI

TransactAI is a secure payment platform featuring real-time fraud detection using both rule-based checks and a machine learning autoencoder model.

## Features

- **Rule-based fraud detection:** Threshold value checks, blocked IPs, browsers, payment gateways, and emails.
- **AI-based detection:** Autoencoder model for anomaly detection in transactions.
- **Web interface:** Streamlit-based frontend for user and admin management.
- **Backend API:** FastAPI for transaction processing and fraud detection.
- **Database integration:** MySQL for storing transactions and fraud rules.
- **ML inference server:** FastAPI microservice for serving autoencoder predictions.

## Installation

1. **Clone the repository:**
```bash
   git clone https://github.com/pratham965/TransactAI.git
   cd TransactAI
```
2. **Install dependencies:**
```bash
   pip install -r requirements.txt
```
3. **Set up environment variables**
- Create a .env file in the frontend and backend directory with following format:
 ```
  DB_HOST=your_mysql_host
  DB_USERNAME=your_mysql_user
  DB_PASSWORD=your_mysql_password
  DB_DB=your_database_name
```
4. **Set up a MySQL database and create tables for `transactions` and `fraud_rules` as per schema.**
5. **Make script executable:**
```bash
   chmod +x TransactAI.sh
```
6. **Run the system:**
```bash
   ./TransactAI.sh
```
