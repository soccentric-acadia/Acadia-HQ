// T-P20: device command producers + runDeviceCommand polling.
import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from '@/lib/api'
import { runDeviceCommand } from '@/lib/deviceCommands'
import type { CommandStatus } from '@/lib/types'

function status(state: CommandStatus['state'], extra: Partial<CommandStatus> = {}): CommandStatus {
  return {
    command_id: 'c1',
    state,
    attempt_count: 1,
    correlation_id: 'c1',
    code: null,
    error: null,
    payload: null,
    completed_at: null,
    expires_at: null,
    retryable: null,
    ...extra,
  }
}

afterEach(() => vi.restoreAllMocks())

describe('api paths', () => {
  it('posts T-P20 commands and the fixed legacy routes to real endpoints', async () => {
    const fetchMock = vi
      .fn<(input: string, init?: RequestInit) => Promise<Response>>()
      .mockImplementation(
        async () => new Response(JSON.stringify({ command_id: 'c1' }), { status: 202 }),
      )
    vi.stubGlobal('fetch', fetchMock)
    await api.commands.reboot('d1')
    await api.commands.shutdown('d1', 'SHUTDOWN')
    await api.commands.serviceControl('d1', 'sshd.service', 'restart')
    await api.devices.factoryReset('d1')
    await api.devices.disable('d1')
    const urls = fetchMock.mock.calls.map((c) => c[0])
    expect(urls).toEqual([
      '/api/devices/d1/power/reboot',
      '/api/devices/d1/power/shutdown',
      '/api/devices/d1/services/control',
      '/api/devices/d1/updates/factory-reset',
      '/api/devices/d1/credential/revoke',
    ])
    expect(JSON.parse(fetchMock.mock.calls[1][1]?.body as string)).toEqual({
      confirmation: 'SHUTDOWN',
    })
    vi.unstubAllGlobals()
  })
})

describe('runDeviceCommand', () => {
  it('returns ok with the device payload once the command succeeds', async () => {
    vi.spyOn(api.devices, 'commandStatus').mockResolvedValue(
      status('succeeded', { payload: { users: [] } }),
    )
    const run = await runDeviceCommand('d1', 'List', async () => ({ command_id: 'c1' }), {
      quiet: true,
    })
    expect(run.ok).toBe(true)
    expect(run.status?.payload).toEqual({ users: [] })
  })

  it('reports failure without throwing', async () => {
    vi.spyOn(api.devices, 'commandStatus').mockResolvedValue(
      status('failed', { code: 'PERMISSION_DENIED', error: 'not allowlisted' }),
    )
    const run = await runDeviceCommand('d1', 'Restart', async () => ({ command_id: 'c1' }), {
      quiet: true,
    })
    expect(run.ok).toBe(false)
    expect(run.status?.code).toBe('PERMISSION_DENIED')
  })

  it('treats a queue error as not ok', async () => {
    const run = await runDeviceCommand(
      'd1',
      'Reboot',
      async () => {
        throw new Error('403')
      },
      { quiet: true },
    )
    expect(run).toEqual({ status: null, ok: false })
  })
})
