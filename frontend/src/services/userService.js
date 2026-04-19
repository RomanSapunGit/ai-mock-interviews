import api from './api';

export const userService = {
  createUser: async (email) => {
    const response = await api.post('/users', { email });
    return response.data;
  },
  getUser: async (userId) => {
    const response = await api.get(`/users/${userId}`);
    return response.data;
  },
  listUserInterviews: async (userId) => {
    const response = await api.get(`/users/${userId}/interviews`);
    return response.data;
  },
};
