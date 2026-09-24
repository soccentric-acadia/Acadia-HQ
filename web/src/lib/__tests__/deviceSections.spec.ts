// Task 008 — device section registry parity vs Acadia-Configuration (WebConfig)
// `frontend/pages/registry.js`. The expected ids/categories/labels below are a
// checked-in snapshot of that file; scripts/check-section-parity.mjs re-diffs
// against the live sibling repository when it is available.
import { describe, expect, it } from 'vitest'
import { DEVICE_SECTIONS, SECTION_IDS, sectionMeta, sectionsByCategory } from '@/lib/deviceSections'

// WebConfig NAV snapshot (registry.js), flattened to [id, label, category].
const WEBCONFIG_NAV: [string, string, string][] = [
  ['overview', 'Overview', 'Dashboard'],
  ['monitoring', 'Monitoring', 'Dashboard'],
  ['telemetry', 'Telemetry', 'Dashboard'],
  ['faults', 'Faults', 'Dashboard'],
  ['alerts', 'Alarms', 'Dashboard'],
  ['logs', 'Logs', 'Dashboard'],
  ['system', 'System settings', 'System'],
  ['time', 'Clock', 'Time & Sync'],
  ['ntp', 'NTP', 'Time & Sync'],
  ['ptp', 'PTP', 'Time & Sync'],
  ['gps', 'GPS / GNSS', 'Time & Sync'],
  ['power', 'Power', 'System'],
  ['system-control', 'System Control', 'System'],
  ['wired', 'Wired', 'Connectivity'],
  ['wireless', 'Wireless', 'Connectivity'],
  ['5g', '5G', 'Connectivity'],
  ['services', 'Services', 'Connectivity'],
  ['cloud', 'Cloud', 'Connectivity'],
  ['updates', 'Updates', 'Maintenance'],
  ['remote-logs', 'Remote Logs', 'Maintenance'],
  ['remote-updates', 'Remote Updates', 'Maintenance'],
  ['backup', 'Backup & Restore', 'Maintenance'],
  ['security', 'Security', 'Security'],
  ['ssh', 'SSH & Console', 'Security'],
  ['firewall', 'Firewall', 'Security'],
  ['secure-boot', 'Secure Boot', 'Security'],
  ['users', 'Users & Groups', 'Security'],
  ['display', 'Display', 'Hardware'],
  ['leds', 'Board LEDs', 'Hardware'],
  ['gpio', 'GPIO', 'Hardware'],
  ['serial', 'Serial Peripherals', 'Hardware'],
  ['can', 'CAN', 'Hardware'],
  ['usb', 'USB', 'Hardware'],
  ['pci', 'PCI', 'Hardware'],
  ['mcu', 'MCU', 'Hardware'],
  ['camera', 'Camera', 'Hardware'],
]

// WebConfig adminOnly flags (registry.js).
const WEBCONFIG_ADMIN_ONLY = new Set([
  'system-control',
  'remote-logs',
  'remote-updates',
  'backup',
  'security',
  'ssh',
  'firewall',
  'secure-boot',
  'users',
  'leds',
  'gpio',
  'serial',
  'can',
])

describe('device section registry', () => {
  const WEBCONFIG_IDS = WEBCONFIG_NAV.map(([id]) => id)
  it('mirrors the WebConfig registry 1:1 (ids, labels, categories, order)', () => {
    expect(SECTION_IDS).toEqual(WEBCONFIG_NAV.map(([id]) => id))
    DEVICE_SECTIONS.forEach((section, i) => {
      const entry = WEBCONFIG_NAV[i]
      expect(entry).toBeDefined()
      const [id, label, category] = entry!
      expect(section.id).toBe(id)
      expect(section.label).toBe(label)
      expect(section.category).toBe(category)
    })
  })

  it('mirrors the WebConfig adminOnly flags', () => {
    for (const [id] of WEBCONFIG_NAV) {
      const section = DEVICE_SECTIONS.find((s) => s.id === id)
      expect(section).toBeDefined()
      expect(section!.adminOnly != null).toBe(WEBCONFIG_ADMIN_ONLY.has(id))
    }
  })

  it('assigns the same g-chord key set as WebConfig', () => {
    // WebConfig itself reuses '6' (gps and remote-logs share it); parity means
    // the same multiset of keys, not enforced uniqueness.
    const keys = DEVICE_SECTIONS.map((s) => s.key).sort()
    const expected = WEBCONFIG_IDS.map((id) => DEVICE_SECTIONS.find((s) => s.id === id)!.key).sort()
    expect(keys).toEqual(expected)
    const dupes = keys.filter((k, i) => i > 0 && keys[i - 1] === k)
    expect(dupes).toEqual(['6'])
  })

  it('groups sections by category in WebConfig sidebar order', () => {
    const groups = sectionsByCategory(true).map(([category, sections]) => ({
      category,
      ids: sections.map((s) => s.id),
    }))
    expect(groups.map((g) => g.category)).toEqual([
      'Dashboard',
      'System',
      'Time & Sync',
      'Connectivity',
      'Maintenance',
      'Security',
      'Hardware',
    ])
  })

  it('hides sections of deferred features (T-P00e)', () => {
    const visible = sectionsByCategory(true).flatMap(([, list]) => list.map((s) => s.id))
    expect(visible).not.toContain('ptp')
    expect(visible).not.toContain('5g')
    expect(sectionMeta('ptp')).toBeUndefined()
    expect(sectionMeta('time')).toBeDefined()
  })

  it('hides admin-only sections from non-admin users', () => {
    const visible = sectionsByCategory(false).flatMap(([, sections]) => sections.map((s) => s.id))
    expect(visible).not.toContain('system-control')
    expect(visible).not.toContain('backup')
    expect(visible).not.toContain('security')
    expect(visible).toContain('overview')
  })

  it('has a page header for every section', async () => {
    const { SECTION_HEADERS } = await import('@/lib/deviceSections')
    for (const id of SECTION_IDS) {
      expect(SECTION_HEADERS[id]).toBeDefined()
    }
  })
})
