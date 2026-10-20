import {
  JobResponse,
  SystemCapabilities,
  EditPlan,
  EditReceipt,
  User,
  AuthResponse,
  IntegrityVerificationResponse,
  InstructionOutcome,
  UndoRedoResponse,
  HistoryStackResponse,
  TimelineMapRequest,
  TimelineMapResponse
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

let currentToken: string | null = localStorage.getItem('clippilot_token');

export const setStoredAuthToken = (token: string | null) => {
  currentToken = token;
  if (token) {
    localStorage.setItem('clippilot_token', token);
  } else {
    localStorage.removeItem('clippilot_token');
  }
};

export const getStoredAuthToken = (): string | null => {
  return currentToken;
};

const getHeaders = (extraHeaders: Record<string, string> = {}): Record<string, string> => {
  const headers: Record<string, string> = { ...extraHeaders };
  if (currentToken) {
    headers['Authorization'] = `Bearer ${currentToken}`;
  }
  return headers;
};

export const api = {
  // Authentication Endpoints
  async signup(payload: {
    full_name: string;
    email: string;
    password: string;
    confirm_password: string;
  }): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE}/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
      throw new Error(err.detail || 'Registration failed');
    }
    const data: AuthResponse = await res.json();
    setStoredAuthToken(data.access_token);
    return data;
  },

  async login(payload: {
    email: string;
    password: string;
    remember_me?: boolean;
  }): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Invalid email or password' }));
      throw new Error(err.detail || 'Invalid email or password');
    }
    const data: AuthResponse = await res.json();
    setStoredAuthToken(data.access_token);
    return data;
  },

  async getMe(): Promise<User> {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: getHeaders(),
      credentials: 'include',
    });
    if (!res.ok) throw new Error('Failed to retrieve user session');
    return res.json();
  },

  async logout(): Promise<void> {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: getHeaders(),
        credentials: 'include',
      });
    } finally {
      setStoredAuthToken(null);
    }
  },

  // Health and System Diagnostics
  async getHealth(): Promise<{ status: string; service: string; version: string }> {
    const res = await fetch(`${API_BASE}/health`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Health check failed');
    return res.json();
  },

  async getCapabilities(): Promise<SystemCapabilities> {
    const res = await fetch(`${API_BASE}/capabilities`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch capabilities');
    return res.json();
  },

  // Video and Job Operations
  async uploadVideo(file: File): Promise<JobResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/jobs/upload`, {
      method: 'POST',
      headers: getHeaders(),
      credentials: 'include',
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
      headers: getHeaders(),
      credentials: 'include',
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
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      credentials: 'include',
      body: JSON.stringify({ prompt }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Prompt analysis failed' }));
      throw new Error(err.detail || 'Prompt analysis failed');
    }
    return res.json();
  },

  async processInstruction(
    jobId: string,
    instruction: string,
    parameters?: Record<string, any>,
    simulateFailure?: boolean,
    timeReference?: string
  ): Promise<InstructionOutcome> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/instruction`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      credentials: 'include',
      body: JSON.stringify({
        instruction,
        parameters,
        simulate_failure: simulateFailure ?? false,
        time_reference: timeReference,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to process instruction' }));
      throw new Error(err.detail || 'Failed to process instruction');
    }
    return res.json();
  },

  async processJob(jobId: string, approvedPlan: EditPlan): Promise<JobResponse> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/process`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      credentials: 'include',
      body: JSON.stringify({ approved_plan: approvedPlan }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Processing initiation failed' }));
      throw new Error(err.detail || 'Processing initiation failed');
    }
    return res.json();
  },

  async getJob(jobId: string): Promise<JobResponse> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`, {
      headers: getHeaders(),
      credentials: 'include',
    });
    if (!res.ok) throw new Error('Failed to fetch job');
    return res.json();
  },

  async listJobs(): Promise<JobResponse[]> {
    const res = await fetch(`${API_BASE}/jobs`, {
      headers: getHeaders(),
      credentials: 'include',
    });
    if (!res.ok) throw new Error('Failed to fetch job history');
    return res.json();
  },

  async getReceipt(jobId: string): Promise<EditReceipt> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/receipt`, {
      headers: getHeaders(),
      credentials: 'include',
    });
    if (!res.ok) throw new Error('Failed to fetch receipt');
    return res.json();
  },

  async deleteJob(jobId: string): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`, {
      method: 'DELETE',
      headers: getHeaders(),
      credentials: 'include',
    });
    if (!res.ok) throw new Error('Failed to delete job');
    return res.json();
  },

  async verifyIntegrity(jobId: string): Promise<IntegrityVerificationResponse> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/verify-integrity`, {
      headers: getHeaders(),
      credentials: 'include',
    });
    if (!res.ok) throw new Error('Failed to verify source media integrity');
    return res.json();
  },

  async saveHistory(jobId: string, history: any[], currentPlan?: EditPlan): Promise<JobResponse> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/history`, {
      method: 'POST',
      headers: getHeaders(),
      credentials: 'include',
      body: JSON.stringify({ history, current_plan: currentPlan }),
    });
    if (!res.ok) throw new Error('Failed to save project edit history');
    return res.json();
  },

  async getTimeline(jobId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/timeline`, {
      headers: getHeaders(),
      credentials: 'include',
    });
    if (!res.ok) throw new Error('Failed to retrieve timeline data');
    return res.json();
  },

  async addTimelineEffect(
    jobId: string,
    payload: {
      type: string;
      source_start: number;
      source_end: number;
      parameters?: Record<string, any>;
      label?: string;
    }
  ): Promise<any> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/timeline/effects`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      credentials: 'include',
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to add content-aware effect to timeline');
    return res.json();
  },

  async transformTimeline(
    jobId: string,
    payload: {
      action: string;
      [key: string]: any;
    }
  ): Promise<any> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/timeline/transform`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      credentials: 'include',
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to apply timeline transformation');
    return res.json();
  },

  async mapTimelineCoordinates(
    jobId: string,
    payload: TimelineMapRequest
  ): Promise<TimelineMapResponse> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/timeline/map`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      credentials: 'include',
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to map timeline coordinates');
    return res.json();
  },

  getOriginalPreviewUrl(jobId: string): string {
    return `${API_BASE}/jobs/${jobId}/preview/original`;
  },

  getOutputPreviewUrl(jobId: string): string {
    return `${API_BASE}/jobs/${jobId}/preview/output?t=${Date.now()}`;
  },

  getDownloadUrl(jobId: string, filename: string = 'ClipPilot_Edited_Video.mp4'): string {
    const token = getStoredAuthToken();
    const params = new URLSearchParams();
    if (filename) params.set('filename', filename);
    if (token) params.set('token', token);
    const query = params.toString() ? `?${params.toString()}` : '';
    return `${API_BASE}/jobs/${jobId}/download${query}`;
  },

  downloadVideo(jobId: string, customFilename?: string): void {
    const finalName = customFilename
      ? (customFilename.toLowerCase().endsWith('.mp4') ? customFilename : `${customFilename}.mp4`)
      : 'ClipPilot_Edited_Video.mp4';
    const downloadUrl = this.getDownloadUrl(jobId, finalName);

    const downloadAnchor = document.createElement('a');
    downloadAnchor.href = downloadUrl;
    downloadAnchor.setAttribute('download', finalName);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  },

  async undo(jobId: string): Promise<UndoRedoResponse> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/undo`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      credentials: 'include',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to undo edit' }));
      throw new Error(err.detail || 'Failed to undo edit');
    }
    return res.json();
  },

  async redo(jobId: string): Promise<UndoRedoResponse> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/redo`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      credentials: 'include',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to redo edit' }));
      throw new Error(err.detail || 'Failed to redo edit');
    }
    return res.json();
  },

  async getHistory(jobId: string): Promise<HistoryStackResponse> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/history`, {
      headers: getHeaders(),
      credentials: 'include',
    });
    if (!res.ok) throw new Error('Failed to fetch history stack');
    return res.json();
  },
};

