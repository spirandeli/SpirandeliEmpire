/**
 * SpirandeliEmpire OS 3.2 — Frontend API & WebSocket Service (Multi-User + BYOK + Model Manager)
 */

const API_BASE = '/api/v1';
const TOKEN_KEY = 'spirandeli_access_token';

export function getAuthToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY);
}

export function setAuthToken(token: string | null, remember = true) {
  sessionStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(TOKEN_KEY);
  if (token) {
    if (remember) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      sessionStorage.setItem(TOKEN_KEY, token);
    }
  }
}

export async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const token = getAuthToken();
  const res = await fetch(`${API_BASE}${url}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
    ...options,
  });
  if (res.status === 401 && !url.startsWith('/auth/')) {
    setAuthToken(null);
    window.dispatchEvent(new Event('spirandeli:unauthorized'));
  }
  if (!res.ok) {
    let msg = `Erro ${res.status}`;
    try {
      const rawText = await res.text();
      try {
        const data = JSON.parse(rawText);
        msg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail || data);
      } catch {
        if (res.status === 504) {
          msg = 'O servidor demorou para responder (Gateway Timeout). A operação continua em segundo plano.';
        } else if (rawText && rawText.length < 500 && !rawText.trim().startsWith('<')) {
          msg = rawText;
        } else {
          msg = `Erro HTTP ${res.status}`;
        }
      }
    } catch {
      msg = `Falha na comunicação com o servidor (${res.status})`;
    }
    throw new Error(msg);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json();
}

export const api = {
  // Auth
  login: (identifier: string, password: string, remember_me = true) =>
    fetchJson<{ access_token: string; refresh_token: string; must_change_password: boolean; user: any }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: identifier, password, remember_me }),
    }),
  register: (data: { full_name: string; email: string; password: string; confirm_password: string; accept_terms: boolean; invite_code?: string }) =>
    fetchJson<any>('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  logout: () => fetchJson<any>('/auth/logout', { method: 'POST' }),
  forgotPassword: (email: string) =>
    fetchJson<any>('/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) }),
  resetPassword: (data: { token: string; new_password: string; confirm_password: string }) =>
    fetchJson<any>('/auth/reset-password', { method: 'POST', body: JSON.stringify(data) }),
  getMe: () => fetchJson<any>('/auth/me'),

  // Profile, Sessions & Admin
  getProfile: () => fetchJson<any>('/users/me'),
  updateProfile: (full_name: string) =>
    fetchJson<any>('/users/me', { method: 'PATCH', body: JSON.stringify({ full_name }) }),
  changePassword: async (data: { current_password: string; new_password: string; confirm_password: string }) => {
    const res = await fetchJson<any>('/users/me/password', { method: 'PATCH', body: JSON.stringify(data) });
    if (res?.access_token) setAuthToken(res.access_token);
    return res;
  },
  getSessions: () => fetchJson<any[]>('/users/me/sessions'),
  revokeSession: (id: string) => fetchJson<any>(`/users/me/sessions/${id}`, { method: 'DELETE' }),
  adminListUsers: () => fetchJson<any[]>('/users/admin/users'),
  adminUpdateUser: (id: string, data: { is_active?: boolean; role?: string }) =>
    fetchJson<any>(`/users/admin/users/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  adminGetPolicies: () => fetchJson<{ registration_mode: string }>('/users/admin/policies'),
  adminUpdatePolicies: (mode: string) =>
    fetchJson<any>('/users/admin/policies', { method: 'PATCH', body: JSON.stringify({ mode }) }),
  adminCreateInvite: () => fetchJson<{ invite_code: string }>('/users/admin/invites', { method: 'POST' }),

  // AI Providers (BYOK)
  getProvidersOverview: () => fetchJson<any[]>('/ai-providers/'),
  listConnections: (provider?: string) =>
    fetchJson<any[]>(`/ai-providers/connections${provider ? `?provider=${provider}` : ''}`),
  createConnection: (data: { provider: string; label: string; api_key: string; workspace_org?: string; is_default?: boolean }) =>
    fetchJson<any>('/ai-providers/connections', { method: 'POST', body: JSON.stringify(data) }),
  updateConnection: (id: string, data: any) =>
    fetchJson<any>(`/ai-providers/connections/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  testConnection: (id: string) =>
    fetchJson<any>(`/ai-providers/connections/${id}/test`, { method: 'POST' }),
  revokeConnection: (id: string) =>
    fetchJson<any>(`/ai-providers/connections/${id}/revoke`, { method: 'POST' }),
  deleteConnection: (id: string) =>
    fetchJson<void>(`/ai-providers/connections/${id}`, { method: 'DELETE' }),

  // AI Models Discovery
  listModels: (params?: { provider?: string; credential_id?: string; capability?: string; search?: string }) => {
    const q = new URLSearchParams();
    if (params?.provider) q.set('provider', params.provider);
    if (params?.credential_id) q.set('credential_id', params.credential_id);
    if (params?.capability) q.set('capability', params.capability);
    if (params?.search) q.set('search', params.search);
    return fetchJson<any[]>(`/ai-models/?${q.toString()}`);
  },
  syncCredentialModels: (credentialId: string, force = true) =>
    fetchJson<any>(`/ai-models/sync/${credentialId}?force=${force}`, { method: 'POST' }),

  // AI Model Manager & Usage
  getGlobalAISettings: () => fetchJson<any>('/ai-settings/'),
  updateGlobalAISettings: (data: any) =>
    fetchJson<any>('/ai-settings/', { method: 'PATCH', body: JSON.stringify(data) }),
  listAgentModelConfigs: () => fetchJson<any[]>('/ai-settings/agents'),
  updateAgentModelConfig: (agentId: string, data: any) =>
    fetchJson<any>(`/ai-settings/agents/${agentId}`, { method: 'PATCH', body: JSON.stringify(data) }),
  listTaskProfiles: () => fetchJson<any[]>('/ai-settings/task-profiles'),
  updateTaskProfile: (profileKey: string, data: any) =>
    fetchJson<any>(`/ai-settings/task-profiles/${profileKey}`, { method: 'PATCH', body: JSON.stringify(data) }),
  getFallbackSettings: () => fetchJson<any>('/ai-settings/fallback'),
  updateFallbackSettings: (data: { fallback_enabled: boolean; fallback_chain: any[] }) =>
    fetchJson<any>('/ai-settings/fallback', { method: 'PATCH', body: JSON.stringify(data) }),
  getUsageSummary: () => fetchJson<any>('/ai-usage/'),
  getUsageByAgent: () => fetchJson<any[]>('/ai-usage/agents'),
  getUsageByModel: () => fetchJson<any[]>('/ai-usage/models'),
  getUsageByProvider: () => fetchJson<any[]>('/ai-usage/providers'),

  // Agents
  getAgents: () => fetchJson<any[]>('/agents/'),
  getAgent: (id: string) => fetchJson<any>(`/agents/${id}`),
  updateAgentState: (id: string, state: string) =>
    fetchJson<any>(`/agents/${id}/state`, {
      method: 'PATCH',
      body: JSON.stringify({ operational_state: state }),
    }),

  // Projects
  getProjects: () => fetchJson<any[]>('/projects/'),
  getProject: (id: string) => fetchJson<any>(`/projects/${id}`),
  createProject: (data: any) =>
    fetchJson<any>('/projects/', { method: 'POST', body: JSON.stringify(data) }),
  updateProject: (id: string, data: any) =>
    fetchJson<any>(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteProject: (id: string) =>
    fetchJson<void>(`/projects/${id}`, { method: 'DELETE' }),
  createDigitalBusiness: (data: any) =>
    fetchJson<any>('/projects/digital-business', { method: 'POST', body: JSON.stringify(data) }),

  // Tasks
  getTasks: (params?: { project_id?: string; agent_id?: string; workflow_id?: string; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.project_id) q.set('project_id', params.project_id);
    if (params?.agent_id) q.set('agent_id', params.agent_id);
    if (params?.workflow_id) q.set('workflow_id', params.workflow_id);
    if (params?.status) q.set('status', params.status);
    return fetchJson<any[]>(`/tasks/?${q.toString()}`);
  },
  getTask: (id: string) => fetchJson<any>(`/tasks/${id}`),
  createTask: (data: { title: string; description?: string; assigned_agent_id?: string; project_id?: string; priority?: string }) =>
    fetchJson<any>('/tasks/', { method: 'POST', body: JSON.stringify(data) }),
  updateTaskStatus: (id: string, status: string, result_summary?: string) =>
    fetchJson<any>(`/tasks/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status, result_summary }) }),
  deleteTask: (id: string) =>
    fetchJson<void>(`/tasks/${id}`, { method: 'DELETE' }),

  // Workflows
  getWorkflows: () => fetchJson<any[]>('/workflows/'),
  getWorkflow: (id: string) => fetchJson<any>(`/workflows/${id}`),
  startWorkflow: (data: { user_request: string; workflow_type?: string; project_id?: string }) =>
    fetchJson<any>('/workflows/start', { method: 'POST', body: JSON.stringify(data) }),
  resumeWorkflow: (id: string, approved: boolean, feedback?: string) =>
    fetchJson<any>(`/workflows/${id}/resume`, { method: 'POST', body: JSON.stringify({ approved, feedback }) }),
  cancelWorkflow: (id: string) =>
    fetchJson<any>(`/workflows/${id}/cancel`, { method: 'POST' }),

  // Artifacts
  getArtifacts: (projectId?: string) =>
    fetchJson<any[]>(`/artifacts/${projectId ? `?project_id=${projectId}` : ''}`),
  getArtifact: (id: string) => fetchJson<any>(`/artifacts/${id}`),

  // Approvals
  getApprovals: (status?: string) =>
    fetchJson<any[]>(`/approvals/${status ? `?status=${status}` : ''}`),
  decideApproval: (id: string, approved: boolean, feedback?: string) =>
    fetchJson<any>(`/approvals/${id}/decide`, { method: 'POST', body: JSON.stringify({ approved, feedback }) }),

  // Legacy Integrations
  getIntegrations: () => fetchJson<any[]>('/integrations/'),
  saveIntegrationCredentials: (id: string, credentials: string) =>
    fetchJson<any>(`/integrations/${id}/credentials`, { method: 'POST', body: JSON.stringify({ credentials }) }),
  testIntegration: (id: string) => fetchJson<any>(`/integrations/${id}/test`, { method: 'POST' }),

  // System
  getSystemMetrics: () => fetchJson<any>('/system/metrics'),

  // Chat
  getChatHistory: (projectId?: string) =>
    fetchJson<any[]>(`/chat/history${projectId ? `?project_id=${projectId}` : ''}`),
  sendChatMessage: (message: string, projectId?: string) =>
    fetchJson<any>('/chat/message', { method: 'POST', body: JSON.stringify({ message, project_id: projectId }) }),
};

// WebSocket Hub
export class LiveEventsSocket {
  private ws: WebSocket | null = null;
  private listeners: ((event: any) => void)[] = [];

  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const token = getAuthToken();
    const wsUrl = `${protocol}//${host}/api/v1/events${token ? `?token=${encodeURIComponent(token)}` : ''}`;

    try {
      this.ws = new WebSocket(wsUrl);
      this.ws.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data);
          this.listeners.forEach((fn) => fn(data));
        } catch {
          // ignore
        }
      };
      this.ws.onclose = () => {
        setTimeout(() => this.connect(), 3000);
      };
    } catch (e) {
      console.warn('WebSocket connection not available yet, will retry.', e);
    }
  }

  subscribe(listener: (event: any) => void) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }
}

export const liveEvents = new LiveEventsSocket();
