// T-P17 (SB-6a/b/c): the configuration contract binds reads through the
// descriptor's config_path, writes nest the section object at the same path,
// and the device's redaction marker is never written back.
import { describe, expect, it, vi } from 'vitest'
import { REDACTED, SECTION_DESCRIPTORS } from '@/lib/sectionSchemas'
import { api } from '@/lib/api'
import { CONFIG_CONTRACT_PENDING, readConfiguration, writeConfiguration } from '@/lib/configCommands'

const TELEMETRY_DESCRIPTOR = SECTION_DESCRIPTORS.telemetry!

describe('configuration contract binding', () => {
  it('descriptors carry the device config path (monitoring.telemetry / system.time)', () => {
    expect(TELEMETRY_DESCRIPTOR.config_path).toBe('monitoring.telemetry')
    expect(SECTION_DESCRIPTORS.time!.config_path).toBe('system.time')
  })

  it('read binds the nested section object from the device document', async () => {
    const tree = {
      schema_version: 1,
      config: { monitoring: { telemetry: { enabled: true, server_url: 'mqtts://x' } } },
      secrets_included: false,
    }
    vi.spyOn(api.configuration, 'read').mockResolvedValue({
      command_id: 'c1', correlation_id: 'c1',
    } as never)
    vi.spyOn(api.devices, 'commandStatus').mockResolvedValue({
      command_id: 'c1',
      state: 'succeeded',
      payload: tree,
    } as never)
    const out = await readConfiguration('dev-1', { descriptor: TELEMETRY_DESCRIPTOR })
    expect(out.values).toEqual({ enabled: true, server_url: 'mqtts://x' })
  })

  it('write nests the section at the config path and drops redacted secrets', async () => {
    const write = vi
      .fn<(id: string, values: Record<string, unknown>) => Promise<unknown>>()
      .mockResolvedValue({ command_id: 'c2', correlation_id: 'c2' })
    vi.spyOn(api.configuration, 'write').mockImplementation(write as never)
    vi.spyOn(api.devices, 'commandStatus').mockResolvedValue({
      command_id: 'c2',
      state: 'succeeded',
      payload: null,
    } as never)
    await writeConfiguration(
      'dev-1',
      TELEMETRY_DESCRIPTOR,
      { enabled: false, password: REDACTED },
      { enabled: true, server_url: 'mqtts://keep', password: REDACTED },
    )
    const sent = write.mock.calls[0]![1] as Record<string, unknown>
    expect(sent).toEqual({
      monitoring: {
        telemetry: { enabled: false, server_url: 'mqtts://keep' },
      },
    })
  })

  it('exposes the pending-contract marker', () => {
    expect(CONFIG_CONTRACT_PENDING).toBe('awaiting_configuration_contract')
  })
})
