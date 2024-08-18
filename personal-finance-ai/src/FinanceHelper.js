import React, { useState } from 'react';
import axios from 'axios';

const FinanceHelper = () => {
  const [file, setFile] = useState(null);
  const [summary, setSummary] = useState('');

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post('/api/analyze', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      setSummary(response.data.summary);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Personal Finance AI Helper</h1>
      <form onSubmit={handleSubmit} className="mb-4">
        <input type="file" onChange={handleFileChange} className="mb-2" />
        <button type="submit" className="bg-blue-500 text-white px-4 py-2 rounded">
          Analyze Statement
        </button>
      </form>
      {summary && (
        <div className="bg-gray-100 p-4 rounded">
          <h2 className="text-xl font-semibold mb-2">Analysis Summary</h2>
          <p>{summary}</p>
        </div>
      )}
    </div>
  );
};

export default FinanceHelper;