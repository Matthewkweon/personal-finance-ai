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
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.sandbox_item_fire_webhook_request import SandboxItemFireWebhookRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.products import Products
from plaid.model.sandbox_item_fire_webhook_request import SandboxItemFireWebhookRequest
from plaid.model.item_webhook_update_request import ItemWebhookUpdateRequest
from datetime import datetime, timedelta
from plaid.model.item_webhook_update_request import ItemWebhookUpdateRequest
import plaid
import random
import time

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
PLAID_ACCESS_TOKEN = os.getenv('PLAID_ACCESS_TOKEN')

def save_access_token(token):
    global PLAID_ACCESS_TOKEN
    PLAID_ACCESS_TOKEN = token
    # Save to environment variable or a secure storage
    os.environ['PLAID_ACCESS_TOKEN'] = token

def update_transactions():
    global PLAID_ACCESS_TOKEN
    if not PLAID_ACCESS_TOKEN:
        print("No access token available. Please connect your bank account.")
        return

    try:
        transactions = simulate_transactions(PLAID_ACCESS_TOKEN)
        if transactions:
            analysis = analyze_transactions(transactions)
            send_pushover_message(analysis)
        else:
            send_pushover_message("No transactions recorded in the last update period.")
    except plaid.ApiException as e:
        error_message = f"Plaid API error: {str(e)}"
        print(error_message)
        send_pushover_message(error_message)
    except Exception as e:
        error_message = f"Error occurred during update: {str(e)}"
        print(error_message)
        send_pushover_message(error_message)

@app.route('/api/start_updates', methods=['POST'])
def start_updates():
    global PLAID_ACCESS_TOKEN
    if not PLAID_ACCESS_TOKEN:
        return jsonify({"error": "No access token available. Please connect your bank account first."}), 400

    global scheduler
    if scheduler.running:
        scheduler.shutdown()
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=update_transactions, trigger="cron", hour=21, minute=25)
    scheduler.start()
    
    # Run immediately
    update_transactions()
    
    return jsonify({'message': 'Updates started successfully. You will receive your first update shortly.'}), 200


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
    public_token = request.json['public_token']
    try:
        exchange_request = ItemPublicTokenExchangeRequest(
            public_token=public_token
        )
        exchange_response = plaid_client.item_public_token_exchange(exchange_request)
        access_token = exchange_response['access_token']
        save_access_token(access_token)
        return jsonify({"status": "success"}), 200
    except plaid.ApiException as e:
        return jsonify({"error": str(e)}), 400

def get_daily_transactions():
    if not PLAID_ACCESS_TOKEN:
        return []
    start_date = (datetime.now() - timedelta(days=1)).date()
    end_date = datetime.now().date()

    request = TransactionsGetRequest(
        access_token=PLAID_ACCESS_TOKEN,
        start_date=start_date,
        end_date=end_date,
        options=TransactionsGetRequestOptions(
            include_personal_finance_category=True
        )
    )
    response = plaid_client.transactions_get(request)
    return response['transactions']

@app.route('/api/update_webhook', methods=['POST'])
def update_webhook():
    global PLAID_ACCESS_TOKEN
    if not PLAID_ACCESS_TOKEN:
        return jsonify({"error": "No access token available"}), 400
    
    try:
        # Use a placeholder URL if you don't have a real webhook endpoint
        webhook_url = "https://www.example.com/webhook"
        request = ItemWebhookUpdateRequest(
            access_token=PLAID_ACCESS_TOKEN,
            webhook=webhook_url
        )
        response = plaid_client.item_webhook_update(request)
        return jsonify({"message": "Webhook updated successfully", "item_id": response['item']['item_id']}), 200
    except plaid.ApiException as e:
        return jsonify({"error": f"Failed to update webhook: {e.body}"}), 500
    

@app.route('/api/create_sandbox_item', methods=['POST'])
def create_sandbox_item():
    try:
        create_request = SandboxPublicTokenCreateRequest(
            institution_id='ins_109508',
            initial_products=[Products('transactions')]
        )
        response = plaid_client.sandbox_public_token_create(create_request)
        public_token = response['public_token']
        
        exchange_request = ItemPublicTokenExchangeRequest(
            public_token=public_token
        )
        exchange_response = plaid_client.item_public_token_exchange(exchange_request)
        global PLAID_ACCESS_TOKEN
        PLAID_ACCESS_TOKEN = exchange_response['access_token']
        
        # Set up webhook for the new item
        webhook_url = "https://www.example.com/webhook"  # Use a placeholder URL
        update_webhook(PLAID_ACCESS_TOKEN, webhook_url)
        
        return jsonify({"message": "Sandbox item created successfully with webhook", "access_token": PLAID_ACCESS_TOKEN}), 200
    except plaid.ApiException as e:
        return jsonify({"error": f"Failed to create sandbox item: {e.body}"}), 500
    
