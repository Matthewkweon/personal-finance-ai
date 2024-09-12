# Personal Finance AI Helper

## Overview

This project is a personal finance assistant that uses AI to analyze bank transactions and provide financial advice. It combines the power of Plaid for secure bank account connections, OpenAI's GPT for intelligent analysis, and Pushover for timely notifications. Thought I did mess around with twilio, or text messaging, but found the verification process to be annoying.

## Features

- Connect to bank accounts securely using Plaid
- Analyze bank statements and provide financial insights
- Simulate transactions for testing purposes
- Receive daily financial updates and advice via Pushover notifications
- AI-powered analysis of spending habits and personalized financial tips

## Tech Stack

- Backend: Flask (Python)
- Frontend: React
- APIs: Plaid, OpenAI GPT, Pushover
- Other tools: APScheduler for scheduling tasks

## Prerequisites

- Python 3.8+
- Node.js 14+
- Plaid developer account
- OpenAI API key
- Pushover account and API token

## Setup

### Backend

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the backend directory with the following content:
   ```
   PLAID_CLIENT_ID=your_plaid_client_id
   PLAID_SECRET=your_plaid_secret
   PLAID_ENV=sandbox
   OPENAI_API_KEY=your_openai_api_key
   PUSHOVER_API_TOKEN=your_pushover_api_token
   PUSHOVER_USER_KEY=your_pushover_user_key
   ```

5. Run the Flask server:
   ```
   python app.py
   ```

### Frontend

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the React development server:
   ```
   npm start
   ```

## Usage

1. Open your browser and go to `http://localhost:3000`
2. Click on "Connect a bank account" to link your bank account using Plaid
3. Once connected, you can:
   - Upload bank statements for analysis
   - Simulate transactions for testing
   - Start daily updates to receive financial advice
   - Trigger manual updates to test the system

## Testing

- Use the "Simulate Transaction" feature to add test transactions
- Click "Trigger Update" to manually run the daily update process and receive a Pushover notification
- Adjust the `scheduler.add_job()` call in `app.py` to change the frequency of automatic updates during testing

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This application is for educational and demonstration purposes only. Always consult with a qualified financial advisor before making important financial decisions.