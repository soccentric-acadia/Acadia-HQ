// Device section registry — mirrors Acadia-Configuration (WebConfig)
// `frontend/pages/registry.js` 1:1 (task 008): same ids, labels, categories,
// order, admin gating, and `g <key>` shortcut chords. The parity is asserted
// by `src/lib/__tests__/deviceSections.spec.ts` and
// `scripts/check-section-parity.mjs`.
//
// `key` is the second letter of the `g <key>` chord, copied from WebConfig
// (pages sharing a first letter don't collide).
import type { Component } from 'vue'
import {
  Activity,
  Archive,
  Cable,
  Camera,
  Clock,
  Cloud,
  Cpu,
  FileText,
  Home,
  LayoutGrid,
  Lightbulb,
  Lock,
  Monitor,
  Network,
  Power,
  RefreshCw,
  Settings,
  Shield,
  Signal,
  SquareTerminal,
  TriangleAlert,
  Usb,
  Users,
  Wifi,
} from 'lucide-vue-next'

export type SectionCategory =
  'Dashboard' | 'System' | 'Time & Sync' | 'Connectivity' | 'Maintenance' | 'Security' | 'Hardware'

export type SectionKind = 'live' | 'configuration'

export interface DeviceSection {
  id: string
  label: string
  icon: Component
  category: SectionCategory
  /** Second letter of the `g <key>` chord (WebConfig shortcut parity). */
  key: string
  adminOnly?: boolean
  /** live = backed by an existing HQ API; configuration = schema-driven via
   * the device configuration command channel. */
  kind: SectionKind
  /** Lazy-loaded section component (views/device/<id>.vue). */
  loader: () => Promise<{ default: Component }>
}

