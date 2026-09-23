// Schema-driven section descriptors — same descriptor shape as WebConfig's
// `frontend/components/schema-form.js` (task 008): a section descriptor lists
// titled groups of typed fields; the renderer builds inputs, applies
// client-side validation, and the backend re-validates. Adding a setting is a
// schema entry, zero UI code (WebConfig spec §3).
//
// Sections without a descriptor yet render the generic pending-contract state;
// descriptors land here as the device configuration contract reports them.

export type FieldType = 'string' | 'int' | 'bool' | 'enum' | 'secret' | 'string_list'

export interface FieldValidation {
  min?: number
  max?: number
  min_len?: number
  max_len?: number
  pattern?: string
}

export interface FieldOption {
  value: string
  label?: string
}

export interface SectionField {
  id: string
  title: string
  field_type: FieldType
  required?: boolean
  options?: FieldOption[] | 'timezones'
  validation?: FieldValidation
  help?: string
}

export interface SectionGroup {
  id: string
  title: string
  fields: SectionField[]
}

export interface SectionDescriptor {
  id: string
  title: string
  /** The device configuration path this section binds to, dot-separated
   * (T-P17/SB-6a): reads navigate the device's config tree through it and
   * writes are sent as nested `{section: object}` at the same path. */
  config_path: string
  groups: SectionGroup[]
}

/** The marker the device uses for redacted secrets in configuration reads
 * (webconfigd redact_secrets) — never written back as a literal (T-P17). */
export const REDACTED = '[redacted]' as const

