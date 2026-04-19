import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Play, Clock, Search, Trash2 } from 'lucide-react';
import { userService } from '../services/userService';
import { sessionService } from '../services/sessionService';
import { interviewService } from '../services/interviewService';
import { useAuth } from '../context/AuthContext';

const Dashboard = () => {
  const [interviews, setInterviews] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const navigate = useNavigate();
  const { user } = useAuth();
  const userId = user?.id;

  useEffect(() => {
    if (!userId) {
      navigate('/');
      return;
    }
    fetchDashboardData();
  }, [userId, navigate]);

  const fetchDashboardData = async () => {
    try {
      const [interviewsData, sessionsData] = await Promise.all([
        userService.listUserInterviews(userId),
        sessionService.getUserSessions(userId)
      ]);
      setInterviews(interviewsData);
      setSessions(sessionsData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (e, id) => {
    e.stopPropagation();
    setConfirmDeleteId(id);
  };

  const confirmDelete = async () => {
    const id = confirmDeleteId;
    if (!id) return;

    setDeleting(true);
    try {
      await interviewService.deleteInterview(id);
      await fetchDashboardData();
      setConfirmDeleteId(null);
    } catch (err) {
      console.error("Failed to delete interview:", err);
      alert("Failed to delete interview");
    } finally {
      setDeleting(false);
    }
  };

  const getInterviewTitle = (interviewId) => {
    const interview = interviews.find(i => i.id === interviewId);
    return interview ? interview.title : "Unknown Interview";
  };

  const handleStartSession = async (interviewId) => {
    try {
      const session = await sessionService.startSession(userId, interviewId);
      navigate(`/sessions/${session.id}`);
    } catch (err) {
      console.error(err);
      alert('Failed to start session');
    }
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div>
          <h1>Your Interviews</h1>
          <p className="text-muted">Select an interview to start practicing</p>
        </div>
        <Link to="/interviews/new" className="btn-primary">
          <Plus size={18} /> New Interview
        </Link>
      </header>

      {loading ? (
        <div className="loading">Loading dashboard...</div>
      ) : (
        <div className="dashboard-content" style={{ display: 'flex', flexDirection: 'column', gap: '4rem' }}>
          <section>
            <h2 style={{ marginBottom: '1.5rem', color: 'var(--text-main)', fontSize: '1.5rem' }}>Active Interviews</h2>
            <div className="interview-grid">
              {interviews.length === 0 ? (
                <div className="empty-state glass-card">
                  <Search size={48} className="text-dim" />
                  <p>No interviews found. Create your first one!</p>
                  <Link to="/interviews/new" className="btn-primary">Create New</Link>
                </div>
              ) : (
                interviews.map(interview => (
                  <div key={interview.id} className="interview-card glass-card">
                    <div className="card-header">
                      <h3>{interview.title}</h3>
                      <div className="card-actions">
                        <span className="date"> <Clock size={14} /> {(new Date(interview.created_at || Date.now())).toLocaleDateString()}</span>
                        <button
                          className="btn-icon delete-btn"
                          onClick={(e) => handleDelete(e, interview.id)}
                          title="Delete interview"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                    <p className="description">{interview.description || 'No description provided'}</p>
                    <div className="card-actions">
                      <button
                        onClick={() => handleStartSession(interview.id)}
                        className="btn-primary btn-sm"
                        disabled={interview.status === 'completed'}
                        style={interview.status === 'completed' ? { opacity: 0.5, cursor: 'not-allowed' } : {}}
                      >
                        <Play size={16} fill="currentColor" /> {interview.status === 'completed' ? 'Completed' : 'Start Practice'}
                      </button>
                      <Link to={`/interviews/${interview.id}`} className="btn-ghost btn-sm">Details</Link>
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>

          <section>
            <h2 style={{ marginBottom: '1.5rem', color: 'var(--text-main)', fontSize: '1.5rem' }}>Session History</h2>
            <div className="interview-grid">
              {sessions.length === 0 ? (
                <div className="empty-state glass-card" style={{ padding: '2rem' }}>
                  <p>You haven't completed any sessions yet.</p>
                </div>
              ) : (
                sessions.map(session => (
                  <div key={session.id} className="interview-card glass-card" style={{ background: 'rgba(255,255,255,0.01)' }}>
                    <div className="card-header">
                      <h3>{getInterviewTitle(session.interview_id)}</h3>
                      <span className="date">
                        <Clock size={14} /> {new Date(session.created_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="card-actions" style={{ marginTop: 'auto', paddingTop: '1rem' }}>
                      <Link to={`/sessions/${session.id}/results`} className="btn-ghost btn-sm" style={{ width: '100%', textAlign: 'center' }}>
                        View Results
                      </Link>
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>
      )}

      <AnimatePresence>
        {confirmDeleteId && (
          <div className="modal-overlay" onClick={() => !deleting && setConfirmDeleteId(null)}>
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="modal-content glass-card delete-confirm-modal"
              onClick={e => e.stopPropagation()}
            >
              <h3>Delete Interview?</h3>
              <p>Are you sure you want to permanently delete this interview? All associated sessions, questions, and records will be lost. This action cannot be undone.</p>
              <div className="modal-footer">
                <button onClick={() => setConfirmDeleteId(null)} className="btn-ghost" disabled={deleting}>Cancel</button>
                <button onClick={confirmDelete} className="btn-danger" disabled={deleting}>
                  {deleting ? 'Deleting...' : 'Delete Interview'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      <style>{`
        .dashboard-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-end;
          margin-bottom: 3rem;
        }
        h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
        .interview-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
          gap: 1.5rem;
        }
        .interview-card {
          padding: 1.5rem;
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; }
        .card-header h3 { font-size: 1.1rem; margin: 0; font-weight: 700; color: var(--text-main); line-height: 1.4; }
        .card-actions { display: flex; gap: 0.5rem; align-items: center; }
        .btn-icon.delete-btn { color: #f87171; background: rgba(248,113,113,0.1); border: 1px solid rgba(248,113,113,0.2); padding: 0.5rem; border-radius: 4px; cursor: pointer; }
        .btn-icon.delete-btn:hover { background: #f87171; color: white; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(248,113,113,0.3); }
        .date {
          font-size: 0.75rem;
          color: var(--text-dim);
          display: flex;
          align-items: center;
          gap: 0.25rem;
        }
        .description {
          color: var(--text-muted);
          font-size: 0.95rem;
          flex: 1;
        }
        .card-actions {
          display: flex;
          gap: 1rem;
        }
        .btn-sm {
          padding: 0.5rem 1rem;
          font-size: 0.85rem;
        }
        .empty-state {
          grid-column: 1 / -1;
          padding: 4rem;
          text-align: center;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1.5rem;
        }
        .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.85); backdrop-filter: blur(12px); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 2rem; }
        .delete-confirm-modal { max-width: 450px !important; padding: 2.5rem !important; text-align: center; }
        .delete-confirm-modal h3 { margin-bottom: 1rem; color: #f87171; font-size: 1.5rem; font-weight: 800; }
        .delete-confirm-modal p { color: var(--text-dim); margin-bottom: 2rem; line-height: 1.6; }
        .modal-footer { display: flex; justify-content: flex-end; gap: 1rem; }
        .btn-ghost { background: transparent; padding: 0.8rem 1.5rem; border-radius: 12px; font-weight: 700; color: var(--text-muted); cursor: pointer; transition: all 0.2s; border: none; }
        .btn-ghost:hover { background: rgba(255,255,255,0.05); color: var(--text-main); }
        .btn-danger { background: #ef4444; color: white; border: none; padding: 0.8rem 1.5rem; border-radius: 12px; font-weight: 700; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 0.5rem; }
        .btn-danger:hover:not(:disabled) { background: #dc2626; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3); }
        .btn-danger:disabled { opacity: 0.7; cursor: not-allowed; }
      `}</style>
    </div>
  );
};

export default Dashboard;
