import React, { useState } from 'react';
import axios from 'axios';

const FinanceHelper = () => {
  const [file, setFile] = useState(null);
  const [summary, setSummary] = useState('');
  const [error, setError] = useState('');

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSummary('');
  
    if (!file) {
      setError('Please select a file first.');
      return;
    }
  
    const formData = new FormData();
    formData.append('file', file);
  
    try {
      const response = await axios.post('http://localhost:5000/api/analyze', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        withCredentials: true
      });
      setSummary(response.data.summary);
    } catch (error) {
      console.error('Error details:', error);
      setError('An error occurred while analyzing the file. Please try again.');
    }
  };

  return (
    <div>
      <h1>Personal Finance AI Helper</h1>
      <form onSubmit={handleSubmit}>
        <input type="file" onChange={handleFileChange} />
        <button type="submit">Analyze Statement</button>
      </form>
      {error && <p style={{color: 'red'}}>{error}</p>}
      {summary && <div>
        <h2>Analysis Summary</h2>
        <p>{summary}</p>
      </div>}
    </div>
  );
};

export default FinanceHelper;