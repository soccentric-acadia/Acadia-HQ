import type {
  Alarm,
  AlarmRule,
  AuditLogListResponse,
  Backup,
  BackupListResponse,
  CommandStatus,
  Device,
  DeviceAlarm,
  DeviceAlarmListResponse,
  DeviceCreateResponse,
  DeviceHealth,
  DeviceListResponse,
  FaultListResponse,
  LogBundleListResponse,
  DeviceUserCommand,
  Rollout,
  RolloutRequest,
  UpdateArtifact,
  Operation,
  QueuedCommand,
  ServiceAction,
  User,
  UserRole,
} from './types'

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail ?? detail
    } catch {
      // response had no JSON body -- fall back to statusText
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

function post(path: string, body?: unknown): Promise<QueuedCommand> {
  return request<QueuedCommand>(path, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

export const api = {
  auth: {
    loginUrl: () => request<{ authorization_url: string }>('/auth/login'),
    callback: (code: string, state: string) =>
      request<{ ok: boolean }>(
        `/auth/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`,
        {
          method: 'POST',
        },
      ),
    logout: () => request<{ ok: boolean }>('/auth/logout', { method: 'POST' }),
    me: () => request<User>('/auth/me'),
  },
  devices: {
    list: (params: { q?: string; limit?: number; offset?: number } = {}) => {
      const qs = new URLSearchParams()
      if (params.q) qs.set('q', params.q)
      if (params.limit) qs.set('limit', String(params.limit))
      if (params.offset) qs.set('offset', String(params.offset))
      const suffix = qs.toString() ? `?${qs}` : ''
      return request<DeviceListResponse>(`/devices${suffix}`)
    },
    get: (id: string) => request<Device>(`/devices/${id}`),
    create: (name: string) =>
      request<DeviceCreateResponse>('/devices', { method: 'POST', body: JSON.stringify({ name }) }),
    telemetry: (id: string) =>
      request<Record<string, { recorded_at: string; value: number }[]>>(`/devices/${id}/telemetry`),
    // The factory-reset producer lives under /updates (task 009, H10); the
    // old /factory-reset path never existed.
    factoryReset: (id: string) =>
      request<QueuedCommand>(`/devices/${id}/updates/factory-reset`, { method: 'POST' }),
    // "Disable" = revoke the device credential: HQ refuses the device from
    // then on (there is no separate /disable endpoint).
    disable: (id: string) =>
      request<{ ok: boolean }>(`/devices/${id}/credential/revoke`, { method: 'POST' }),
    health: (id: string) => request<DeviceHealth>(`/devices/${id}/health`),
    commandStatus: (id: string, commandId: string) =>
      request<CommandStatus>(`/devices/${id}/commands/${encodeURIComponent(commandId)}`),
  },
  operations: {
    list: () => request<{ items: Operation[] }>('/operations'),
  },
  // T-P21: OTA artifact store + staged rollouts + device tags.
  fleetUpdates: {
    artifacts: () => request<{ items: UpdateArtifact[] }>('/updates/artifacts'),
    createArtifact: (body: { version: string; target_board_rev: string; checksum_sha256: string }) =>
      request<UpdateArtifact>('/updates/artifacts', { method: 'POST', body: JSON.stringify(body) }),
    // Raw body upload: HQ hashes the stream and refuses a SHA-256 mismatch.
    uploadContent: (id: string, file: Blob) =>
      request<UpdateArtifact>(`/updates/artifacts/${id}/content`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/octet-stream' },
        body: file,
      }),
    rollouts: () => request<{ items: Rollout[] }>('/updates/rollouts'),
    createRollout: (body: RolloutRequest) =>
      request<Rollout>('/updates/rollouts', { method: 'POST', body: JSON.stringify(body) }),
    drive: (id: string, action: 'start' | 'halt' | 'resume') =>
      request<Rollout>(`/updates/rollouts/${id}/${action}`, { method: 'POST' }),
    setTags: (deviceId: string, tags: string[]) =>
      request<{ tags: string[] }>(`/devices/${deviceId}/tags`, {
        method: 'PUT',
        body: JSON.stringify({ tags }),
      }),
  },
  // T-P20: device command producers. Each returns the queued command; the
  // device-reported result arrives via devices.commandStatus polling.
  commands: {
    reboot: (id: string) => post(`/devices/${id}/power/reboot`),
    shutdown: (id: string, confirmation: string) =>
      post(`/devices/${id}/power/shutdown`, { confirmation }),
    rebootToApply: (id: string) => post(`/devices/${id}/updates/reboot-to-apply`),
    confirmUpdate: (id: string) => post(`/devices/${id}/updates/confirm`),
    rollbackUpdate: (id: string, confirmation: string) =>
      post(`/devices/${id}/updates/rollback`, { confirmation }),
    serviceControl: (id: string, unit: string, action: ServiceAction) =>
      post(`/devices/${id}/services/control`, { unit, action }),
    requestLogBundle: (id: string) => post(`/devices/${id}/logs/request`),
    users: (id: string, body: DeviceUserCommand) => post(`/devices/${id}/users/command`, body),
    runOperation: (id: string, daemon: string, operation: string, args = {}) =>
      post(`/devices/${id}/operations`, { daemon, operation, args }),
  },
  configuration: {
    // Both endpoints return HTTP 202 with the queued command envelope; the
    // device-reported result arrives via commandStatus polling.
    read: (id: string) =>
      request<{
        status: string
        integration_status: string
        command_id: string
        correlation_id: string
      }>(`/devices/${id}/configuration`, { method: 'GET' }),
    write: (id: string, values: Record<string, unknown>) =>
      request<{
        status: string
        integration_status: string
        command_id: string
        correlation_id: string
      }>(`/devices/${id}/configuration`, {
        method: 'PUT',
        body: JSON.stringify({ values }),
      }),
  },
  faults: {
    list: (deviceId: string) => request<FaultListResponse>(`/devices/${deviceId}/faults`),
  },
  alarms: {
    listForDevice: (deviceId: string) =>
      request<DeviceAlarmListResponse>(`/devices/${deviceId}/alarms`),
    acknowledge: (id: string) => request<Alarm>(`/alarms/${id}/acknowledge`, { method: 'POST' }),
    resolve: (id: string) => request<Alarm>(`/alarms/${id}/resolve`, { method: 'POST' }),
    clear: (deviceId: string, alarmId: string) =>
      request<DeviceAlarm>(`/devices/${deviceId}/alarms/${alarmId}/clear`, { method: 'POST' }),
  },
  alarmRules: {
    list: () => request<AlarmRule[]>('/alarm-rules'),
    create: (name: string, condition: Record<string, unknown>) =>
      request<AlarmRule>('/alarm-rules', {
        method: 'POST',
        body: JSON.stringify({ name, condition }),
      }),
  },
  logs: {
    list: (deviceId: string) => request<LogBundleListResponse>(`/devices/${deviceId}/logs`),
    downloadUrl: (deviceId: string, bundleId: string) =>
      request<{ download_url: string }>(`/devices/${deviceId}/logs/${bundleId}/download`),
  },
  backups: {
    list: (deviceId: string) => request<BackupListResponse>(`/devices/${deviceId}/backups`),
    takeNow: (deviceId: string) =>
      request<Backup>(`/devices/${deviceId}/backups`, { method: 'POST' }),
    restore: (deviceId: string, backupId: string) =>
      request<{ ok: boolean }>(`/devices/${deviceId}/backups/${backupId}/restore`, {
        method: 'POST',
      }),
  },
  users: {
    list: () => request<User[]>('/users'),
    invite: (email: string, role: UserRole) =>
      request<User>('/users/invite', { method: 'POST', body: JSON.stringify({ email, role }) }),
  },
  auditLog: {
    list: (params: { limit?: number; offset?: number } = {}) => {
      const qs = new URLSearchParams()
      if (params.limit) qs.set('limit', String(params.limit))
      if (params.offset) qs.set('offset', String(params.offset))
      const suffix = qs.toString() ? `?${qs}` : ''
      return request<AuditLogListResponse>(`/audit-log${suffix}`)
    },
  },
}
