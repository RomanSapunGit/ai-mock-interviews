import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { sessionService } from '../services/sessionService';
import { interviewService } from '../services/interviewService';
import { ChevronLeft, CheckCircle, Star } from 'lucide-react';

const SessionResults = () => {
  const { id: sessionId } = useParams();
  const [session, setSession] = useState(null);
  const [interview, setInterview] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchResults();
  }, [sessionId]);

  const fetchResults = async () => {
    try {
      setLoading(true);
      const sessionData = await sessionService.getSession(sessionId);
      setSession(sessionData);

      if (sessionData && sessionData.interview_id) {
        const interviewData = await interviewService.getInterview(sessionData.interview_id);
        setInterview(interviewData);
      }

      const answersData = await sessionService.listAnswers(sessionId);
      setAnswers(answersData);
    } catch (err) {
      console.error("Failed to load results:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading your results...</div>;
  if (!session) return <div className="error">Session not found.</div>;

  const averageScore = session.score !== null && session.score !== undefined ? session.score.toFixed(1) : (answers.length > 0
    ? (answers.reduce((acc, ans) => acc + (ans.score || 0), 0) / answers.length).toFixed(1)
    : 0);

  return (
    <div className="results-container">
      <header className="detail-header" style={{ marginBottom: '2rem' }}>
        <Link to="/dashboard" className="btn-ghost btn-sm">
          <ChevronLeft size={18} /> Back to Dashboard
        </Link>
        <div className="header-main" style={{ marginTop: '1rem' }}>
          <div>
            <h1>Session Results</h1>
            <p className="description">
              {interview ? `Interview: ${interview.title}` : 'Completed Practice Session'}
            </p>
          </div>
          <div className="score-summary" style={{ textAlign: 'right' }}>
            <h2 style={{ fontSize: '2.5rem', color: 'var(--primary)', margin: 0 }}>
              {averageScore} / 10
            </h2>
            <span style={{ color: 'var(--text-muted)' }}>Average Score</span>
          </div>
        </div>
      </header>

      {session.feedback && (
        <div className="glass-card" style={{ padding: '2rem', marginBottom: '2.5rem', border: '1px solid var(--primary-glow)' }}>
          <h3 style={{ color: 'var(--primary)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Star size={20} /> Overall Feedback
          </h3>
          <p style={{ color: 'var(--text-main)', lineHeight: 1.6 }}>{session.feedback}</p>
        </div>
      )}

      <div className="answers-list" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        {answers.length === 0 ? (
          <div className="glass-card" style={{ padding: '3rem', textAlign: 'center' }}>
            <p>No answers recorded for this session.</p>
          </div>
        ) : (
          answers.map((ans, idx) => (
            <div key={ans.id} className="glass-card" style={{ padding: '2rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.5rem', borderBottom: '1px solid var(--border)', paddingBottom: '1rem' }}>
                <h3 style={{ margin: 0, color: 'var(--text-main)' }}>Question {idx + 1}</h3>
                <div style={{ padding: '0.25rem 1rem', background: 'rgba(129, 140, 248, 0.1)', borderRadius: '100px', color: 'var(--primary)', fontWeight: 700 }}>
                  Score: {ans.score || 'N/A'}/10
                </div>
              </div>
              
              <div style={{ marginBottom: '1.5rem' }}>
                <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.5rem', letterSpacing: '0.05rem' }}>Your Answer</h4>
                {ans.code ? (
                  <pre style={{ 
                    color: '#a5b4fc', 
                    lineHeight: 1.6, 
                    background: 'rgba(15, 23, 42, 0.5)', 
                    padding: '1.5rem', 
                    borderRadius: '12px', 
                    overflowX: 'auto',
                    fontFamily: 'monospace',
                    fontSize: '0.9rem',
                    border: '1px solid rgba(129, 140, 248, 0.2)'
                  }}>
                    <code>{ans.code}</code>
                  </pre>
                ) : (
                  <p style={{ color: 'var(--text-main)', lineHeight: 1.6, background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '8px' }}>
                    {ans.text || <i>No audio/text provided</i>}
                  </p>
                )}
              </div>

              <div>
                <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: 'var(--primary)', marginBottom: '0.5rem', letterSpacing: '0.05rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Star size={14} /> AI Feedback
                </h4>
                <p style={{ color: 'var(--text-dim)', lineHeight: 1.6, fontStyle: 'italic' }}>
                  {ans.ai_feedback || 'No feedback available.'}
                </p>
              </div>
            </div>
          ))
        )}
      </div>

      <div style={{ marginTop: '3rem', textAlign: 'center' }}>
        <Link to="/dashboard" className="btn-primary" style={{ padding: '1rem 3rem', fontSize: '1.1rem' }}>
          <CheckCircle size={20} /> Finish Review
        </Link>
      </div>

      <style>{`
        .results-container {
          max-width: 900px;
          margin: 0 auto;
          padding: 2rem 0;
        }
      `}</style>
    </div>
  );
};

export default SessionResults;