export const DEVICE_SECTIONS: DeviceSection[] = [
  // Dashboard: understand the current state before changing anything.
  {
    id: 'overview',
    label: 'Overview',
    icon: Home,
    category: 'Dashboard',
    key: 'o',
    kind: 'live',
    loader: () => import('@/views/device/overview.vue'),
  },
  {
    id: 'monitoring',
    label: 'Monitoring',
    icon: Activity,
    category: 'Dashboard',
    key: 'm',
    kind: 'live',
    loader: () => import('@/views/device/monitoring.vue'),
  },
  {
    id: 'telemetry',
    label: 'Telemetry',
    icon: Signal,
    category: 'Dashboard',
    key: '4',
    kind: 'configuration',
    loader: () => import('@/views/device/telemetry.vue'),
  },
  {
    id: 'faults',
    label: 'Faults',
    icon: TriangleAlert,
    category: 'Dashboard',
    key: '2',
    kind: 'live',
    loader: () => import('@/views/device/faults.vue'),
  },
  {
    id: 'alerts',
    label: 'Alarms',
    icon: TriangleAlert,
    category: 'Dashboard',
    key: 'a',
    kind: 'live',
    loader: () => import('@/views/device/alerts.vue'),
  },
  {
    id: 'logs',
    label: 'Logs',
    icon: FileText,
    category: 'Dashboard',
    key: 'l',
    kind: 'live',
    loader: () => import('@/views/device/logs.vue'),
  },

  // System: local identity and lifecycle controls.
  {
    id: 'system',
    label: 'System settings',
    icon: Settings,
    category: 'System',
    key: 's',
    kind: 'configuration',
    loader: () => import('@/views/device/system.vue'),
  },
  {
    id: 'time',
    label: 'Clock',
    icon: Clock,
    category: 'Time & Sync',
    key: 't',
    kind: 'configuration',
    loader: () => import('@/views/device/time.vue'),
  },
  {
    id: 'ntp',
    label: 'NTP',
    icon: Clock,
    category: 'Time & Sync',
    key: '8',
    kind: 'configuration',
    loader: () => import('@/views/device/ntp.vue'),
  },
  {
    id: 'ptp',
    label: 'PTP',
    icon: Activity,
    category: 'Time & Sync',
    key: '9',
    kind: 'configuration',
    loader: () => import('@/views/device/ptp.vue'),
  },
  {
    id: 'gps',
    label: 'GPS / GNSS',
    icon: Signal,
    category: 'Time & Sync',
    key: '6',
    kind: 'configuration',
    loader: () => import('@/views/device/gps.vue'),
  },
  {
    id: 'power',
    label: 'Power',
    icon: Power,
    category: 'System',
    key: 'p',
    kind: 'live',
    loader: () => import('@/views/device/power.vue'),
  },
  {
    id: 'system-control',
    label: 'System Control',
    icon: Settings,
    category: 'System',
    key: '0',
    kind: 'live',
    adminOnly: true,
    loader: () => import('@/views/device/system-control.vue'),
  },

  // Connectivity: network links and connected services.
  {
    id: 'wired',
    label: 'Wired',
    icon: Cable,
    category: 'Connectivity',
    key: 'n',
    kind: 'configuration',
    loader: () => import('@/views/device/wired.vue'),
  },
  {
    id: 'wireless',
    label: 'Wireless',
    icon: Wifi,
    category: 'Connectivity',
    key: 'h',
    kind: 'configuration',
    loader: () => import('@/views/device/wireless.vue'),
  },
  {
    id: '5g',
    label: '5G',
    icon: Signal,
    category: 'Connectivity',
    key: '5',
    kind: 'configuration',
    loader: () => import('@/views/device/fiveg.vue'),
  },
  {
    id: 'services',
    label: 'Services',
    icon: LayoutGrid,
    category: 'Connectivity',
    key: 'v',
    kind: 'configuration',
    loader: () => import('@/views/device/services.vue'),
  },
  {
    id: 'cloud',
    label: 'Cloud',
    icon: Cloud,
    category: 'Connectivity',
    key: 'c',
    kind: 'configuration',
    loader: () => import('@/views/device/cloud.vue'),
  },

  // Maintenance: updates and configuration recovery.
  {
    id: 'updates',
    label: 'Updates',
    icon: RefreshCw,
    category: 'Maintenance',
    key: 'u',
    kind: 'live',
    loader: () => import('@/views/device/updates.vue'),
  },
  {
    id: 'remote-logs',
    label: 'Remote Logs',
    icon: FileText,
    category: 'Maintenance',
    key: '6',
    kind: 'live',
    adminOnly: true,
    loader: () => import('@/views/device/remote-logs.vue'),
  },
  {
    id: 'remote-updates',
    label: 'Remote Updates',
    icon: Cloud,
    category: 'Maintenance',
    key: '7',
    kind: 'live',
    adminOnly: true,
    loader: () => import('@/views/device/remote-updates.vue'),
  },
  {
    id: 'backup',
    label: 'Backup & Restore',
    icon: Archive,
    category: 'Maintenance',
    key: 'b',
    kind: 'live',
    adminOnly: true,
    loader: () => import('@/views/device/backup.vue'),
  },

  // Security: access, exposure, trust, and user administration.
  {
    id: 'security',
    label: 'Security',
    icon: Shield,
    category: 'Security',
    key: 'e',
    kind: 'configuration',
    adminOnly: true,
    loader: () => import('@/views/device/security.vue'),
  },
  {
    id: 'ssh',
    label: 'SSH & Console',
    icon: SquareTerminal,
    category: 'Security',
    key: 'j',
    kind: 'configuration',
    adminOnly: true,
    loader: () => import('@/views/device/ssh.vue'),
  },
  {
    id: 'firewall',
    label: 'Firewall',
    icon: Shield,
    category: 'Security',
    key: 'f',
    kind: 'configuration',
    adminOnly: true,
    loader: () => import('@/views/device/firewall.vue'),
  },
  {
    id: 'secure-boot',
    label: 'Secure Boot',
    icon: Lock,
    category: 'Security',
    key: 'r',
    kind: 'configuration',
    adminOnly: true,
    loader: () => import('@/views/device/secure-boot.vue'),
  },
  {
    id: 'users',
    label: 'Users & Groups',
    icon: Users,
    category: 'Security',
    key: 'g',
    kind: 'configuration',
    adminOnly: true,
    loader: () => import('@/views/device/users.vue'),
  },

  // Hardware: individual peripheral controls.
  {
    id: 'display',
    label: 'Display',
    icon: Monitor,
    category: 'Hardware',
    key: 'i',
    kind: 'configuration',
    loader: () => import('@/views/device/display.vue'),
  },
  {
    id: 'leds',
    label: 'Board LEDs',
    icon: Lightbulb,
    category: 'Hardware',
    key: '1',
    kind: 'configuration',
    adminOnly: true,
    loader: () => import('@/views/device/leds.vue'),
  },
  {
    id: 'gpio',
    label: 'GPIO',
    icon: Network,
    category: 'Hardware',
    key: 'd',
    kind: 'configuration',
    adminOnly: true,
    loader: () => import('@/views/device/gpio.vue'),
  },
  {
    id: 'serial',
    label: 'Serial Peripherals',
    icon: Cable,
    category: 'Hardware',
    key: 'w',
    kind: 'configuration',
    adminOnly: true,
    loader: () => import('@/views/device/serial.vue'),
  },
  {
    id: 'can',
    label: 'CAN',
    icon: Network,
    category: 'Hardware',
    key: 'z',
    kind: 'configuration',
    adminOnly: true,
    loader: () => import('@/views/device/can.vue'),
  },
  {
    id: 'usb',
    label: 'USB',
    icon: Usb,
    category: 'Hardware',
    key: 'x',
    kind: 'configuration',
    loader: () => import('@/views/device/usb.vue'),
  },
  {
    id: 'pci',
    label: 'PCI',
    icon: Network,
    category: 'Hardware',
    key: 'y',
    kind: 'configuration',
    loader: () => import('@/views/device/pci.vue'),
  },
  {
    id: 'mcu',
    label: 'MCU',
    icon: Cpu,
    category: 'Hardware',
    key: 'q',
    kind: 'configuration',
    loader: () => import('@/views/device/mcu.vue'),
  },
  {
    id: 'camera',
    label: 'Camera',
    icon: Camera,
    category: 'Hardware',
    key: 'k',
    kind: 'configuration',
    loader: () => import('@/views/device/camera.vue'),
  },
]

