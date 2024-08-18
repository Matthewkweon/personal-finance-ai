from flask import Flask, request, jsonify
import openai
import os

app = Flask(__name__)

# Set your OpenAI API key
openai.api_key = os.environ.get('OPENAI_API_KEY')

@app.route('/api/analyze', methods=['POST'])
def analyze_statement():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        # Read and process the file
        content = file.read().decode('utf-8')
        
        # Use OpenAI to analyze the content
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a personal finance expert. Analyze the following bank statement and provide a summary of spending and advice for cutting expenses."},
                {"role": "user", "content": content}
            ]
        )
        
        summary = response.choices[0].message['content']
        return jsonify({'summary': summary})

if __name__ == '__main__':
    app.run(debug=True)