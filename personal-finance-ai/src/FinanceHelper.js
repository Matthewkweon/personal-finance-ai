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
  const [file, setFile] = useState(null);
  const [summary, setSummary] = useState('');

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

  const createSandboxItem = async () => {
    setIsLoading(true);
    setError('');
    try {
      const response = await axios.post('http://localhost:5000/api/create_sandbox_item');
      setPlaidConnected(true);
      alert('Sandbox item created successfully!');
    } catch (error) {
      console.error('Error creating sandbox item:', error);
      setError('Failed to create sandbox item. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

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

  return (
    <div>
      <h1>Personal Finance AI Helper</h1>
      {!plaidConnected && (
        <>
          <button onClick={() => open()} disabled={!ready || !linkToken}>
            Connect a real bank account
          </button>
          <button onClick={createSandboxItem} disabled={isLoading}>
            Create Sandbox Item
          </button>
        </>
      )}
      {plaidConnected && (
        <>
          <p>Bank account connected!</p>
          <button onClick={simulateTransactions} disabled={isLoading}>
            {isLoading ? 'Simulating...' : 'Simulate Transactions'}
          </button>
        </>
      )}
      <form onSubmit={handleSubmit}>
        <input type="file" onChange={handleFileChange} accept=".pdf,.txt,.csv" />
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Analyzing...' : 'Analyze Statement'}
        </button>
      </form>
      {error && <p style={{color: 'red'}}>{error}</p>}
      {analysis && (
        <div>
          <h2>Transaction Analysis</h2>
          <ReactMarkdown>{analysis}</ReactMarkdown>
        </div>
      )}
      {summary && (
        <div>
          <h2>Statement Analysis</h2>
          <ReactMarkdown>{summary}</ReactMarkdown>
        </div>
      )}
    </div>
  );
};

export default FinanceHelper;