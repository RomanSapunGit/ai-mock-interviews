import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Brain, User, LogOut, ChevronDown } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import LoginModal from './LoginModal';

const Navbar = () => {
  const { user, logout } = useAuth();
  const [showModal, setShowModal] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef(null);


  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const initials = user?.email?.slice(0, 2).toUpperCase() ?? '';

  return (
    <>
      <nav className="glass-navbar">
        <div className="nav-content">
          <Link to={user ? '/dashboard' : '/'} className="logo">
            <Brain size={32} className="logo-icon" />
            <span>AI Mock Interview</span>
          </Link>

          <div className="nav-links">
            {user && <Link to="/dashboard" className="nav-link">Dashboard</Link>}

            {user ? (
              <div className="user-menu" ref={dropdownRef}>
                <button
                  id="user-avatar-btn"
                  className="user-profile user-profile--active"
                  onClick={() => setShowDropdown((v) => !v)}
                  aria-label="User menu"
                >
                  <span className="user-initials">{initials}</span>
                  <ChevronDown size={12} className={`chevron ${showDropdown ? 'rotated' : ''}`} />
                </button>
                {showDropdown && (
                  <div className="dropdown">
                    <div className="dropdown-email">{user.email}</div>
                    <hr className="dropdown-divider" />
                    <button
                      id="logout-btn"
                      className="dropdown-item"
                      onClick={() => { logout(); setShowDropdown(false); }}
                    >
                      <LogOut size={14} />
                      Sign out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button
                id="user-avatar-btn"
                className="user-profile"
                onClick={() => setShowModal(true)}
                aria-label="Sign in"
                title="Sign in"
              >
                <User size={20} />
              </button>
            )}
          </div>
        </div>

        <style>{`
          .nav-content {
            max-width: 1200px;
            margin: 0 auto;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
          }
          .logo {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-weight: 800;
            font-size: 1.25rem;
            background: linear-gradient(to right, #818cf8, #f472b6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
          }
          .logo-icon {
            color: #818cf8;
            -webkit-text-fill-color: initial;
          }
          .nav-links {
            display: flex;
            align-items: center;
            gap: 2rem;
          }
          .nav-link {
            color: var(--text-muted);
            font-weight: 500;
            transition: color var(--transition-fast);
          }
          .nav-link:hover { color: var(--text-main); }
          .user-profile {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: var(--border);
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid var(--border);
            cursor: pointer;
            transition: border-color 0.2s, transform 0.15s;
            color: var(--text-muted);
          }
          .user-profile:hover { border-color: #818cf8; transform: scale(1.05); }
          .user-profile--active {
            background: linear-gradient(135deg, #818cf860, #f472b640);
            border-color: #818cf8;
            gap: 4px;
            width: auto;
            padding: 0 10px;
            border-radius: 999px;
          }
          .user-initials {
            font-size: 0.75rem;
            font-weight: 700;
            background: linear-gradient(135deg, #818cf8, #f472b6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
          }
          .chevron { color: var(--text-muted); transition: transform 0.2s; -webkit-text-fill-color: initial; }
          .chevron.rotated { transform: rotate(180deg); }
          .user-menu { position: relative; }
          .dropdown {
            position: absolute;
            right: 0;
            top: calc(100% + 8px);
            background: var(--surface, #1e1e2e);
            border: 1px solid var(--border, #2a2a3e);
            border-radius: 0.75rem;
            padding: 0.5rem;
            min-width: 200px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.4);
            animation: dropIn 0.15s ease;
            z-index: 200;
          }
          @keyframes dropIn { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: none; } }
          .dropdown-email {
            padding: 0.5rem 0.75rem;
            font-size: 0.8rem;
            color: var(--text-muted);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          .dropdown-divider { border: none; border-top: 1px solid var(--border); margin: 0.25rem 0; }
          .dropdown-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            width: 100%;
            padding: 0.5rem 0.75rem;
            border-radius: 0.5rem;
            color: #f87171;
            font-size: 0.875rem;
            font-weight: 500;
            background: transparent;
            border: none;
            cursor: pointer;
            transition: background 0.15s;
          }
          .dropdown-item:hover { background: rgba(248,113,113,0.1); }
        `}</style>
      </nav>

      {showModal && <LoginModal onClose={() => setShowModal(false)} />}
    </>
  );
};

export default Navbar;
