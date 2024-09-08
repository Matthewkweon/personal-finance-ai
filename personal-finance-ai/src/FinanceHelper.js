import React, { useState, useCallback, useEffect } from 'react';
import { usePlaidLink } from 'react-plaid-link';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

const FinanceHelper = () => {
  const [file, setFile] = useState(null);
  const [summary, setSummary] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [dailyUpdatesStarted, setDailyUpdatesStarted] = useState(false);
  const [linkToken, setLinkToken] = useState(null);
  const [plaidConnected, setPlaidConnected] = useState(false);

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

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
    setError('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSummary('');
    setIsLoading(true);

    if (!file) {
      setError('Please select a file first.');
      setIsLoading(false);
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post('http://localhost:5000/api/analyze', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      setSummary(response.data.summary);
    } catch (error) {
      console.error('Error details:', error);
      setError('An error occurred while analyzing the file. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const startDailyUpdates = async () => {
    try {
      const response = await axios.post('http://localhost:5000/api/start_daily_updates');
      setDailyUpdatesStarted(true);
      alert(response.data.message);
    } catch (error) {
      console.error('Error starting daily updates:', error);
      setError('An error occurred while starting daily updates. Please try again.');
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
      {plaidConnected && <p>Bank account connected!</p>}
      <form onSubmit={handleSubmit}>
        <input type="file" onChange={handleFileChange} accept=".pdf,.txt,.csv" />
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Analyzing...' : 'Analyze Statement'}
        </button>
      </form>
      <button onClick={startDailyUpdates} disabled={dailyUpdatesStarted || !plaidConnected}>
        {dailyUpdatesStarted ? 'Daily Updates Started' : 'Start Daily Updates'}
      </button>
      {error && <p style={{color: 'red'}}>{error}</p>}
      {summary && (
        <div>
          <h2>Analysis Summary</h2>
          <ReactMarkdown>{summary}</ReactMarkdown>
        </div>
      )}
    </div>
  );
};

export default FinanceHelper;
