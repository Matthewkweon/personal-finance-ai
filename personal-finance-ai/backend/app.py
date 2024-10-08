from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
from dotenv import load_dotenv
import chardet
from PyPDF2 import PdfReader
import io
import re
import requests
from apscheduler.schedulers.background import BackgroundScheduler
import plaid
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from datetime import datetime, timedelta
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
import random
import json

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}}, supports_credentials=True)

load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')

PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID')
PLAID_SECRET = os.getenv('PLAID_SECRET')
PLAID_ENV = os.getenv('PLAID_ENV', 'sandbox')

# Pushover configuration
PUSHOVER_API_TOKEN = os.getenv('PUSHOVER_API_TOKEN')
PUSHOVER_USER_KEY = os.getenv('PUSHOVER_USER_KEY')

configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={
        'clientId': PLAID_CLIENT_ID,
        'secret': PLAID_SECRET,
    }
)

plaid_client = plaid_api.PlaidApi(plaid.ApiClient(configuration))

# Global variable to store the access token
PLAID_ACCESS_TOKEN = None

SIMULATED_TRANSACTIONS_FILE = 'simulated_transactions.json'

def load_simulated_transactions():
    if os.path.exists(SIMULATED_TRANSACTIONS_FILE):
        try:
            with open(SIMULATED_TRANSACTIONS_FILE, 'r') as f:
                content = f.read()
                if content.strip():  # Check if the file is not empty
                    return json.loads(content)
                else:
                    print("Simulated transactions file is empty. Initializing with an empty list.")
                    return []
        except json.JSONDecodeError:
            print("Error decoding JSON from simulated transactions file. Initializing with an empty list.")
            return []
    else:
        print("Simulated transactions file does not exist. Initializing with an empty list.")
        return []

def save_simulated_transactions(transactions):
    with open(SIMULATED_TRANSACTIONS_FILE, 'w') as f:
        json.dump(transactions, f)

# Load simulated transactions at startup
simulated_transactions = load_simulated_transactions()


@app.route('/api/create_link_token', methods=['POST'])
def create_link_token():
    try:
        request = LinkTokenCreateRequest(
            products=[Products('transactions')],
            client_name="Your App Name",
            country_codes=[CountryCode('US')],
            language='en',
            user=LinkTokenCreateRequestUser(
                client_user_id=str(random.randint(0, 1000000))
            )
        )
        response = plaid_client.link_token_create(request)
        return jsonify(response.to_dict())
    except plaid.ApiException as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/set_access_token', methods=['POST'])
def set_access_token():
    global PLAID_ACCESS_TOKEN
    public_token = request.json['public_token']
    try:
        exchange_request = ItemPublicTokenExchangeRequest(
            public_token=public_token
        )
        exchange_response = plaid_client.item_public_token_exchange(exchange_request)
        PLAID_ACCESS_TOKEN = exchange_response['access_token']
        return jsonify({"status": "success"}), 200
    except plaid.ApiException as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/simulate_transaction', methods=['POST'])
def simulate_transaction():
    global simulated_transactions
    transaction = request.json
    transaction['date'] = datetime.now().strftime('%Y-%m-%d')
    simulated_transactions.append(transaction)
    save_simulated_transactions(simulated_transactions)
    return jsonify({"status": "success", "transaction": transaction}), 200


def get_daily_transactions():
    global simulated_transactions
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    if PLAID_ACCESS_TOKEN:
        # Use real Plaid transactions if available
        request = TransactionsGetRequest(
            access_token=PLAID_ACCESS_TOKEN,
            start_date=yesterday,
            end_date=today,
            options=TransactionsGetRequestOptions(
                include_personal_finance_category=True
            )
        )
        response = plaid_client.transactions_get(request)
        return response['transactions']
    else:
        # Use simulated transactions
        return [t for t in simulated_transactions if yesterday <= datetime.strptime(t['date'], '%Y-%m-%d').date() <= today]