export const SECTION_DESCRIPTORS: Record<string, SectionDescriptor> = {
  // Telemetry publishing policy — mirrors WebConfig pages/telemetry.js.
  // Keyed by the UI section id; config_path is the DEVICE contract path
  // (T-P17/SB-6a): the device tree is {monitoring: {telemetry: {...}}}.
  telemetry: {
    id: 'telemetry',
    title: 'Telemetry publishing',
    config_path: 'monitoring.telemetry',
    groups: [
      {
        id: 'publishing',
        title: 'Publishing policy',
        fields: [
          { id: 'enabled', title: 'Enable telemetry publishing', field_type: 'bool' },
          {
            id: 'include_diagnostics',
            title: 'Include diagnostics',
            field_type: 'bool',
            help: 'Attach diagnostic payloads to published telemetry.',
          },
          {
            id: 'server_url',
            title: 'Telemetry server URL',
            field_type: 'string',
            help: 'Ingest endpoint the device publishes metrics to.',
          },
          { id: 'username', title: 'Login', field_type: 'string' },
          { id: 'password', title: 'Password', field_type: 'secret' },
          {
            id: 'publish_interval_secs',
            title: 'Publish interval (seconds)',
            field_type: 'int',
            validation: { min: 5 },
            help: 'Minimum interval is 5 seconds.',
          },
        ],
      },
    ],
  },

  // Clock — mirrors WebConfig pages/time.js (timezone + air-gapped manual time).
  system: {
    id: 'system',
    title: 'System identity',
    config_path: 'system',
    groups: [
      {
        id: 'identity',
        title: 'Identity',
        fields: [
          {
            id: 'hostname',
            title: 'Hostname',
            field_type: 'string',
            validation: { pattern: '^[A-Za-z0-9][A-Za-z0-9-]{0,62}$' },
            help: 'RFC 1123 hostname — applied to the OS (serial/hw-revision come from the factory record, T-P24).',
          },
          { id: 'asset_tag', title: 'Asset tag', field_type: 'string' },
        ],
      },
    ],
  },
  time: {
    id: 'time',
    title: 'Clock',
    config_path: 'system.time',
    groups: [
      {
        id: 'time',
        title: 'Time settings',
        fields: [
          {
            id: 'timezone',
            title: 'Timezone',
            field_type: 'enum',
            options: 'timezones',
            help: 'IANA timezone for displayed times and scheduled operations.',
          },
          {
            id: 'ntp_enabled',
            title: 'NTP enabled',
            field_type: 'bool',
            help: 'Mutually exclusive with PTP (the device enforces the pair).',
          },
          {
            id: 'manual_datetime',
            title: 'Manual datetime (air-gapped)',
            field_type: 'string',
            help: 'Only used while NTP is disabled and the device cannot reach a time server.',
          },
        ],
      },
    ],
  },

  // NTP — the server list rides SystemConfig.ntp_servers (top-level field of
  // the system section; the RMW merge composes edits from the time/ntp/ptp/gps
  // pages, all bound through `system`).
  ntp: {
    id: 'ntp',
    title: 'NTP servers',
    config_path: 'system',
    groups: [
      {
        id: 'ntp',
        title: 'Network time',
        fields: [
          { id: 'ntp_servers', title: 'NTP server list', field_type: 'string_list', help: 'One server per line. Applied as the timesyncd drop-in (T-P02).' },
        ],
      },
    ],
  },

  ptp: {
    id: 'ptp',
    title: 'PTP',
    config_path: 'system.time',
    groups: [
      {
        id: 'ptp',
        title: 'Precision Time Protocol',
        fields: [
          { id: 'ptp_enabled', title: 'Enable PTP (ptp4l + phc2sys)', field_type: 'bool' },
          { id: 'ptp_interface', title: 'PTP interface', field_type: 'string', help: 'e.g. eth0 — the interface carrying the PTP domain.' },
          { id: 'ptp_domain', title: 'PTP domain', field_type: 'int', validation: { min: 0, max: 127 } },
        ],
      },
    ],
  },

  gps: {
    id: 'gps',
    title: 'GNSS time',
    config_path: 'system.time',
    groups: [
      {
        id: 'gps',
        title: 'GPS / GNSS time source',
        fields: [
          { id: 'gps_enabled', title: 'Enable GNSS time (gpsd + chrony)', field_type: 'bool' },
          { id: 'gps_device', title: 'gpsd device', field_type: 'string', help: 'e.g. /dev/ttyAMA2 — the Pico/GNSS link per the UART allocation.' },
          { id: 'gps_pps_device', title: 'PPS device', field_type: 'string', help: 'Optional kernel PPS source.' },
        ],
      },
    ],
  },

  wired: {
    id: 'wired',
    title: 'Wired network',
    config_path: 'network',
    groups: [
      {
        id: 'dns',
        title: 'DNS servers',
        fields: [
          { id: 'dns_servers', title: 'DNS server list', field_type: 'string_list', help: 'One resolver per line — applied as the resolved.conf.d drop-in. Per-interface addressing stays on the device network UI.' },
        ],
      },
    ],
  },

  wireless: {
    id: 'wireless',
    title: 'Wireless',
    config_path: 'network',
    groups: [
      {
        id: 'regulatory',
        title: 'Regulatory domain',
        fields: [
          { id: 'regulatory_domain', title: 'Regulatory domain', field_type: 'string', validation: { pattern: '^[A-Z]{2}$' }, help: 'Two-letter country code (iw reg set). Network list editing stays on the device Wi-Fi UI.' },
        ],
      },
    ],
  },

  services: {
    id: 'services',
    title: 'MQTT broker',
    config_path: 'services.mqtt',
    groups: [
      {
        id: 'mqtt',
        title: 'MQTT connectivity (alert delivery)',
        fields: [
          { id: 'enabled', title: 'Enable MQTT alert delivery', field_type: 'bool' },
          { id: 'host', title: 'Broker host', field_type: 'string' },
          { id: 'port', title: 'Broker port', field_type: 'int', validation: { min: 1, max: 65535 } },
          { id: 'tls', title: 'Use TLS', field_type: 'bool' },
          { id: 'username', title: 'Username', field_type: 'string' },
          { id: 'password', title: 'Password', field_type: 'secret' },
          { id: 'client_id', title: 'Client id', field_type: 'string' },
          { id: 'base_topic', title: 'Base topic', field_type: 'string' },
        ],
      },
    ],
  },

  cloud: {
    id: 'cloud',
    title: 'Cloud services',
    config_path: 'updates.ota',
    groups: [
      {
        id: 'ota',
        title: 'Update-server polling',
        fields: [
          { id: 'enabled', title: 'Enable update-server polling', field_type: 'bool', help: 'Notify-only check (K15); auto-apply stays [v2] and HQ-managed OTA is preferred (K09).' },
          { id: 'server_url', title: 'Update server URL', field_type: 'string' },
          { id: 'token', title: 'Poll token', field_type: 'secret' },
        ],
      },
    ],
  },

  security: {
    id: 'security',
    title: 'Session security',
    config_path: 'security',
    groups: [
      {
        id: 'session',
        title: 'Web session policy',
        fields: [
          { id: 'session_idle_timeout_secs', title: 'Idle timeout (seconds)', field_type: 'int', validation: { min: 60, max: 86400 } },
        ],
      },
    ],
  },

  ssh: {
    id: 'ssh',
    title: 'SSH & console',
    config_path: 'system.ssh',
    groups: [
      {
        id: 'ssh',
        title: 'SSH service',
        fields: [
          { id: 'sshd_enabled', title: 'Enable SSH (key-only)', field_type: 'bool' },
          { id: 'serial_getty_enabled', title: 'Serial console getty', field_type: 'bool' },
        ],
      },
    ],
  },

  firewall: {
    id: 'firewall',
    title: 'Firewall',
    config_path: 'network.firewall',
    groups: [
      {
        id: 'firewall',
        title: 'Service firewall',
        fields: [
          { id: 'enabled', title: 'Enable the service firewall', field_type: 'bool', help: 'Manages the device-owned inet webconfig table; the OS default-deny baseline (T-P14) always applies.' },
        ],
      },
    ],
  },

  leds: {
    id: 'leds',
    title: 'Board LEDs',
    config_path: 'io.board_leds',
    groups: [
      {
        id: 'leds',
        title: 'Status LEDs',
        fields: [
          { id: 'enabled', title: 'Enable board LED policy', field_type: 'bool' },
          { id: 'system_led', title: 'System LED (Instrumentation)', field_type: 'string', help: 'Device name, e.g. ACT.' },
          { id: 'os_led', title: 'OS LED', field_type: 'string' },
        ],
      },
    ],
  },

  serial: {
    id: 'serial',
    title: 'Serial ports',
    config_path: 'io',
    groups: [
      {
        id: 'serial',
        title: 'Serial subsystem',
        fields: [
          { id: 'serial_enabled', title: 'Enable serial port management', field_type: 'bool', help: 'Per-port entries are read-only here — edit on the device (list of objects).' },
        ],
      },
    ],
  },

  can: {
    id: 'can',
    title: 'CAN',
    config_path: 'io',
    groups: [
      {
        id: 'can',
        title: 'CAN subsystem',
        fields: [
          { id: 'can_enabled', title: 'Enable CAN interfaces', field_type: 'bool' },
        ],
      },
    ],
  },

  gpio: {
    id: 'gpio',
    title: 'GPIO',
    config_path: 'io',
    groups: [
      {
        id: 'gpio',
        title: 'GPIO subsystem',
        fields: [
          { id: 'gpio_enabled', title: 'Enable GPIO control', field_type: 'bool' },
        ],
      },
    ],
  },

  camera: {
    id: 'camera',
    title: 'Cameras',
    config_path: 'io',
    groups: [
      {
        id: 'camera',
        title: 'Camera subsystem',
        fields: [
          { id: 'cameras_enabled', title: 'Enable camera capture service', field_type: 'bool' },
        ],
      },
    ],
  },
}

