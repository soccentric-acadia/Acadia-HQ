// Device configuration command channel — queues configuration.read /
// configuration.write against HQ's 202-accepted endpoints and polls
// `GET /devices/{id}/commands/{command_id}` for the durable terminal result.
//
// HQ never reports a queued configuration command as device-applied state:
// while `integration_status === 'awaiting_configuration_contract'` the read
// result carries no device config and callers must surface the pending state.

import { api } from '@/lib/api'
import type { CommandStatus } from '@/lib/types'

export const CONFIG_CONTRACT_PENDING = 'awaiting_configuration_contract'

export interface ConfigurationCommandOutcome {
  command: CommandStatus
  /** Values reported by the device, or null while unavailable/pending. */
  values: Record<string, unknown> | null
}

function valuesFromPayload(
  payload: Record<string, unknown> | null,
): Record<string, unknown> | null {
  if (!payload || typeof payload !== 'object') return null
  // The device contract reports {"values": {...}} inside the result payload;
  // tolerate the raw document form as well.
  if (payload.values && typeof payload.values === 'object') {
    return payload.values as Record<string, unknown>
  }
  return payload
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

/** Queue a configuration read and wait for the durable result. */
export async function readConfiguration(
  deviceId: string,
  options?: { timeoutMs?: number },
): Promise<ConfigurationCommandOutcome> {
  const queued = await api.configuration.read(deviceId)
  const command = await awaitCommand(deviceId, queued.command_id, options)
  if (!command || command.state !== 'succeeded') {
    return { command: command ?? queuedAsStatus(queued), values: null }
  }
  return { command, values: valuesFromPayload(command.payload) }
}

/** Queue a configuration write (signed server-side) and wait for the ack. */
export async function writeConfiguration(
  deviceId: string,
  values: Record<string, unknown>,
  options?: { timeoutMs?: number },
): Promise<ConfigurationCommandOutcome> {
  const queued = await api.configuration.write(deviceId, values)
  const command = await awaitCommand(deviceId, queued.command_id, options)
  if (!command || command.state === 'queued' || command.state === 'delivered') {
    return { command: command ?? queuedAsStatus(queued), values: null }
  }
  return { command, values: null }
}
