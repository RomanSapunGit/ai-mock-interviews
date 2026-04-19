import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, Send, Loader2, Settings2, Hash, Target } from 'lucide-react';
import { interviewService } from '../services/interviewService';
import { useAuth } from '../context/AuthContext';

const CreateInterview = () => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [topic, setTopic] = useState('');
  const [count, setCount] = useState(5);
  const [text, setText] = useState('');
  const [files, setFiles] = useState([]);
  const [interviewType, setInterviewType] = useState('behavioral');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { user } = useAuth();
  const userId = user?.id;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {

      const interview = await interviewService.createInterview({
        title,
        description,
        user_id: userId,
        interview_type: interviewType
      });


      const formData = new FormData();
      formData.append('interview_id', interview.id);
      if (text) formData.append('text', text);
      files.forEach(file => formData.append('files', file));

      formData.append('count', count.toString());
      if (topic) formData.append('topic', topic);

      await interviewService.ingestQuestions(formData);


      navigate('/dashboard');
    } catch (err) {
      console.error(err);
      alert('Failed to create interview');
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
  };

  return (
    <div className="create-container">
      <header className="page-header">
        <h1>New Interview</h1>
        <p className="text-muted">Configure your mock interview and provide context documents</p>
      </header>

      <form onSubmit={handleSubmit} className="create-form">
        <div className="form-section glass-card shadow-lg">
          <div className="section-header">
            <Settings2 size={20} className="text-primary" />
            <h3>Basic Info & Settings</h3>
          </div>

          <div className="input-grid">
            <div className="input-group full-width">
              <label>Interview Title</label>
              <input
                className="glass-input"
                placeholder="e.g. Senior Frontend Engineer"
                value={title}
                onChange={e => setTitle(e.target.value)}
                required
              />
            </div>

            <div className="input-group full-width">
              <label>Interview Type</label>
              <div className="type-toggle glass-card">
                <button
                  type="button"
                  className={interviewType === 'behavioral' ? 'active' : ''}
                  onClick={() => setInterviewType('behavioral')}
                >
                  Behavioral
                </button>
                <button
                  type="button"
                  className={interviewType === 'coding' ? 'active' : ''}
                  onClick={() => setInterviewType('coding')}
                >
                  Coding (Technical)
                </button>
              </div>
            </div>

            <div className="input-group">
              <label><Target size={14} /> Target Topic (Optional)</label>
              <input
                className="glass-input"
                placeholder="e.g. System Design, React"
                value={topic}
                onChange={e => setTopic(e.target.value)}
              />
            </div>

            <div className="input-group">
              <label><Hash size={14} /> Question Count</label>
              <input
                type="number"
                className="glass-input"
                min="1" max="20"
                value={count}
                onChange={e => setCount(parseInt(e.target.value) || 5)}
              />
            </div>

            <div className="input-group full-width">
              <label>Description (Optional)</label>
              <textarea
                className="glass-input"
                placeholder="Focus on React and System Design..."
                value={description}
                onChange={e => setDescription(e.target.value)}
                rows={2}
              />
            </div>
          </div>
        </div>

        <div className="form-section glass-card shadow-lg">
          <div className="section-header">
            <FileText size={20} className="text-primary" />
            <h3>Context & Documents</h3>
          </div>
          <p className="section-hint">Provide text or upload PDF/TXT files to generate questions from.</p>

          <div className="input-group">
            <label>Paste Job Description or Notes</label>
            <textarea
              className="glass-input"
              placeholder="Paste text here..."
              value={text}
              onChange={e => setText(e.target.value)}
              rows={5}
            />
          </div>

          <div className="file-upload">
            <label className="file-label">
              <Upload size={24} />
              <span>{files.length > 0 ? `${files.length} files selected` : 'Click to upload documents (PDF, TXT)'}</span>
              <input type="file" multiple onChange={handleFileChange} />
            </label>
            <div className="file-list">
              {files.map((f, i) => <div key={i} className="file-tag">{f.name}</div>)}
            </div>
          </div>
        </div>

        <div className="actions">
          <button type="button" onClick={() => navigate('/dashboard')} className="btn-ghost">Cancel</button>
          <button type="submit" className="btn-primary main-cta" disabled={loading}>
            {loading ? <><Loader2 className="animate-spin" size={18} /> Initializing...</> : <><Send size={18} /> Create & Generate</>}
          </button>
        </div>
      </form>

      <style>{`
        .create-container { max-width: 800px; margin: 0 auto; padding-bottom: 4rem; }
        .page-header { margin-bottom: 2.5rem; }
        .create-form { display: flex; flex-direction: column; gap: 2.5rem; }
        .form-section { padding: 2.5rem; display: flex; flex-direction: column; gap: 1.5rem; border-radius: 20px; }
        .section-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem; }
        .section-header h3 { font-size: 1.3rem; margin: 0; font-weight: 700; color: var(--text-main); }

        .input-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
        .full-width { grid-column: span 2; }

        .input-group { display: flex; flex-direction: column; gap: 0.6rem; }
        label { font-size: 0.85rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.05rem; display: flex; align-items: center; gap: 0.5rem; }

        .section-hint { font-size: 0.9rem; color: var(--text-dim); line-height: 1.6; margin-top: -0.5rem; }

        .file-upload {
          border: 2px dashed rgba(129, 140, 248, 0.3);
          border-radius: 16px;
          padding: 3rem;
          text-align: center;
          transition: all 0.3s;
          background: rgba(255,255,255,0.01);
        }
        .file-upload:hover { border-color: var(--primary); background: rgba(129, 140, 248, 0.02); }
        .file-label { cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 1rem; color: var(--text-muted); font-weight: 600; }
        .file-label input { display: none; }

        .file-list { display: flex; flex-wrap: wrap; gap: 0.6rem; margin-top: 1.5rem; justify-content: center; }
        .file-tag { background: rgba(129, 140, 248, 0.1); color: #a5b4fc; padding: 0.3rem 0.8rem; border-radius: 100px; font-size: 0.8rem; font-weight: 600; }

        .actions { display: flex; justify-content: flex-end; gap: 1.25rem; margin-top: 1.5rem; }
        .main-cta { padding: 0.85rem 2rem; font-weight: 700; border-radius: 12px; }

        .type-toggle { display: flex; padding: 0.3rem; border-radius: 12px; background: rgba(255,255,255,0.03); }
        .type-toggle button { flex: 1; padding: 0.8rem; border-radius: 9px; border: none; background: transparent; color: var(--text-dim); font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .type-toggle button.active { background: var(--primary); color: white; box-shadow: 0 4px 12px rgba(129, 140, 248, 0.4); }

        .animate-spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default CreateInterview;
