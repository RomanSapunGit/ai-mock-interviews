import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import CreateInterview from './pages/CreateInterview';
import InterviewSession from './pages/InterviewSession';
import InterviewDetail from './pages/InterviewDetail';
import SessionResults from './pages/SessionResults';

function App() {
  return (
    <Router>
      <AuthProvider>
        <div className="app-container">
          <Navbar />
          <main className="content">
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
              <Route path="/interviews/new" element={<ProtectedRoute><CreateInterview /></ProtectedRoute>} />
              <Route path="/interviews/:id" element={<ProtectedRoute><InterviewDetail /></ProtectedRoute>} />
              <Route path="/sessions/:id" element={<ProtectedRoute><InterviewSession /></ProtectedRoute>} />
              <Route path="/sessions/:id/results" element={<ProtectedRoute><SessionResults /></ProtectedRoute>} />
            </Routes>
          </main>
        </div>

        <style>{`
          .app-container {
            display: flex;
            flex-direction: column;
            min-height: 100vh;
          }
          .content {
            flex: 1;
            padding: 2rem;
            max-width: 1200px;
            margin: 0 auto;
            width: 100%;
          }
        `}</style>
      </AuthProvider>
    </Router>
  );
}

export default App;