def update_webhook(access_token, webhook_url):
    try:
        request = ItemWebhookUpdateRequest(
            access_token=access_token,
            webhook=webhook_url
        )
        response = plaid_client.item_webhook_update(request)
        print(f"Webhook updated successfully for item: {response['item']['item_id']}")
    except plaid.ApiException as e:
        print(f"Failed to update webhook: {e.body}")


def simulate_transactions(access_token, max_retries=5, delay_seconds=2):
    for attempt in range(max_retries):
        try:
            # Fire the webhook to simulate new transactions
            request = SandboxItemFireWebhookRequest(
                access_token=access_token,
                webhook_code="DEFAULT_UPDATE"
            )
            plaid_client.sandbox_item_fire_webhook(request)
            
            # Fetch the updated transactions
            start_date = (datetime.now() - timedelta(days=30)).date()
            end_date = datetime.now().date()
            request = TransactionsGetRequest(
                access_token=access_token,
                start_date=start_date,
                end_date=end_date
            )
            response = plaid_client.transactions_get(request)
            transactions = response['transactions']
            
            print(f"Successfully simulated and fetched {len(transactions)} transactions on attempt {attempt + 1}")
            return transactions
        except plaid.ApiException as e:
            if 'PRODUCT_NOT_READY' in str(e):
                print(f"Product not ready on attempt {attempt + 1}. Retrying in {delay_seconds} seconds...")
                time.sleep(delay_seconds)
            else:
                print(f"Error simulating transactions: {e.body}")
                raise
    
    print("Max retries reached. Unable to simulate transactions.")
    return None

    
@app.route('/api/simulate_transactions', methods=['POST'])
def simulate_transactions_route():
    global PLAID_ACCESS_TOKEN
    if not PLAID_ACCESS_TOKEN:
        return jsonify({"error": "No access token available"}), 400
    
    try:
        transactions = simulate_transactions(PLAID_ACCESS_TOKEN)
        if transactions:
            transaction_details = [
                {"name": t['name'], "amount": t['amount'], "date": t['date']}
                for t in transactions
            ]
            return jsonify({
                "message": f"Simulated and fetched {len(transactions)} transactions",
                "transactions": transaction_details
            }), 200
        else:
            return jsonify({"error": "Failed to simulate transactions after multiple attempts"}), 500
    except plaid.ApiException as e:
        print(f"Error simulating transactions: {e.body}")
        return jsonify({"error": f"Failed to simulate transactions: {e.body}"}), 500
    

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
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful personal finance assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message['content']


def format_summary(text):
    # Split the text into sections based on ###
    sections = re.split(r'(?m)^###', text)
    
    # Process each section
    formatted_sections = []
    for section in sections:
        if section.strip():
            # Add ### back to the beginning of each non-empty section
            section = "###" + section
            
            # Replace numbered bullet points with new lines
            section = re.sub(r'(?m)^\d+\.', r'\n\g<0>', section)
            
            formatted_sections.append(section.strip())
    
    # Join the sections with two newlines between them
    return "\n\n".join(formatted_sections)


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
    global PLAID_ACCESS_TOKEN
    if not PLAID_ACCESS_TOKEN:
        send_pushover_message("No access token available. Please connect your bank account.")
        return

    try:
        transactions = simulate_transactions(PLAID_ACCESS_TOKEN)
        if transactions:
            analysis = analyze_transactions(transactions)
            send_pushover_message(analysis)
        else:
            send_pushover_message("No transactions recorded in the last update period.")
    except Exception as e:
        send_pushover_message(f"Error occurred during update: {str(e)}")


scheduler = BackgroundScheduler()
scheduler.add_job(func=daily_update, trigger="cron", hour=21, minute=)  # Run daily at 8 PM
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

if __name__ == '__main__':
    app.run(debug=True)