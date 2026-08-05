const auth = {
  isAuthenticated() { return !!localStorage.getItem('token'); },
  requireAuth() { if (!this.isAuthenticated()) window.location.href = 'login.html'; },
  logout() { localStorage.removeItem('token'); window.location.href = 'login.html'; },
  currentUserId() {
    const token = localStorage.getItem('token');
    if (!token) return null;
    try {
      const b64 = token.split('.')[1].replace(/-/g,'+').replace(/_/g,'/');
      const pad = b64.length % 4;
      return JSON.parse(atob(pad ? b64 + '='.repeat(4-pad) : b64)).sub || null;
    } catch(_) { return null; }
  },
  async getCurrentUser() {
    if (!this.isAuthenticated()) return null;
    try { return await api.get('/auth/me'); } catch(_) { return null; }
  }
};
