import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, ChevronLeft, Loader2, RefreshCw, Settings2, Upload, FileText, X, PlusCircle, Trash2, Hash } from 'lucide-react';
import { interviewService } from '../services/interviewService';
import { sessionService } from '../services/sessionService';
import { useAuth } from '../context/AuthContext';

const InterviewDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [interview, setInterview] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
   const [deletingId, setDeletingId] = useState(null);
   const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  
  // Generation Params
  const [count, setCount] = useState(5);
  const [topic, setTopic] = useState('');
  
  // Modal Context Params
  const [contextText, setContextText] = useState('');
  const [files, setFiles] = useState([]);
  
  const { user } = useAuth();
  const userId = user?.id;

  useEffect(() => {
    fetchData();
  }, [id]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [intv, qstns] = await Promise.all([
        interviewService.getInterview(id),
        interviewService.listQuestions(id)
      ]);
      setInterview(intv);
      setQuestions(qstns);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
  };

  const handleRegenerate = async (useModalContext = false) => {
    setRegenerating(true);
    try {
      if (useModalContext) {
        // Full regeneration with new context
        const formData = new FormData();
        formData.append('interview_id', id);
        formData.append('count', count.toString());
        if (topic) formData.append('topic', topic);
        if (contextText) formData.append('text', contextText);
        files.forEach(f => formData.append('files', f));
        
        await interviewService.ingestQuestions(formData);
        setIsModalOpen(false);
        setContextText('');
        setFiles([]);
      } else {
        // Just reset existing questions to active
        await interviewService.resetQuestions(id);
      }
      
      // Refresh questions after a delay
      setTimeout(() => fetchData(), useModalContext ? 3000 : 1000);
    } catch (err) {
      console.error(err);
      alert('Failed to trigger question generation');
    } finally {
      setRegenerating(false);
    }
  };

  const handleDeleteQuestion = async (questionId) => {
    setConfirmDeleteId(questionId);
  };

  const confirmDelete = async () => {
    const questionId = confirmDeleteId;
    if (!questionId) return;
    
    setConfirmDeleteId(null);
    setDeletingId(questionId);
    try {
      await interviewService.deleteQuestion(id, questionId);
      await fetchData();
    } catch (err) {
      console.error(err);
      alert('Failed to delete question');
    } finally {
      setDeletingId(null);
    }
  };

  const handleStartSession = async () => {
    try {
      const session = await sessionService.startSession(userId, id);
      navigate(`/sessions/${session.id}`);
    } catch (err) {
      console.error(err);
      alert('Failed to start session');
    }
  };

  if (loading && !interview) return <div className="loading">Loading details...</div>;
  if (!interview) return <div className="error">Interview not found.</div>;

  return (
    <div className="detail-container">
      <header className="detail-header">
        <Link to="/dashboard" className="btn-ghost btn-sm">
          <ChevronLeft size={18} /> Back to Dashboard
        </Link>
        <div className="header-main">
          <div>
            <div className="title-row">
              <h1>{interview.title}</h1>
              <span className={`type-badge ${interview.interview_type}`}>{interview.interview_type}</span>
            </div>
            <p className="description">{interview.description}</p>
          </div>
          <div className="header-actions">
            <button 
              onClick={handleStartSession} 
              className="btn-primary main-cta"
              disabled={interview.status === 'completed' || (questions.length > 0 && questions.every(q => q.status === 'completed'))}
              style={(interview.status === 'completed' || (questions.length > 0 && questions.every(q => q.status === 'completed'))) ? { opacity: 0.5, cursor: 'not-allowed' } : {}}
            >
              <Play size={18} fill="currentColor" /> 
              {(interview.status === 'completed' || (questions.length > 0 && questions.every(q => q.status === 'completed'))) ? 'Completed' : 'Start Session'}
            </button>
          </div>
        </div>
      </header>

      <div className="detail-grid">
        <section className="questions-section glass-card">
          <div className="section-header">
            <h3>Interview Questions</h3>
            <span className="count-badge">{questions.length} Questions</span>
          </div>
          
          <div className="questions-list">
            {questions.length === 0 ? (
              <div className="empty-questions">
                {regenerating && <Loader2 className="animate-spin" />}
                <p>{regenerating ? "Generating questions in the background..." : "nothing to answer to"}</p>
              </div>
            ) : (
              questions.map((q, i) => (
                <div key={q.id || i} className={`question-item ${q.status === 'completed' ? 'completed' : ''}`}>
                  <div className="q-num">{i + 1}</div>
                  <div className="q-body">
                    <p className="q-text">{q.text}</p>
                    <div className="q-footer">
                      <div className="q-tags">
                        {q.status === 'completed' && <span className="tag status-completed">Completed</span>}
                        {q.status !== 'completed' && <span className="tag status-pending">Unanswered</span>}
                        {q.difficulty && <span className={`tag diff-${q.difficulty}`}>{q.difficulty}</span>}
                        {q.category && <span className="tag category">{q.category}</span>}
                      </div>
                      <button 
                        onClick={() => handleDeleteQuestion(q.id)} 
                        className="btn-delete"
                        disabled={deletingId === q.id}
                        title="Delete Question"
                      >
                        {deletingId === q.id ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        <aside className="controls-sidebar">
          <div className="glass-card sidebar-group">
            <div className="group-header">
              <Settings2 size={18} />
              <h3>Parameters</h3>
            </div>
            
            <div className="control-item">
              <label>Question Count</label>
              <input type="number" className="glass-input" value={count} onChange={e => setCount(parseInt(e.target.value))} min="1" max="20" />
            </div>

            <div className="control-item">
              <label>Current Area/Topic</label>
              <input type="text" className="glass-input" placeholder="e.g. System Design" value={topic} onChange={e => setTopic(e.target.value)} />
            </div>

            <button onClick={() => handleRegenerate(false)} className="btn-secondary w-full" disabled={regenerating}>
              {regenerating ? <Loader2 className="animate-spin" size={16} /> : <RefreshCw size={16} />}
              Regenerate
            </button>
          </div>

          <div className="glass-card sidebar-group accent-group">
            <div className="group-header">
              <PlusCircle size={18} />
              <h3>Add Context</h3>
            </div>
            <p className="sidebar-hint">Need more specific questions? Upload new documents or paste extra notes.</p>
            <button onClick={() => setIsModalOpen(true)} className="btn-ghost-prime w-full">
              <Upload size={16} /> Add Documents
            </button>
          </div>
        </aside>
      </div>

      <AnimatePresence>
        {confirmDeleteId && (
          <div className="modal-overlay" onClick={() => setConfirmDeleteId(null)}>
            <motion.div 
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="modal-content glass-card delete-confirm-modal"
              onClick={e => e.stopPropagation()}
            >
              <h3>Delete Question?</h3>
              <p>Are you sure you want to remove this question? This action cannot be undone.</p>
              <div className="modal-footer">
                <button onClick={() => setConfirmDeleteId(null)} className="btn-ghost">Cancel</button>
                <button onClick={confirmDelete} className="btn-danger">Delete Question</button>
              </div>
            </motion.div>
          </div>
        )}

        {isModalOpen && (
          <div className="modal-overlay" onClick={() => setIsModalOpen(false)}>
            <motion.div 
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="modal-content glass-card premium"
              onClick={e => e.stopPropagation()}
            >
              <div className="modal-header">
                <h3>Add Interview Context</h3>
                <button onClick={() => setIsModalOpen(false)} className="close-btn"><X size={20} /></button>
              </div>

              <div className="modal-body">
                <div className="form-group">
                  <label><FileText size={16} /> Paste New Context</label>
                  <textarea 
                    className="glass-input" 
                    placeholder="Paste job details, tech requirements, or your notes here..." 
                    value={contextText}
                    onChange={e => setContextText(e.target.value)}
                    rows={8}
                  />
                </div>

                <div className="form-group mini-group">
                  <label><Hash size={16} /> Question Count</label>
                  <input 
                    type="number" 
                    className="glass-input" 
                    min="1" max="20"
                    value={count} 
                    onChange={e => setCount(parseInt(e.target.value) || 5)} 
                  />
                </div>

                <div className="upload-zone">
                  <label className="upload-label">
                    <Upload size={24} />
                    <span>{files.length > 0 ? `${files.length} files selected` : "Drag or Click to add PDFs/TXTs"}</span>
                    <input type="file" multiple onChange={handleFileChange} />
                  </label>
                  {files.length > 0 && (
                    <div className="mini-file-list">
                      {files.map((f, i) => <span key={i} className="f-tag">{f.name}</span>)}
                    </div>
                  )}
                </div>
              </div>

              <div className="modal-footer">
                <button onClick={() => setIsModalOpen(false)} className="btn-ghost">Cancel</button>
                <button onClick={() => handleRegenerate(true)} className="btn-primary" disabled={regenerating || (!contextText && files.length === 0)}>
                  {regenerating ? <><Loader2 className="animate-spin" size={18} /> Processing...</> : <><RefreshCw size={18} /> Update & Regenerate</>}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      <style>{`
        .detail-container { display: flex; flex-direction: column; gap: 2.5rem; }
        .detail-header { display: flex; flex-direction: column; gap: 1.5rem; }
        .header-main { display: flex; justify-content: space-between; align-items: flex-end; }
        h1 { font-size: 2.5rem; background: linear-gradient(to right, #fff, #a5b4fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; }
        .description { color: var(--text-muted); font-size: 1.1rem; max-width: 600px; margin-top: 0.5rem; }
        .main-cta { padding: 0.85rem 2rem; font-size: 1.1rem; border-radius: 12px; }

        .detail-grid { display: grid; grid-template-columns: 1fr 340px; gap: 2.5rem; align-items: start; }
        .questions-section { padding: 2rem; }
        .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2.5rem; }
        .count-badge { background: var(--primary-glow); color: var(--primary); padding: 0.25rem 1rem; border-radius: 100px; font-weight: 700; font-size: 0.8rem; }
        
        .questions-list { display: flex; flex-direction: column; gap: 1.25rem; }
        .question-item { display: flex; gap: 1.5rem; padding: 1.75rem; border-radius: 16px; background: rgba(255,255,255,0.02); border: 1px solid var(--border); transition: all 0.3s; }
        .question-item:hover { transform: translateX(8px); border-color: rgba(129, 140, 248, 0.4); background: rgba(255,255,255,0.04); }
        .q-num { width: 36px; height: 36px; background: var(--border); border-radius: 12px; display: flex; align-items: center; justify-content: center; font-weight: 800; color: var(--primary); flex-shrink: 0; font-size: 1rem; }
        .q-body { flex: 1; }
        .q-text { font-size: 1.15rem; line-height: 1.6; margin-bottom: 1rem; color: #e2e8f0; font-weight: 400; }
        
        .q-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 1rem; }
        .q-tags { display: flex; gap: 0.5rem; }
        .btn-delete { background: transparent; border: none; color: var(--text-dim); cursor: pointer; padding: 0.5rem; border-radius: 8px; transition: all 0.2s; display: flex; align-items: center; justify-content: center; }
        .btn-delete:hover { background: rgba(239, 68, 68, 0.1); color: #f87171; }
        
        .tag { font-size: 0.72rem; padding: 0.2rem 0.75rem; border-radius: 6px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05rem; }
        .diff-easy { background: rgba(34, 197, 94, 0.1); color: #4ade80; }
        .diff-medium { background: rgba(234, 179, yellow, 0.1); color: #fde047; }
        .diff-hard { background: rgba(239, 68, 68, 0.1); color: #f87171; }
        .category { background: rgba(255,255,255,0.05); color: var(--text-dim); }
        .status-completed { background: rgba(16, 185, 129, 0.2); color: #34d399; }
        .status-pending { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }
        .question-item.completed { opacity: 0.6; border-color: rgba(16, 185, 129, 0.3); }

        .controls-sidebar { display: flex; flex-direction: column; gap: 1.5rem; }
        .sidebar-group { padding: 1.75rem; display: flex; flex-direction: column; gap: 1.25rem; }
        .group-header { display: flex; align-items: center; gap: 0.75rem; color: var(--text-main); margin-bottom: 0.5rem; }
        .group-header h3 { font-size: 1.1rem; font-weight: 700; margin: 0; }
        .control-item { display: flex; flex-direction: column; gap: 0.6rem; }
        .control-item label { font-size: 0.8rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.05rem; }
        .sidebar-hint { font-size: 0.85rem; color: var(--text-dim); line-height: 1.5; margin: 0; }
        .accent-group { border-color: var(--primary-glow); background: rgba(129, 140, 248, 0.03); }
        .btn-ghost-prime { border: 1px solid var(--primary-glow); background: transparent; color: var(--primary); padding: 0.85rem; border-radius: 12px; display: flex; align-items: center; justify-content: center; gap: 0.6rem; font-weight: 600; transition: all 0.2s; }
        .btn-ghost-prime:hover { background: var(--primary-glow); color: white; }

        .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.85); backdrop-filter: blur(12px); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 2rem; }
        .modal-content.premium { width: 100%; max-width: 700px; padding: 3rem; border: 1px solid rgba(129, 140, 248, 0.3); border-radius: 24px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); }
        .modal-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2rem; }
        .modal-header h3 { font-size: 1.75rem; font-weight: 800; margin: 0; }
        .close-btn { background: var(--border); border: none; color: var(--text-dim); width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s; }
        .close-btn:hover { background: rgba(255,255,255,0.1); color: white; }
        
        .form-group { display: flex; flex-direction: column; gap: 0.75rem; }
        .form-group label { font-size: 0.95rem; font-weight: 700; color: var(--text-main); display: flex; align-items: center; gap: 0.6rem; }
        .upload-zone { border: 2px dashed var(--border); border-radius: 16px; padding: 2.5rem; text-align: center; transition: all 0.3s; background: rgba(255,255,255,0.01); }
        .upload-zone:hover { border-color: var(--primary); background: rgba(129, 140, 248, 0.02); }
        .upload-label { cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 1rem; color: var(--text-muted); }
        .upload-label input { display: none; }
        
        .mini-file-list { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 1.5rem; justify-content: center; }
        .f-tag { background: var(--border); padding: 0.3rem 0.8rem; border-radius: 100px; font-size: 0.75rem; color: #a5b4fc; font-weight: 600; }
        
        .modal-footer { display: flex; justify-content: flex-end; gap: 1.25rem; margin-top: 3rem; }
        .w-full { width: 100%; display: flex; justify-content: center; gap: 0.6rem; }
        .loading { display: flex; justify-content: center; align-items: center; min-height: 300px; color: var(--text-dim); }
        .animate-spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

        .title-row { display: flex; align-items: center; gap: 1.5rem; }
        .type-badge { padding: 0.3rem 1rem; border-radius: 100px; font-size: 0.8rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05rem; }
        .type-badge.coding { background: rgba(129, 140, 248, 0.2); color: #a5b4fc; border: 1px solid rgba(129, 140, 248, 0.4); }
        .type-badge.behavioral { background: rgba(16, 185, 129, 0.1); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.2); }
        
        .delete-confirm-modal { max-width: 450px !important; padding: 2rem !important; text-align: center; }
        .delete-confirm-modal h3 { margin-bottom: 1rem; color: #f87171; }
        .delete-confirm-modal p { color: var(--text-dim); margin-bottom: 2rem; line-height: 1.5; }
        .btn-danger { background: #ef4444; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 10px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .btn-danger:hover { background: #dc2626; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3); }
        .mini-group { width: 140px; }
      `}</style>
    </div>
  );
};

export default InterviewDetail;
