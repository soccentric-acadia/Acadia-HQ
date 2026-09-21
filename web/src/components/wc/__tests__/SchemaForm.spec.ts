// Task 008 — schema form component: renders WebConfig-style fields, validates
// before save, exposes dirty state for the navigation guard.
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { SECTION_DESCRIPTORS } from '@/lib/sectionSchemas'
import SchemaForm from '@/components/wc/SchemaForm.vue'

const descriptor = SECTION_DESCRIPTORS.telemetry!

describe('SchemaForm', () => {
  it('renders one control per descriptor field', () => {
    const wrapper = mount(SchemaForm, {
      props: { descriptor, values: {} },
    })
    // bool fields render switches; the rest render .input controls
    expect(wrapper.findAll('.switch').length).toBe(2)
    expect(wrapper.findAll('.input').length).toBe(4)
  })

  it('blocks save when validation fails and reports the error', async () => {
    const wrapper = mount(SchemaForm, {
      props: { descriptor, values: { publish_interval_secs: 30 } },
    })
    const inputs = wrapper.findAll('.input')
    expect(inputs.length).toBe(4)
    const numberInput = inputs[3]!
    await numberInput.setValue('1')
    await wrapper.find('form .btn, .form-actions .btn').trigger('click')
    expect(wrapper.find('.field-error').text()).toBe('min 5')
    expect(wrapper.emitted('save')).toBeUndefined()
  })

  it('emits save with merged values when valid', async () => {
    const wrapper = mount(SchemaForm, {
      props: {
        descriptor,
        values: { enabled: true, server_url: 'https://t.example', publish_interval_secs: 30 },
      },
    })
    await wrapper.find('.form-actions .btn').trigger('click')
    expect(wrapper.emitted('save')).toBeTruthy()
    const payload = wrapper.emitted('save')![0]![0] as Record<string, unknown>
    expect(payload.enabled).toBe(true)
    expect(payload.publish_interval_secs).toBe(30)
  })

  it('reports dirty when values diverge from the device-reported ones', async () => {
    const wrapper = mount(SchemaForm, {
      props: { descriptor, values: { server_url: 'https://t.example' } },
    })
    expect((wrapper.vm as unknown as { dirty: boolean }).dirty).toBe(false)
    await wrapper.findAll('.input')[0]!.setValue('https://other.example')
    expect((wrapper.vm as unknown as { dirty: boolean }).dirty).toBe(true)
  })
})