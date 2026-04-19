import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const LoginModal = ({ onClose, initialEmail = '' }) => {
  const { login, register } = useAuth();
  const [tab, setTab] = useState('login');
  const [email, setEmail] = useState(initialEmail);
  const [password, setPassword] = useState('');

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (tab === 'login') {
        await login(email, password);
      } else {
        await register(email, password);
      }
      onClose();
      navigate('/dashboard');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-tabs">
          <button
            className={`modal-tab ${tab === 'login' ? 'active' : ''}`}
            onClick={() => { setTab('login'); setError(''); }}
          >
            Sign In
          </button>
          <button
            className={`modal-tab ${tab === 'register' ? 'active' : ''}`}
            onClick={() => { setTab('register'); setError(''); }}
          >
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-group">
            <label htmlFor="auth-email">Email</label>
            <input
              id="auth-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoFocus
            />
          </div>
          <div className="form-group">
            <label htmlFor="auth-password">Password</label>
            <input
              id="auth-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>
          {error && <p className="modal-error">{error}</p>}
          <button type="submit" className="modal-submit" disabled={loading}>
            {loading ? 'Loading...' : tab === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <style>{`
          .modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.6);
            backdrop-filter: blur(4px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            animation: fadeIn 0.15s ease;
          }
          @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
          .modal-card {
            background: var(--surface, #1e1e2e);
            border: 1px solid var(--border, #2a2a3e);
            border-radius: 1rem;
            padding: 2rem;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 25px 50px rgba(0,0,0,0.5);
            animation: slideUp 0.2s ease;
          }
          @keyframes slideUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: none; } }
          .modal-tabs {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1.75rem;
            background: var(--bg, #13131f);
            border-radius: 0.5rem;
            padding: 0.25rem;
          }
          .modal-tab {
            flex: 1;
            padding: 0.5rem;
            border-radius: 0.375rem;
            font-weight: 600;
            font-size: 0.875rem;
            color: var(--text-muted, #888);
            background: transparent;
            border: none;
            cursor: pointer;
            transition: all 0.2s;
          }
          .modal-tab.active {
            background: linear-gradient(135deg, #818cf8, #f472b6);
            color: #fff;
          }
          .modal-form {
            display: flex;
            flex-direction: column;
            gap: 1rem;
          }
          .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.375rem;
          }
          .form-group label {
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-muted, #888);
            text-transform: uppercase;
            letter-spacing: 0.05em;
          }
          .form-group input {
            background: var(--bg, #13131f);
            border: 1px solid var(--border, #2a2a3e);
            border-radius: 0.5rem;
            padding: 0.65rem 0.875rem;
            color: var(--text-main, #e8e8f0);
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.2s;
          }
          .form-group input:focus {
            border-color: #818cf8;
          }
          .modal-error {
            color: #f87171;
            font-size: 0.85rem;
            text-align: center;
          }
          .modal-submit {
            margin-top: 0.5rem;
            padding: 0.75rem;
            border-radius: 0.5rem;
            font-weight: 700;
            font-size: 0.95rem;
            background: linear-gradient(135deg, #818cf8, #f472b6);
            color: #fff;
            border: none;
            cursor: pointer;
            transition: opacity 0.2s, transform 0.1s;
          }
          .modal-submit:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
          .modal-submit:disabled { opacity: 0.6; cursor: not-allowed; }
        `}</style>
      </div>
    </div>
  );
};

export default LoginModal;
