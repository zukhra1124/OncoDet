// API service — all backend calls go through here

import axios from 'axios';

// use the env variable in production, otherwise proxy through vite
const API_BASE = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
    baseURL: API_BASE,
    timeout: 120000, // 2 min — model inference can be slow
});

// upload an X-ray and get prediction + Grad-CAM back
export const predictImage = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/predict', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
};

// just upload without running inference
export const uploadImage = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
};

// get Grad-CAM visualisation for an image
export const generateGradCAM = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/gradcam', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
};

// run federated learning simulation
export const runFederatedTraining = async (numClients = 4, numRounds = 5) => {
    const response = await api.post('/federated-train', {
        num_clients: numClients,
        num_rounds: numRounds,
    });
    return response.data;
};

// grab model performance stats for the dashboard
export const getModelStats = async () => {
    const response = await api.get('/model-stats');
    return response.data;
};

// quick check if the backend is alive
export const healthCheck = async () => {
    const response = await api.get('/health');
    return response.data;
};

export default api;
