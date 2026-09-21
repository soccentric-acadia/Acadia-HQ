// Task 008 — schema-driven form: WebConfig descriptor parity, validation, dirty tracking.
import { describe, expect, it } from 'vitest'
import { SECTION_DESCRIPTORS, validateField, validateValues } from '@/lib/sectionSchemas'

describe('sectionSchemas', () => {
  it('descriptors use the WebConfig field-type set (string|int|bool|enum|secret)', () => {
    const allowed = new Set(['string', 'int', 'bool', 'enum', 'secret'])
    for (const descriptor of Object.values(SECTION_DESCRIPTORS)) {
      for (const group of descriptor.groups) {
        for (const field of group.fields) {
          expect(allowed.has(field.field_type), `${descriptor.id}.${field.id}`).toBe(true)
        }
      }
    }
  })

  it('telemetry descriptor mirrors the WebConfig publishing-policy fields', () => {
    const fields = SECTION_DESCRIPTORS.telemetry!.groups[0]!.fields.map((f) => f.id)
    // From WebConfig pages/telemetry.js.
    expect(fields).toEqual([
      'enabled',
      'include_diagnostics',
      'server_url',
      'username',
      'password',
      'publish_interval_secs',
    ])
  })

  it('validates int min (publish interval >= 5, WebConfig rule)', () => {
    const field = SECTION_DESCRIPTORS.telemetry!.groups[0]!.fields.find(
      (f) => f.id === 'publish_interval_secs',
    )!
    expect(validateField(field, 4)).toBe('min 5')
    expect(validateField(field, 5)).toBe('')
    expect(validateField(field, 5.5)).toBe('must be an integer')
  })

  it('marks required fields and enum choices', () => {
    expect(
      validateField(
        { id: 'x', title: 'X', field_type: 'enum', required: true, options: [{ value: 'a' }] },
        '',
      ),
    ).toBe('required')
    expect(
      validateField({ id: 'x', title: 'X', field_type: 'enum', options: [{ value: 'a' }] }, 'b'),
    ).toBe('invalid choice')
  })

  it('validates whole values objects', () => {
    const descriptor = SECTION_DESCRIPTORS.telemetry!
    const errors = validateValues(descriptor, { publish_interval_secs: 1 })
    expect(Object.keys(errors)).toEqual(['publish_interval_secs'])
    expect(validateValues(descriptor, { publish_interval_secs: 30 })).toEqual({})
  })
})
