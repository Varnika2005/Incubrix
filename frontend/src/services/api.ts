import { JobResponse, SystemCapabilities, EditPlan, EditReceipt } from '../types';

const API_BASE = 'http://127.0.0.1:8000/api';

export const api = {
  async getHealth(): Promise<{ status: string; service: string; version: string }> {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error('Health check failed');
    return res.json();
  },

  async getCapabilities(): Promise<SystemCapabilities> {
    const res = await fetch(`${API_BASE}/capabilities`);
    if (!res.ok) throw new Error('Failed to fetch capabilities');
    return res.json();
  },

  async uploadVideo(file: File): Promise<JobResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/jobs/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
  },

  async createDemoJob(): Promise<JobResponse> {
    const res = await fetch(`${API_BASE}/jobs/demo`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to start demo job' }));
      throw new Error(err.detail || 'Failed to start demo job');
    }
    return res.json();
  },

  async analyzePrompt(jobId: string, prompt: string): Promise<JobResponse> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Prompt analysis failed' }));
      throw new Error(err.detail || 'Prompt analysis failed');
    }
    return res.json();
  },

  async processJob(jobId: string, approvedPlan: EditPlan): Promise<JobResponse> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved_plan: approvedPlan }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Processing initiation failed' }));
      throw new Error(err.detail || 'Processing initiation failed');
    }
    return res.json();
  },

  async getJob(jobId: string): Promise<JobResponse> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`);
    if (!res.ok) throw new Error('Failed to fetch job');
    return res.json();
  },

  async listJobs(): Promise<JobResponse[]> {
    const res = await fetch(`${API_BASE}/jobs`);
    if (!res.ok) throw new Error('Failed to fetch job history');
    return res.json();
  },

  async getReceipt(jobId: string): Promise<EditReceipt> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/receipt`);
    if (!res.ok) throw new Error('Failed to fetch receipt');
    return res.json();
  },

  async deleteJob(jobId: string): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete job');
    return res.json();
  },

  getOriginalPreviewUrl(jobId: string): string {
    return `${API_BASE}/jobs/${jobId}/preview/original`;
  },

  getOutputPreviewUrl(jobId: string): string {
    return `${API_BASE}/jobs/${jobId}/preview/output?t=${Date.now()}`;
  },

  getDownloadUrl(jobId: string): string {
    return `${API_BASE}/jobs/${jobId}/download`;
  },
};
