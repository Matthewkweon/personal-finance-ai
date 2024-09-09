import React, { useState, useCallback, useEffect } from 'react';
import { usePlaidLink } from 'react-plaid-link';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

const FinanceHelper = () => {
  const [linkToken, setLinkToken] = useState(null);
  const [plaidConnected, setPlaidConnected] = useState(false);
  const [analysis, setAnalysis] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [dailyUpdatesRunning, setDailyUpdatesRunning] = useState(false);

  const generateToken = useCallback(async () => {
    try {
      const response = await axios.post('http://localhost:5000/api/create_link_token');
      setLinkToken(response.data.link_token);
    } catch (error) {
      console.error('Error generating link token:', error);
      setError('Failed to generate Plaid link token');
    }
  }, []);

  useEffect(() => {
    generateToken();
  }, [generateToken]);

  const onSuccess = useCallback(async (public_token, metadata) => {
    try {
      await axios.post('http://localhost:5000/api/set_access_token', { public_token });
      setPlaidConnected(true);
      alert('Bank account connected successfully!');
    } catch (error) {
      console.error('Error setting access token:', error);
      setError('Failed to connect bank account');
    }
  }, []);

  const config = {
    token: linkToken,
    onSuccess,
  };

  const { open, ready } = usePlaidLink(config);

  const simulateTransactions = async () => {
    setIsLoading(true);
    setError('');
    setAnalysis('');
    try {
      const response = await axios.post('http://localhost:5000/api/simulate_transactions');
      setAnalysis(response.data.analysis);
    } catch (error) {
      console.error('Error simulating transactions:', error);
      setError('Failed to simulate transactions. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const startDailyUpdates = async () => {
    try {
      const response = await axios.post('http://localhost:5000/api/start_daily_updates');
      alert(response.data.message);
      setDailyUpdatesRunning(true);
    } catch (error) {
      console.error('Error starting daily updates:', error);
      setError('Failed to start daily updates. Please try again.');
    }
  };

  const stopDailyUpdates = async () => {
    try {
      const response = await axios.post('http://localhost:5000/api/stop_daily_updates');
      alert(response.data.message);
      setDailyUpdatesRunning(false);
    } catch (error) {
      console.error('Error stopping daily updates:', error);
      setError('Failed to stop daily updates. Please try again.');
    }
  };

  return (
    <div>
      <h1>Personal Finance AI Helper</h1>
      {!plaidConnected && (
        <button onClick={() => open()} disabled={!ready || !linkToken}>
          Connect a bank account
        </button>
      )}
      {plaidConnected && (
        <>
          <p>Bank account connected!</p>
          <button onClick={simulateTransactions} disabled={isLoading}>
            {isLoading ? 'Simulating...' : 'Simulate Transactions'}
          </button>
          {dailyUpdatesRunning ? (
            <button onClick={stopDailyUpdates}>Stop Daily Updates</button>
          ) : (
            <button onClick={startDailyUpdates}>Start Daily Updates</button>
          )}
        </>
      )}
      {error && <p style={{color: 'red'}}>{error}</p>}
      {analysis && (
        <div>
          <h2>Analysis Summary</h2>
          <ReactMarkdown>{analysis}</ReactMarkdown>
        </div>
      )}
    </div>
  );
};

export default FinanceHelper;