/** Sections whose device view is live/read-only data (no configuration
 * contract): re-classified per T-P19 — usb/pci inventory, secure-boot state,
 * display status, MCU status (flash via the live page), 5G deferred
 * (T-P00e). These render a read-only notice instead of a pending-descriptor
 * state. */
export const READ_ONLY_SECTIONS: ReadonlySet<string> = new Set([
  'display',
  'usb',
  'pci',
  'secure-boot',
  '5g',
  'mcu',
])

/** Sections managed through dedicated device COMMANDS, not configuration
 * (T-P19/T-P20): device user/group management. */
export const COMMAND_MANAGED_SECTIONS: ReadonlySet<string> = new Set(['users'])

export function fieldOptions(field: SectionField): FieldOption[] {
  if (field.options === 'timezones') {
    // Full IANA catalog from the browser's own tz database (WebConfig
    // pages/time.js); defensive fallback keeps the page usable on old engines.
    let zones: string[] = []
    try {
      const intl = Intl as unknown as { supportedValuesOf?: (kind: string) => string[] }
      zones = intl.supportedValuesOf ? intl.supportedValuesOf('timeZone') : []
    } catch {
      zones = []
    }
    if (zones.length === 0) {
      zones = [
        'UTC',
        'America/New_York',
        'America/Chicago',
        'America/Denver',
        'America/Los_Angeles',
      ]
    }
    return zones.map((z) => ({ value: z, label: z.replace(/_/g, ' ') }))
  }
  return field.options ?? []
}

/** Validate one field against its rules; returns '' or an error message
 * (same rule set as WebConfig's schema-form validateField). */
export function validateField(field: SectionField, value: unknown): string {
  const v = field.validation ?? {}
  const empty = value === '' || value == null
  if (field.required && empty) return 'required'
  if (empty) return ''
  switch (field.field_type) {
    case 'int': {
      const n = Number(value)
      if (!Number.isInteger(n)) return 'must be an integer'
      if (v.min != null && n < v.min) return `min ${v.min}`
      if (v.max != null && n > v.max) return `max ${v.max}`
      break
    }
    case 'string':
    case 'secret': {
      const s = String(value)
      if (v.min_len != null && s.length < v.min_len) return `min length ${v.min_len}`
      if (v.max_len != null && s.length > v.max_len) return `max length ${v.max_len}`
      if (v.pattern) {
        try {
          if (!new RegExp(v.pattern).test(s)) return 'pattern mismatch'
        } catch {
          // bad pattern: skip
        }
      }
      break
    }
    case 'enum': {
      const options = fieldOptions(field)
      if (options.length && !options.some((o) => o.value === value)) return 'invalid choice'
      break
    }
  }
  return ''
}

/** Validate a whole values object against a descriptor; returns a map of
 * fieldId -> error (empty map = valid). */
export function validateValues(
  descriptor: SectionDescriptor,
  values: Record<string, unknown>,
): Record<string, string> {
  const errors: Record<string, string> = {}
  for (const group of descriptor.groups) {
    for (const field of group.fields) {
      const error = validateField(field, values[field.id])
      if (error) errors[field.id] = error
    }
  }
  return errors
}
