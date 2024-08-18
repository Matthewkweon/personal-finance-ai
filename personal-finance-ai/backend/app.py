from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')

@app.route('/')
def home():
    return "Welcome to the Personal Finance AI Helper API"

@app.route('/api/analyze', methods=['POST'])
def analyze_statement():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        content = file.read().decode('utf-8')
        
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a personal finance expert. Analyze the following bank statement and provide a summary of spending and advice for cutting expenses."},
                {"role": "user", "content": content}
            ]
        )
        
        summary = response.choices[0].message['content']
        return jsonify({'summary': summary})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
