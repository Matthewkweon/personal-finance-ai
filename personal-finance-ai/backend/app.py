from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
from dotenv import load_dotenv
import chardet
from PyPDF2 import PdfReader
import io

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}}, supports_credentials=True)

load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')

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

if __name__ == '__main__':
    app.run(debug=True)