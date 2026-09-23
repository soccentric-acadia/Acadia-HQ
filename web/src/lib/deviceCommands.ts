// T-P20: queue a device command and wait for the device-reported outcome.
import { awaitCommand } from './configCommands'
import type { CommandStatus, QueuedCommand } from './types'
import { toast } from '@/stores/toasts'

export interface CommandRun {
  status: CommandStatus | null
  ok: boolean
}

/**
 * Queue via `queue()`, then poll the durable command until it is terminal.
 * Toasts the outcome with `label`. A command still queued at the deadline
 * (device offline) is reported as pending, not failed — it is delivered on
 * the next connection until its TTL.
 */
export async function runDeviceCommand(
  deviceId: string,
  label: string,
  queue: () => Promise<QueuedCommand>,
  opts: { timeoutMs?: number; quiet?: boolean } = {},
): Promise<CommandRun> {
  let queued: QueuedCommand
  try {
    queued = await queue()
  } catch (e) {
    toast(e instanceof Error ? e.message : `${label} failed.`, 'error')
    return { status: null, ok: false }
  }
  const status = await awaitCommand(deviceId, queued.command_id, { timeoutMs: opts.timeoutMs })
  const ok = status?.state === 'succeeded'
  if (!opts.quiet) {
    if (ok) toast(`${label}: done.`, 'success')
    else if (!status || status.state === 'queued' || status.state === 'delivering')
      toast(`${label}: queued — the device runs it when it next connects.`, 'info')
    else toast(`${label}: ${status.error ?? status.code ?? status.state}`, 'error')
  }
  return { status, ok }
}
