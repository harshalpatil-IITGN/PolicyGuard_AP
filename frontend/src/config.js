// Centralized API configuration for local dev and production deployment
// In local dev: defaults to '/api' (proxied by Vite to http://localhost:8000)
// In production (Vercel): can be set via VITE_API_URL environment variable, or defaults to '/api'
export const API = import.meta.env.VITE_API_URL || '/api';
