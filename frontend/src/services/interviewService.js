import api from './api';

export const interviewService = {
  createInterview: async (interviewData) => {
    const response = await api.post('/interviews', interviewData);
    return response.data;
  },
  getInterview: async (id) => {
    const response = await api.get(`/interviews/${id}`);
    return response.data;
  },
  listQuestions: async (interviewId, query = '', k = 10) => {
    const response = await api.get(`/interviews/${interviewId}/questions`, {
      params: { query, k },
    });
    return response.data;
  },
  deleteQuestion: async (interviewId, questionId) => {
    const response = await api.delete(`/interviews/${interviewId}/questions/${questionId}`);
    return response.data;
  },
  resetQuestions: async (interviewId) => {
    const response = await api.post(`/interviews/${interviewId}/reset-questions`);
    return response.data;
  },
  ingestQuestions: async (formData) => {
    const response = await api.post('/questions', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  deleteInterview: async (id) => {
    const response = await api.delete(`/interviews/${id}`);
    return response.data;
  }
};