def analyze_transactions(transactions):
    total_spent = sum(transaction['amount'] for transaction in transactions if transaction['amount'] > 0)
    
    transaction_details = [f"{t['name']}: ${t['amount']:.2f}" for t in transactions]
    transaction_text = "\n".join(transaction_details)

    prompt = f"""
    Today's transactions:
    {transaction_text}

    Total spent: ${total_spent:.2f}

    Please provide a brief summary of today's spending and 2-3 concise tips for managing expenses better tomorrow.
    Format the response as:
    Summary: [Your summary here]
    Tips:
    1. [First tip]
    2. [Second tip]
    3. [Third tip if applicable]
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful personal finance assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message['content']

def send_pushover_message(message):
    try:
        data = {
            "token": PUSHOVER_API_TOKEN,
            "user": PUSHOVER_USER_KEY,
            "message": message,
            "title": "Finance Update"
        }
        response = requests.post("https://api.pushover.net/1/messages.json", data=data)
        if response.status_code == 200:
            print("Pushover message sent successfully.")
        else:
            print(f"Failed to send Pushover message: {response.status_code}")
    except Exception as e:
        print(f"Error sending Pushover message: {str(e)}")

def daily_update():
    transactions = get_daily_transactions()
    if transactions:
        analysis = analyze_transactions(transactions)
        send_pushover_message(analysis)
    else:
        send_pushover_message("No transactions recorded today.")

scheduler = BackgroundScheduler()
scheduler.add_job(func=daily_update, trigger="interval", minutes=5)  # Run daily at 8 PM
scheduler.start()

@app.route('/api/analyze', methods=['POST'])
def analyze_statement():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        print(f"Received file: {file.filename}")
        print(f"File content type: {file.content_type}")
        
        file_content = file.read()
        print(f"File size: {len(file_content)} bytes")

        if file.filename.lower().endswith('.pdf'):
            # Handle PDF file
            try:
                pdf_reader = PdfReader(io.BytesIO(file_content))
                content = ""
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
            except Exception as e:
                print(f"Error processing PDF: {str(e)}")
                return jsonify({'error': 'Unable to process PDF file. Please ensure it\'s a valid PDF.'}), 400
        else:
            # Handle text file
            detected = chardet.detect(file_content)
            encoding = detected['encoding'] or 'utf-8'
            print(f"Detected encoding: {encoding}")
            
            try:
                content = file_content.decode(encoding)
            except UnicodeDecodeError:
                return jsonify({'error': 'Unable to decode file. Please ensure it\'s a valid text or PDF file.'}), 400
        
        # For debugging, print the first 100 characters of the content
        print("File content (first 100 chars):", content[:100])
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a personal finance expert. Analyze the following bank statement and provide a summary of spending and advice for cutting expenses."},
                    {"role": "user", "content": content}
                ]
            )
            
            summary = response.choices[0].message['content']
            return jsonify({'summary': summary})
        except Exception as e:
            print("OpenAI API error:", str(e))
            return jsonify({'error': 'An error occurred while analyzing the file.'}), 500
    except Exception as e:
        print("Unexpected error:", str(e))
        return jsonify({'error': 'An unexpected error occurred.'}), 500

@app.route('/api/start_daily_updates', methods=['POST'])
def start_daily_updates():
    try:
        # Trigger the first update immediately
        daily_update()
        return jsonify({'message': 'Daily updates started successfully. You will receive your first update shortly.'}), 200
    except Exception as e:
        print("Error starting daily updates:", str(e))
        return jsonify({'error': 'An error occurred while starting daily updates.'}), 500

@app.route('/api/trigger_update', methods=['POST'])
def trigger_update():
    try:
        daily_update()
        return jsonify({'message': 'Update triggered successfully.'}), 200
    except Exception as e:
        print("Error triggering update:", str(e))
        return jsonify({'error': 'An error occurred while triggering the update.'}), 500

if __name__ == '__main__':
    app.run(debug=True)