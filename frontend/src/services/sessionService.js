import api from './api';

export const sessionService = {
  startSession: async (userId, interviewId) => {
    const response = await api.post('/sessions', { user_id: userId, interview_id: interviewId });
    return response.data;
  },
  getSession: async (sessionId) => {
    const response = await api.get(`/sessions/${sessionId}`);
    return response.data;
  },
  getUserSessions: async (userId) => {
    const response = await api.get('/sessions', { params: { user_id: userId } });
    return response.data;
  },
  getNextQuestion: async (sessionId, tts = false) => {
    const response = await api.get(`/sessions/${sessionId}/next-question`, {
      params: { tts },
    });
    return response.data;
  },
  submitAnswer: async (sessionId, formData) => {
    const response = await api.post(`/sessions/${sessionId}/answers`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  listAnswers: async (sessionId) => {
    const response = await api.get(`/sessions/${sessionId}/answers`);
    return response.data;
  },
  endSession: async (sessionId) => {
    const response = await api.post(`/sessions/${sessionId}/end`);
    return response.data;
  },
};
