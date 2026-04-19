import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sparkles, ArrowRight } from 'lucide-react';
import LoginModal from '../components/LoginModal';

const Landing = () => {
  const [email, setEmail] = useState('');
  const [showModal, setShowModal] = useState(false);

  const handleStart = (e) => {
    e.preventDefault();
    setShowModal(true);
  };

  return (
    <div className="landing-container">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="hero"
      >
        <span className="badge">
          <Sparkles size={14} /> AI Powered
        </span>
        <h1>Master Your Next <br/><span className="gradient-text">Interview</span></h1>
        <p className="subtitle">
          Practice with semi-structured AI interviews tailored to your experience.
          Upload documents or provide text to generate relevant questions.
        </p>

        <form onSubmit={handleStart} className="login-form">
          <input
            type="email"
            placeholder="Enter your email to start"
            className="glass-input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <button type="submit" className="btn-primary">
            Get Started <ArrowRight size={18} />
          </button>
        </form>
      </motion.div>

      {showModal && <LoginModal onClose={() => setShowModal(false)} initialEmail={email} />}

      <div className="grid-bg" />

      <style>{`
        .landing-container {
          height: 80vh;
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
        }
        .hero {
          text-align: center;
          max-width: 800px;
          z-index: 10;
        }
        .badge {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.4rem 1rem;
          background: rgba(129, 140, 248, 0.1);
          border: 1px solid rgba(129, 140, 248, 0.2);
          border-radius: 100px;
          color: var(--primary);
          font-size: 0.8rem;
          font-weight: 600;
          margin-bottom: 2rem;
        }
        h1 {
          font-size: 4rem;
          line-height: 1.1;
          margin-bottom: 1.5rem;
          font-weight: 800;
        }
        .gradient-text {
          background: linear-gradient(135deg, var(--primary), var(--accent));
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        .subtitle {
          font-size: 1.25rem;
          color: var(--text-muted);
          margin-bottom: 3rem;
        }
        .login-form {
          display: flex;
          gap: 1rem;
          justify-content: center;
          max-width: 500px;
          margin: 0 auto;
        }
        .login-form input {
          flex: 1;
        }
        .grid-bg {
          position: absolute;
          inset: 0;
          background-image: radial-gradient(circle at 2px 2px, rgba(255,255,255,0.05) 1px, transparent 0);
          background-size: 24px 24px;
          mask-image: radial-gradient(circle at center, black, transparent 80%);
          z-index: 1;
        }
      `}</style>
    </div>
  );
};

export default Landing;