export const SECTION_IDS = DEVICE_SECTIONS.map((s) => s.id)

export const sectionMeta = (id: string): DeviceSection | undefined =>
  DEVICE_SECTIONS.find((s) => s.id === id)

/** Category-grouped order, same grouping WebConfig's Sidebar renders. */
export function sectionsByCategory(adminOnly: boolean): [SectionCategory, DeviceSection[]][] {
  const groups = new Map<SectionCategory, DeviceSection[]>()
  for (const section of DEVICE_SECTIONS) {
    if (section.adminOnly && !adminOnly) continue
    const list = groups.get(section.category) ?? []
    list.push(section)
    groups.set(section.category, list)
  }
  return [...groups.entries()]
}

/** Section descriptor title/description, shown as the page header. */
export const SECTION_HEADERS: Record<string, { title: string; description: string }> = {
  overview: {
    title: 'Overview',
    description: 'Device identity, health, and current state at a glance.',
  },
  monitoring: {
    title: 'Monitoring',
    description: 'Device metrics reported to HQ, with per-metric history.',
  },
  telemetry: {
    title: 'Telemetry',
    description:
      'Control publication of device metrics and diagnostics to the configured cloud service.',
  },
  faults: { title: 'Faults', description: 'Faults reported by the device.' },
  alerts: { title: 'Alarms', description: 'Device-reported alarms and their lifecycle.' },
  logs: { title: 'Logs', description: 'Log bundles the device has uploaded to HQ.' },
  system: {
    title: 'System settings',
    description: 'Device identity and base system configuration.',
  },
  time: { title: 'Clock', description: 'Timezone and manual time for air-gapped systems.' },
  ntp: { title: 'NTP', description: 'Network Time Protocol synchronization.' },
  ptp: { title: 'PTP', description: 'Precision Time Protocol synchronization.' },
  gps: { title: 'GPS / GNSS', description: 'Satellite time synchronization.' },
  power: { title: 'Power', description: 'Safely reboot or shut down the device.' },
  'system-control': {
    title: 'System Control',
    description: 'Reset configuration or return the device to its installed defaults.',
  },
  wired: { title: 'Wired', description: 'Ethernet interfaces and addressing.' },
  wireless: { title: 'Wireless', description: 'Wi-Fi radios, networks, and access.' },
  '5g': { title: '5G', description: 'Cellular modems, SIM state, and signal quality.' },
  services: { title: 'Services', description: 'Connected services running on the device.' },
  cloud: { title: 'Cloud', description: 'Cloud connectivity settings for this device.' },
  updates: { title: 'Updates', description: 'Software updates delivered to the device from HQ.' },
  'remote-logs': { title: 'Remote Logs', description: 'Retrieve logs from the device through HQ.' },
  'remote-updates': {
    title: 'Remote Updates',
    description: 'Stage and apply device updates through HQ.',
  },
  backup: {
    title: 'Backup & Restore',
    description: 'Protect, inspect, and restore the device configuration.',
  },
  security: { title: 'Security', description: 'Device access, exposure, and trust settings.' },
  ssh: { title: 'SSH & Console', description: 'Shell access to the device.' },
  firewall: { title: 'Firewall', description: 'Perimeter filtering on the device.' },
  'secure-boot': { title: 'Secure Boot', description: 'Boot-chain trust settings.' },
  users: { title: 'Users & Groups', description: 'Local device accounts.' },
  display: { title: 'Display', description: 'Attached display configuration.' },
  leds: { title: 'Board LEDs', description: 'Onboard LED behavior.' },
  gpio: { title: 'GPIO', description: 'General-purpose input/output pins.' },
  serial: { title: 'Serial Peripherals', description: 'UART and RS-232/485 ports.' },
  can: { title: 'CAN', description: 'CAN bus interfaces.' },
  usb: { title: 'USB', description: 'USB ports and attached devices.' },
  pci: { title: 'PCI', description: 'PCI devices.' },
  mcu: { title: 'MCU', description: 'Onboard microcontroller applications.' },
  camera: { title: 'Camera', description: 'Attached cameras.' },
}
