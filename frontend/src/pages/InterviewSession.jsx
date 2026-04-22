import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Send, Square, CheckCircle, Loader2, Volume2, Eye, EyeOff } from 'lucide-react';
import { sessionService } from '../services/sessionService';
import { API_WS_URL } from '../config';
import CodeEditor from '../components/CodeEditor';
import './InterviewSession.css';

const InterviewSession = () => {
  const { id: sessionId } = useParams();
  const navigate = useNavigate();

  const [session, setSession] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [showTranscript, setShowTranscript] = useState(false);
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [evalResult, setEvalResult] = useState(null);
  const [editableExamples, setEditableExamples] = useState('');
  const [audioBlocked, setAudioBlocked] = useState(false);
  const [started, setStarted] = useState(() => {
    return localStorage.getItem(`started_${sessionId}`) === 'true';
  });

  const audioRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const aiAudioChunksRef = useRef([]);
  const userAudioChunksRef = useRef([]);
  const stoppingForPlaybackRef = useRef(false);
  const ws = useRef(null);


  const currentQuestionRef = useRef(currentQuestion);
  const isRecordingRef = useRef(isRecording);
  const isPlayingRef = useRef(isPlaying);

  useEffect(() => { currentQuestionRef.current = currentQuestion; }, [currentQuestion]);
  useEffect(() => { isRecordingRef.current = isRecording; }, [isRecording]);
  useEffect(() => { isPlayingRef.current = isPlaying; }, [isPlaying]);

  useEffect(() => {
    if (started) {
      localStorage.setItem(`started_${sessionId}`, 'true');
      connectWebSocket();
    }
    return () => {
      if (ws.current) ws.current.close();
    };
  }, [sessionId, started]);


  useEffect(() => {
    if (!started || !currentQuestion) return;
    const timer = setInterval(() => {
      if (window.currentCode) {
        localStorage.setItem(`code_${sessionId}_${currentQuestion.id}`, window.currentCode);
      }
      if (window.currentLanguage) {
        localStorage.setItem(`lang_${sessionId}_${currentQuestion.id}`, window.currentLanguage);
      }
      if (feedback) {
        localStorage.setItem(`feedback_${sessionId}_${currentQuestion.id}`, feedback);
      }
      if (evalResult) {
        localStorage.setItem(`eval_${sessionId}_${currentQuestion.id}`, JSON.stringify(evalResult));
      }
      if (answer) {
        localStorage.setItem(`answer_${sessionId}_${currentQuestion.id}`, answer);
      }
      if (editableExamples) {
        localStorage.setItem(`examples_${sessionId}_${currentQuestion.id}`, editableExamples);
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [sessionId, started, currentQuestion]);

  const connectWebSocket = () => {
    const socket = new WebSocket(`${API_WS_URL}/sessions/${sessionId}/ws`);

    socket.onopen = () => {
      console.log('WebSocket connected');
      setLoading(false);
    };

    socket.onmessage = async (event) => {
      const data = JSON.parse(event.data);
      console.log('WS Message:', data);

      switch (data.type) {
        case 'question':
          const qData = {
            id: data.question_id,
            text: data.text,
            order: data.order,
            is_followup: data.is_followup || false,
            question_type: data.question_type || 'behavioral',
            starter_code: data.starter_code || '',
            examples: data.examples || '',
            category: data.category || '',
          };


          const savedCode = localStorage.getItem(`code_${sessionId}_${qData.id}`);
          if (savedCode) {
            qData.starter_code = savedCode;
            window.currentCode = savedCode;
          } else {
            window.currentCode = qData.starter_code;
          }
          const savedLang = localStorage.getItem(`lang_${sessionId}_${qData.id}`);
          if (savedLang) {
            window.currentLanguage = savedLang;
          } else {
            window.currentLanguage = 'python';
          }

          setCurrentQuestion(qData);
          currentQuestionRef.current = qData;
          aiAudioChunksRef.current = [];
          userAudioChunksRef.current = [];
          if (audioRef.current) audioRef.current.src = '';
          setAnswer('');
          setSubmitting(false);


          const savedFeedback = localStorage.getItem(`feedback_${sessionId}_${qData.id}`);
          setFeedback(savedFeedback || null);

          const savedEval = localStorage.getItem(`eval_${sessionId}_${qData.id}`);
          if (savedEval) {
            try {
              setEvalResult(JSON.parse(savedEval));
            } catch (e) {
              setEvalResult(null);
            }
          } else {
            setEvalResult(null);
          }

          const savedAnswer = localStorage.getItem(`answer_${sessionId}_${qData.id}`);
          setAnswer(savedAnswer || '');

          const savedExamples = localStorage.getItem(`examples_${sessionId}_${qData.id}`);
          setEditableExamples(savedExamples || qData.examples || '');

          setShowTranscript(false);


          if (qData.question_type === 'coding') {
            setTimeout(() => startRecording(), 500);
          }
          break;

        case 'audio_chunk':
          handleIncomingAudio(data.data);
          break;

        case 'audio_done':
          playAggregatedAudio();
          break;

        case 'evaluation':
          setEvalResult({
            score: data.score,
            feedback: data.feedback
          });
          setSubmitting(false);
          aiAudioChunksRef.current = [];
          userAudioChunksRef.current = [];
          if (audioRef.current) audioRef.current.src = '';
          break;

        case 'hint':
          setFeedback(data.text);
          setSubmitting(false);
          aiAudioChunksRef.current = [];
          if (audioRef.current) audioRef.current.src = '';
          break;

        case 'evaluating_overall':
          setSubmitting(true);
          setFeedback("Generating overall session feedback...");
          break;

        case 'session_complete':
          cleanupSessionStorage();
          setFeedback("All questions completed! Redirecting to results...");
          setTimeout(() => navigate(`/sessions/${sessionId}/results`), 2000);
          setCurrentQuestion(null);
          break;

        case 'error':
          alert(`Error: ${data.detail}`);
          break;
        default:
          break;
      }
    };

    socket.onclose = () => {
      console.log('WebSocket disconnected');
    };

    ws.current = socket;
  };

  const handleIncomingAudio = (base64Data) => {
    const binaryString = window.atob(base64Data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    aiAudioChunksRef.current.push(bytes);
  };

  const playAggregatedAudio = async () => {
    if (aiAudioChunksRef.current.length === 0) {

      startRecording();
      return;
    }


    const q = currentQuestionRef.current;
    const isCoding = q?.question_type === 'coding';
    if (!isCoding) {
      stoppingForPlaybackRef.current = true;
      stopRecording();
    }
    setIsPlaying(true);
    isPlayingRef.current = true;

    console.log(`Playing AI audio with ${aiAudioChunksRef.current.length} chunks`);
    const blob = new Blob(aiAudioChunksRef.current, { type: 'audio/mpeg' });
    const url = URL.createObjectURL(blob);

    if (audioRef.current) {
      audioRef.current.src = url;
      audioRef.current.onended = () => {
        console.log("AI audio playback ended");
        setIsPlaying(false);
        isPlayingRef.current = false;
        URL.revokeObjectURL(url);

        aiAudioChunksRef.current = [];

        if (!isCoding) {
          startRecording();
        }
      };

      try {
        await audioRef.current.play();
        setAudioBlocked(false);
      } catch (err) {
        console.warn("Autoplay blocked:", err);
        setAudioBlocked(true);
        setIsPlaying(false);
      }
    }
  };

  const handleReplayAudio = async () => {
    if (audioRef.current && !isPlaying && aiAudioChunksRef.current.length > 0) {
      try {
        setIsPlaying(true);
        const blob = new Blob(aiAudioChunksRef.current, { type: 'audio/mpeg' });
        const url = URL.createObjectURL(blob);
        audioRef.current.src = url;
        audioRef.current.onended = () => {
          setIsPlaying(false);
          URL.revokeObjectURL(url);
          startRecording();
        };
        await audioRef.current.play();
      } catch (err) {
        console.error("Replay failed:", err);
        setIsPlaying(false);
      }
    }
  };

  const handleStartInterview = async () => {
    setStarted(true);

    if (audioRef.current) {
      try {
        await audioRef.current.play();

        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach(track => track.stop());
      } catch (e) {
        console.warn("Pre-emptive priming failed", e);
      }
    }
  };

  const handleUnblockAudio = async () => {
    if (audioRef.current && audioBlocked) {
      try {
        await audioRef.current.play();
        setAudioBlocked(false);
        setIsPlaying(true);
      } catch (err) {
        console.error("Manual play failed:", err);
      }
    }
  };

  const startRecording = async () => {
    const q = currentQuestionRef.current;
    const canStartWhilePlaying = q?.question_type === 'coding';
    if (isRecordingRef.current || (isPlayingRef.current && !canStartWhilePlaying) || !q) {
      console.log('startRecording blocked:', { isRecording: isRecordingRef.current, isPlaying: isPlayingRef.current, hasQuestion: !!q });
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      ws.current.send(JSON.stringify({
        type: 'answer_audio_start',
        question_id: q.id,
        filename: 'answer.webm'
      }));

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && ws.current.readyState === WebSocket.OPEN) {
          if (q.question_type === 'coding') {
            userAudioChunksRef.current.push(event.data);
          } else {
            ws.current.send(event.data);
          }
        }
      };

      mediaRecorder.onstop = () => {
        stream.getTracks().forEach(track => track.stop());

        if (stoppingForPlaybackRef.current) {
          stoppingForPlaybackRef.current = false;
          return;
        }

        const q = currentQuestionRef.current;
        if (ws.current && ws.current.readyState === WebSocket.OPEN && q) {
          if (q.question_type === 'coding') {

             ws.current.send(JSON.stringify({
               type: 'answer_audio_start',
               question_id: q.id,
               filename: 'explanation.webm'
             }));

             userAudioChunksRef.current.forEach(chunk => {
               ws.current.send(chunk);
             });
          }

          const payload = { type: 'answer_audio_end' };
          if (q.question_type === 'coding') {
            payload.code = window.currentCode;
            payload.language = window.currentLanguage;
            payload.examples = editableExamples;
          }
          ws.current.send(JSON.stringify(payload));
          setSubmitting(true);
        }
      };

      mediaRecorder.start(250);
      setIsRecording(true);
      isRecordingRef.current = true;
    } catch (err) {
      console.error('Failed to start recording', err);

      const msg = err.name === 'NotAllowedError' ? 'Microphone access denied. Please allow it in the browser settings.' :
                  (err.name === 'NotFoundError' ? 'No microphone found.' : `Microphone error: ${err.name} - ${err.message}`);
      alert(msg);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      isRecordingRef.current = false;
    }
  };

  const handleTextSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!answer) return;

    setSubmitting(true);
    ws.current.send(JSON.stringify({
      type: 'answer_text',
      question_id: currentQuestion.id,
      text: answer
    }));
  };

  const handleCodeSubmit = (code, language) => {
    if (!code.trim() || !currentQuestion) return;
    window.currentCode = code;
    window.currentLanguage = language;
    setSubmitting(true);
    ws.current.send(JSON.stringify({
      type: 'answer_code',
      question_id: currentQuestion.id,
      code: code,
      language: language,
      examples: editableExamples,
    }));
    stopRecording();
  };

  const handleRequestHint = () => {
    const q = currentQuestionRef.current;
    if (!q) return;
    ws.current.send(JSON.stringify({
      type: 'request_hint',
      question_id: q.id,
      code: window.currentCode,
      language: window.currentLanguage,
      examples: editableExamples,
    }));
  };

  const cleanupSessionStorage = () => {
    localStorage.removeItem(`started_${sessionId}`);


    Object.keys(localStorage).forEach(key => {
      if (key.includes(`_${sessionId}_`)) {
        localStorage.removeItem(key);
      }
    });
  };

  const handleEndSession = async () => {
    try {
      cleanupSessionStorage();
      await sessionService.endSession(sessionId);
      navigate(`/sessions/${sessionId}/results`);
    } catch (err) {
      console.error(err);
      navigate(`/sessions/${sessionId}/results`);
    }
  };

  if (loading && started) return <div className="loading">Connecting to session...</div>;

  const showPulse = isPlaying || isRecording || isTranscribing;

  return (
    <div className="session-container">
      <audio ref={audioRef} hidden />

      <header className="session-header">
        <div className="session-info">
          <span className="live-badge">LIVE SESSION</span>
          <h2>Practice Session</h2>
        </div>
        <button onClick={handleEndSession} className="btn-ghost">End Session</button>
      </header>

      <div className="main-layout">
        {!started ? (
           <div className="start-overlay glass-card">
              <Volume2 size={64} className="text-primary" />
              <h2>Ready to Start?</h2>
              <p>We'll use audio for questions. Click below to begin.</p>
              <button onClick={handleStartInterview} className="btn-primary start-btn">
                 Start Interview
              </button>
           </div>
        ) : (
          <>
            <div className="question-area">
              <AnimatePresence mode="wait">
                {currentQuestion ? (
                  <motion.div
                    key={currentQuestion.id}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="question-card glass-card"
                  >
                    <div className={`voice-visualizer ${showPulse ? 'active' : ''} ${isRecording ? 'recording' : ''}`}>
                      <div className="ring r1"></div>
                      <div className="ring r2"></div>
                      <div className="ring r3"></div>
                      <div className="center-orb" onClick={handleReplayAudio} style={{ cursor: aiAudioChunksRef.current.length > 0 && !isPlaying ? 'pointer' : 'default' }}>
                        {audioBlocked ? (
                          <button onClick={(e) => { e.stopPropagation(); handleUnblockAudio(); }} className="unblock-btn" title="Play Question">
                            <Volume2 size={40} />
                          </button>
                        ) : (
                          <Volume2 size={40} className="voice-icon" />
                        )}
                      </div>
                    </div>

                    {audioBlocked && <p className="unblock-notice">Click the icon to hear the question</p>}

                    <h3 className="status-text">
                      {isRecording ? 'Listening for your explanation...' : (isTranscribing ? 'Transcribing...' : (isPlaying ? 'Playing question...' : (submitting ? 'Evaluating your answer...' : 'Listen to the question')))}
                    </h3>

                    <AnimatePresence>
                      {currentQuestion.is_followup && (
                        <motion.div
                          initial={{ opacity: 0, y: -20 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="followup-badge"
                        >
                          Follow-up Question
                        </motion.div>
                      )}
                    </AnimatePresence>

                    <div className="transcript-container">
                      <button
                        onClick={() => setShowTranscript(!showTranscript)}
                        className="btn-transcript"
                      >
                        {showTranscript ? <><EyeOff size={16} /> Hide Transcript</> : <><Eye size={16} /> Show Transcript</>}
                      </button>

                      {showTranscript && (
                        <motion.p
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="q-content"
                        >
                          {currentQuestion.text}
                        </motion.p>
                      )}
                    </div>

                    <AnimatePresence>
                      {evalResult && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          className="eval-mini-card"
                        >
                          <div className="eval-score">
                            <span>Score:</span> <strong>{evalResult.score}/10</strong>
                          </div>
                          <p className="eval-feedback">{evalResult.feedback}</p>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    <AnimatePresence>
                      {feedback && feedback.length > 0 && !evalResult && (
                        <motion.div
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="hint-alert glass-card"
                        >
                          <div className="hint-header">AI TECHNICAL HINT</div>
                          <p className="hint-content">{feedback}</p>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    <div className="q-meta">
                       {currentQuestion.category && <span className="category-tag">{currentQuestion.category}</span>}
                    </div>
                  </motion.div>
                ) : (
                  feedback ? (
                    <motion.div className="feedback-card glass-card">
                       {feedback.includes("Generating") ? (
                         <Loader2 size={48} className="animate-spin text-primary" />
                       ) : (
                         <CheckCircle size={48} className="text-success" />
                       )}
                       <h3>{feedback}</h3>
                       {!feedback.includes("Redirecting") && !feedback.includes("Generating") && (
                         <button onClick={handleEndSession} className="btn-primary">Back to Dashboard</button>
                       )}
                    </motion.div>
                  ) : (
                    <div className="loading"><Loader2 className="animate-spin" /> Preparing next question...</div>
                  )
                )}
              </AnimatePresence>
            </div>

            <div className="answer-area">
              {currentQuestion?.question_type === 'coding' ? (
                <div className="coding-answer-container">
                  <CodeEditor
                    key={currentQuestion.id}
                    starterCode={currentQuestion.starter_code || ''}
                    onChange={(c) => { window.currentCode = c; }}
                    onLanguageChange={(l) => { window.currentLanguage = l; }}
                    onSubmit={handleCodeSubmit}
                    disabled={submitting || !currentQuestion}
                  />
                  <div className="coding-examples glass-card">
                    <div className="examples-header">
                      <Eye size={16} />
                      <h4>Problem Examples (Editable)</h4>
                    </div>
                    <textarea
                      className="examples-input"
                      value={editableExamples}
                      onChange={(e) => setEditableExamples(e.target.value)}
                      placeholder="Input: ... \nOutput: ..."
                      disabled={submitting}
                    />
                  </div>
                  <div className="coding-actions glass-card">
                    <button
                      type="button"
                      className={`btn-record ${isRecording ? 'active' : ''}`}
                      onClick={isRecording ? stopRecording : startRecording}
                      disabled={submitting || isTranscribing || !currentQuestion}
                    >
                      {isRecording ? <Square size={20} /> : <Mic size={20} />}
                      {isRecording ? 'Stop Recording' : 'Record Explanation/Context'}
                    </button>
                    <button
                      type="button"
                      className="btn-ghost"
                      onClick={handleRequestHint}
                      disabled={submitting || !currentQuestion}
                    >
                      Get AI Hint
                    </button>
                    <p className="hint-text">Recording is active. Speak to explain your approach.</p>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleTextSubmit} className="answer-box glass-card">
                  <textarea
                    className="glass-input answer-input"
                    placeholder={isTranscribing ? "Transcribing..." : "Enter your response..."}
                    value={answer}
                    onChange={e => setAnswer(e.target.value)}
                    disabled={submitting || isRecording || isTranscribing || !currentQuestion}
                  />
                  <div className="answer-actions">
                    <button
                      type="button"
                      className={`btn-record ${isRecording ? 'active' : ''}`}
                      onClick={isRecording ? stopRecording : startRecording}
                      disabled={submitting || isTranscribing || !currentQuestion}
                    >
                      {isRecording ? <Square size={20} /> : <Mic size={20} />}
                      {isRecording ? 'Stop Recording' : 'Record Answer'}
                    </button>

                    <button
                      type="submit"
                      className="btn-primary"
                      disabled={submitting || isTranscribing || !answer || !currentQuestion}
                    >
                      {submitting ? <Loader2 className="animate-spin" size={18} /> : <><Send size={18} /> Submit Answer</>}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default InterviewSession;
