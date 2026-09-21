// Schema-driven section descriptors — same descriptor shape as WebConfig's
// `frontend/components/schema-form.js` (task 008): a section descriptor lists
// titled groups of typed fields; the renderer builds inputs, applies
// client-side validation, and the backend re-validates. Adding a setting is a
// schema entry, zero UI code (WebConfig spec §3).
//
// Sections without a descriptor yet render the generic pending-contract state;
// descriptors land here as the device configuration contract reports them.

export type FieldType = 'string' | 'int' | 'bool' | 'enum' | 'secret'

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
  groups: SectionGroup[]
}

export const SECTION_DESCRIPTORS: Record<string, SectionDescriptor> = {
  // Telemetry publishing policy — mirrors WebConfig pages/telemetry.js.
  telemetry: {
    id: 'telemetry',
    title: 'Telemetry publishing',
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
  time: {
    id: 'time',
    title: 'Clock',
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
            id: 'manual_datetime',
            title: 'Manual datetime (air-gapped)',
            field_type: 'string',
            help: 'Only used while NTP is disabled and the device cannot reach a time server.',
          },
        ],
      },
    ],
  },
}

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
