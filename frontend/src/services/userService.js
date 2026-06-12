import api from './api';

export const userService = {
  getUser: async (userId) => {
    const response = await api.get(`/users/${userId}`);
    return response.data;
  },
  listUserInterviews: async (userId) => {
    const response = await api.get(`/users/${userId}/interviews`);
    return response.data;
  },
};
