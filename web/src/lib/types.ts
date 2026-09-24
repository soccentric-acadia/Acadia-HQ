export type UserRole = 'viewer' | 'operator' | 'admin'
export type PairingState = 'pending' | 'authorized' | 'disabled' | 'revoked'

export interface Page {
  total: number
  limit: number
  offset: number
}

export interface User {
  id: string
  email: string
  role: UserRole
  created_at: string
}

export interface Device {
  id: string
  name: string
  pairing_state: PairingState
  online: boolean
  last_seen_at: string | null
  serial: string | null
  board_rev: string | null
  tags?: string[]
  // T-P24: last heartbeat snapshot
  status?: DeviceStatusSnapshot
  status_updated_at?: string | null
  image_version?: string | null
  running_slot?: string | null
  health_score?: number | null
  created_at: string
}

export interface DeviceListResponse {
  items: Device[]
  page: Page
}

export interface DeviceCreateResponse {
  device: Device
  pairing_token: string | null
}

export interface AuditLogEntry {
  id: string
  actor_user_id: string | null
  action: string
  target_device_id: string | null
  payload: Record<string, unknown>
  created_at: string
}

export interface AuditLogListResponse {
  items: AuditLogEntry[]
  page: Page
}

export type FaultSeverity = 'info' | 'warn' | 'critical'

export interface Fault {
  id: string
  device_id: string
  code: string
  severity: FaultSeverity
  message: string
  raised_at: string
  cleared_at: string | null
}

export interface FaultListResponse {
  items: Fault[]
  page: Page
}

export type AlarmState = 'active' | 'acknowledged' | 'resolved'

export interface Alarm {
  id: string
  alarm_rule_id: string
  device_id: string
  state: AlarmState
  triggered_at: string
  acknowledged_at: string | null
  resolved_at: string | null
}

export interface AlarmListResponse {
  items: Alarm[]
  page: Page
}

// Device-reported 4-byte alarm from the `alarms` table (GET /devices/{id}/alarms).
// `alarm_code` is the packed big-endian uint32 (byte0=major_id, byte1=sub_section,
// byte2=fault_type, byte3=severity), e.g. 0x01020304 -> (1, 2, 3, 4).
export interface DeviceAlarm {
  id: string
  device_id: string
  major_id: number
  sub_section: number
  fault_type: number
  severity: number
  alarm_code: number
  state: AlarmState
  triggered_at: string
  resolved_at: string | null
}

export interface DeviceAlarmListResponse {
  items: DeviceAlarm[]
  page: Page
}

export interface AlarmRule {
  id: string
  name: string
  condition: Record<string, unknown>
  notify_channels: Record<string, unknown>
  enabled: boolean
}

export interface LogBundle {
  id: string
  device_id: string
  size_bytes: number
  uploaded_at: string
  time_range_start: string
  time_range_end: string
  /** T-P22: pending until the device reports the upload and HQ verified it. */
  upload_state: 'pending' | 'complete' | 'failed' | 'unverified'
  sha256?: string | null
  upload_error?: string | null
}

export interface LogBundleListResponse {
  items: LogBundle[]
  page: Page
}

export interface Backup {
  id: string
  device_id: string
  size_bytes: number
  created_at: string
  restored_at: string | null
  /** T-P22: pending until the device reports the upload and HQ verified it. */
  upload_state: 'pending' | 'complete' | 'failed' | 'unverified'
  sha256?: string | null
  upload_error?: string | null
}

export interface BackupListResponse {
  items: Backup[]
  page: Page
}

export interface DeviceHealthFactor {
  name: string
  status: string
  penalty: number
  count?: number
}

export interface DeviceHealth {
  device_id: string
  score: number
  status: 'healthy' | 'degraded' | 'offline'
  online: boolean
  last_seen_at: string | null
  factors: DeviceHealthFactor[]
}

export type CommandState = 'queued' | 'delivered' | 'succeeded' | 'failed' | 'expired'

export interface CommandStatus {
  command_id: string
  state: CommandState
  attempt_count: number
  correlation_id: string
  code: string | null
  error: string | null
  payload: Record<string, unknown> | null
  completed_at: string | null
  expires_at: string | null
  retryable: boolean | null
  integration_status?: string
}

export interface Operation {
  name: string
  daemon: string
  command_kind: string
  description: string
  integration_status?: string
}

/** A durable device command HQ queued (T-P20 producers). */
export interface QueuedCommand {
  status?: string
  ok?: boolean
  command_id: string
  correlation_id?: string
}

export type ServiceAction = 'start' | 'stop' | 'restart' | 'enable' | 'disable'

export type DeviceUserOperation = 'users.list' | 'users.create' | 'users.delete' | 'users.set_role'

export interface DeviceUserCommand {
  operation: DeviceUserOperation
  username?: string
  role?: 'admin' | 'operator' | 'viewer'
  password?: string
}

export interface DeviceUserRow {
  username: string
  role: string
  groups: string[]
}

/** T-P21: an OTA artifact in the HQ store. */
export interface UpdateArtifact {
  id: string
  version: string
  target_board_rev: string
  checksum_sha256: string
  size_bytes: number | null
  uploaded_at: string | null
  created_at: string
}

export type RolloutStatus = 'pending' | 'in_progress' | 'halted' | 'completed' | 'failed'

export interface RolloutDevice {
  device_id: string
  wave: number
  status: 'pending' | 'applying' | 'succeeded' | 'failed'
  error: string | null
  applied_at: string | null
  command_id: string | null
}

export interface Rollout {
  id: string
  artifact_id: string
  artifact_version: string | null
  target: 'all' | 'specific_devices' | 'device_group'
  target_selector: Record<string, unknown>
  status: RolloutStatus
  policy: { canary_percent: number; halt_failure_percent: number; auto_activate: boolean }
  halted_reason: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  summary: Record<string, number>
  devices: RolloutDevice[]
}

export interface RolloutRequest {
  artifact_id: string
  target: Rollout['target']
  device_ids?: string[]
  tag?: string
  canary_percent?: number
  halt_failure_percent?: number
  auto_activate?: boolean
}

/** T-P24: DeviceStatus from the device heartbeat (proto field names). */
export interface DeviceStatusSnapshot {
  image_version?: string
  running_slot?: string
  slot_confirmed?: boolean
  component_versions?: Record<string, string>
  health_known?: boolean
  health_score?: number
  time_synchronized?: boolean
  services?: { unit: string; active: string }[]
  serial?: string
  hardware_revision?: string
  istate_state?: string
  collected_at_unix_ms?: string
}
