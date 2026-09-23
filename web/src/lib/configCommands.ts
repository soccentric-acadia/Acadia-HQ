// Device configuration command channel — queues configuration.read /
// configuration.write against HQ's 202-accepted endpoints and polls
// `GET /devices/{id}/commands/{command_id}` for the durable terminal result.
//
// T-P17 (SB-6a/6b/6c): the device configuration tree is NESTED by config path
// (`{monitoring: {telemetry: {...}}, system: {time: {...}}}`) — descriptors
// carry `config_path` and this module binds reads through it and sends
// writes as nested `{section: object}` with read-modify-write merge. The
// device's redaction marker (`[redacted]`) is never written back as a
// literal: dropped fields keep their current device value once the device
// merge lands (T-P18).

import { api } from '@/lib/api'
import { REDACTED } from '@/lib/sectionSchemas'
import type { CommandStatus } from '@/lib/types'

export const CONFIG_CONTRACT_PENDING = 'awaiting_configuration_contract'

export interface ConfigurationCommandOutcome {
  command: CommandStatus
  /** The bound section object reported by the device, or null while unavailable/pending. */
  values: Record<string, unknown> | null
}

/** Navigate a dot-separated path into a config tree, tolerating missing nodes. */
function bindSection(
  tree: Record<string, unknown> | null,
  configPath: string,
): Record<string, unknown> | null {
  let node: unknown = tree
  for (const part of configPath.split('.')) {
    if (!node || typeof node !== 'object') return null
    node = (node as Record<string, unknown>)[part]
  }
  return node && typeof node === 'object' && !Array.isArray(node)
    ? (node as Record<string, unknown>)
    : null
}

/** The device configuration document from a command result payload: the
 * contract read result is `{schema_version, config, secrets_included}` —
 * tolerate a bare config tree as well. */
function configTreeFromPayload(
  payload: Record<string, unknown> | null,
): Record<string, unknown> | null {
  if (!payload || typeof payload !== 'object') return null
  if (payload.config && typeof payload.config === 'object') {
    return payload.config as Record<string, unknown>
  }
  // Tolerate a wrapped {"values": {...}} result form.
  if (payload.values && typeof payload.values === 'object') {
    const v = payload.values as Record<string, unknown>
    if (v.config && typeof v.config === 'object') return v.config as Record<string, unknown>
    return v
  }
  return null
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/** Poll a queued command until it reaches a terminal state or times out. */
export async function awaitCommand(
  deviceId: string,
  commandId: string,
  { timeoutMs = 20000, intervalMs = 1200 }: { timeoutMs?: number; intervalMs?: number } = {},
): Promise<CommandStatus | null> {
  const deadline = Date.now() + timeoutMs
  let last: CommandStatus | null = null
  while (Date.now() < deadline) {
    try {
      last = await api.devices.commandStatus(deviceId, commandId)
    } catch {
      return last
    }
    if (['succeeded', 'failed', 'expired'].includes(last.state)) return last
    await sleep(intervalMs)
  }
  return last
}

function queuedAsStatus(queued: {
  command_id: string
  correlation_id: string
  integration_status?: string
}): CommandStatus {
  return {
    command_id: queued.command_id,
    state: 'queued',
    attempt_count: 0,
    correlation_id: queued.correlation_id,
    code: null,
    error: null,
    payload: null,
    completed_at: null,
    expires_at: null,
    retryable: null,
    integration_status: queued.integration_status,
  }
}

/** Queue a configuration read and wait for the durable result. The returned
 * `values` are the section object bound at the descriptor's config_path. */
export async function readConfiguration(
  deviceId: string,
  options?: { timeoutMs?: number; descriptor?: { config_path: string } },
): Promise<ConfigurationCommandOutcome> {
  const queued = await api.configuration.read(deviceId)
  const command = await awaitCommand(deviceId, queued.command_id, options)
  if (!command || command.state !== 'succeeded') {
    return { command: command ?? queuedAsStatus(queued), values: null }
  }
  const tree = configTreeFromPayload(command.payload)
  const path = options?.descriptor?.config_path
  return {
    command,
    values: tree ? (path ? bindSection(tree, path) : tree) : null,
  }
}

/** Queue a configuration write (signed server-side) and wait for the ack.
 *
 * Read-modify-write (T-P17/6c): `sectionValues` are overlaid onto the
 * previously-read section object and sent as a nested section object at the
 * descriptor's config path — `{monitoring: {telemetry: {...}}}` — which the
 * device merges. Fields holding the redaction marker are dropped, never
 * written back as literals. */
export async function writeConfiguration(
  deviceId: string,
  descriptor: { config_path: string },
  sectionValues: Record<string, unknown>,
  current?: Record<string, unknown> | null,
  options?: { timeoutMs?: number },
): Promise<ConfigurationCommandOutcome> {
  const merged: Record<string, unknown> = { ...current, ...sectionValues }
  for (const [k, v] of Object.entries(merged)) {
    if (v === REDACTED) delete merged[k]
  }
  // Nest the section at its config path: 'monitoring.telemetry' →
  // {monitoring: {telemetry: {...}}}.
  const parts = descriptor.config_path.split('.')
  let nested: Record<string, unknown> = merged
  for (let i = parts.length - 1; i > 0; i--) {
    nested = { [parts[i] as string]: nested }
  }
  const config: Record<string, unknown> = { [parts[0] as string]: nested }
  const queued = await api.configuration.write(deviceId, config)
  const command = await awaitCommand(deviceId, queued.command_id, options)
  if (!command || command.state === 'queued' || command.state === 'delivered') {
    return { command: command ?? queuedAsStatus(queued), values: null }
  }
  return { command, values: null }
}