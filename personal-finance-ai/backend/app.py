from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
from dotenv import load_dotenv
import chardet
from PyPDF2 import PdfReader
import io
import re
from apscheduler.schedulers.background import BackgroundScheduler
import plaid
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from datetime import datetime, timedelta
from twilio.rest import Client

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}}, supports_credentials=True)

load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')

PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID')
PLAID_SECRET = os.getenv('PLAID_SECRET')
PLAID_ACCESS_TOKEN = os.getenv('PLAID_ACCESS_TOKEN')
PLAID_ENV = os.getenv('PLAID_ENV', 'sandbox')

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_FROM_NUMBER = os.getenv('TWILIO_FROM_NUMBER')
TWILIO_TO_NUMBER = os.getenv('TWILIO_TO_NUMBER')

configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={
        'clientId': PLAID_CLIENT_ID,
        'secret': PLAID_SECRET,
    }
)

plaid_client = plaid_api.PlaidApi(plaid.ApiClient(configuration))

# Configure Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def get_daily_transactions():
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

def send_twilio_message(message):
    try:
        message = twilio_client.messages.create(
            body=message,
            from_=TWILIO_FROM_NUMBER,
            to=TWILIO_TO_NUMBER
        )
        print(f"Message sent successfully. SID: {message.sid}")
    except Exception as e:
        print(f"Failed to send message: {str(e)}")

def daily_update():
    transactions = get_daily_transactions()
    if transactions:
        analysis = analyze_transactions(transactions)
        send_twilio_message(analysis)
    else:
        send_twilio_message("No transactions recorded today.")

scheduler = BackgroundScheduler()
scheduler.add_job(func=daily_update, trigger="cron", hour=20)  # Run daily at 8 PM
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
    summary = response.choices[0].message.content
    formatted_summary = format_summary(summary)
    return jsonify({'summary': formatted_summary})

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