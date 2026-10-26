/**
 * API service client for Statement Categorizer.
 * Communicates with FastAPI backend through the Vite proxy (/api).
 */

const BASE_URL = '/api';

/**
 * Fetch domain categories and tax rules.
 */
export async function getCategories() {
  const res = await fetch(`${BASE_URL}/categories`);
  if (!res.ok) {
    throw new Error(`Failed to load categories: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Load the built-in synthetic sample statement for live demo.
 */
export async function getSampleStatement() {
  const res = await fetch(`${BASE_URL}/sample-statement`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to load sample statement (${res.status})`);
  }
  return res.json();
}

/**
 * Upload a CSV statement file via multipart form-data.
 * Enforces client-side size check (5 MB limit).
 */
export async function uploadStatement(file) {
  if (!file) {
    throw new Error('Please select a file to upload.');
  }

  const MAX_SIZE_BYTES = 5 * 1024 * 1024;
  if (file.size > MAX_SIZE_BYTES) {
    throw new Error('File exceeds maximum allowable size of 5 MB.');
  }

  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${BASE_URL}/upload-statement`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload failed with status ${res.status}`);
  }

  return res.json();
}

/**
 * Reclassify a transaction's category via the backend review endpoint.
 * Returns the updated transactions and recalculated statement summary.
 */
export async function reviewTransaction(transactionId, newCategory, currentTransactions) {
  const payload = {
    payload: {
      transaction_id: transactionId,
      new_category: newCategory,
    },
    transactions: currentTransactions,
  };

  const res = await fetch(`${BASE_URL}/review-transaction`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Review update failed (${res.status})`);
  }

  return res.json();
}

/**
 * Export current transactions to standard CSV for tax preparation.
 * Downloads the resulting CSV blob directly in the browser.
 */
export async function exportStatement(transactions, filename = 'categorized_statement.csv') {
  const payload = {
    transactions,
    filename,
  };

  const res = await fetch(`${BASE_URL}/export-statement`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `CSV export failed (${res.status})`);
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = url;
  a.download = filename.endsWith('.csv') ? filename : `${filename}.csv`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}
