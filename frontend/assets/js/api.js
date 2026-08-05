/**
 * api.js — Thin fetch wrapper for the StudyDeck API.
 * Automatically attaches Authorization header when a token is in localStorage.
 * All methods throw an Error with a human-readable message on non-OK responses.
 */

const BASE_URL = 'http://localhost:8000';

function _headers(extra = {}) {
  const h = { 'Content-Type': 'application/json', ...extra };
  const token = localStorage.getItem('token');
  if (token) {
    h['Authorization'] = `Bearer ${token}`;
  }
  return h;
}

async function _handleResponse(res) {
  if (res.status === 401) {
    // Token expired or invalid — clear and redirect to login
    localStorage.removeItem('token');
    window.location.href = 'login.html';
    throw new Error('Session expired. Please log in again.');
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  // 204 No Content — return null
  if (res.status === 204) return null;
  return res.json();
}

const api = {
  async get(path) {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: 'GET',
      headers: _headers(),
    });
    return _handleResponse(res);
  },

  async post(path, body) {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: _headers(),
      body: JSON.stringify(body),
    });
    return _handleResponse(res);
  },

  async put(path, body) {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: 'PUT',
      headers: _headers(),
      body: JSON.stringify(body),
    });
    return _handleResponse(res);
  },

  async delete(path) {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: 'DELETE',
      headers: _headers(),
    });
    return _handleResponse(res);
  },
};
