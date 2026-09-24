// Task 008 — command palette: Ctrl+K open, filtering, navigation events.
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import CommandPalette from '@/components/wc/CommandPalette.vue'

describe('CommandPalette', () => {
  it('lists all device sections plus actions for admins', () => {
    const wrapper = mount(CommandPalette, {
      props: { open: true, admin: true },
      global: { stubs: { teleport: true } },
    })
    const items = wrapper.findAll('.cmdk-item')
    // 36 sections − 2 deferred (ptp, 5g; T-P00e) + 2 actions
    expect(items.length).toBe(36)
  })

  it('hides admin-only sections from non-admin users (sidebar parity)', () => {
    const wrapper = mount(CommandPalette, {
      props: { open: true, admin: false },
      global: { stubs: { teleport: true } },
    })
    const labels = wrapper.findAll('.cmdk-item-text').map((n) => n.text())
    expect(labels).not.toContain('Backup & Restore')
    expect(labels).not.toContain('Security')
    expect(labels).toContain('Overview')
  })

  it('filters sections by query', async () => {
    const wrapper = mount(CommandPalette, {
      props: { open: true, admin: true },
      global: { stubs: { teleport: true } },
    })
    await wrapper.find('.cmdk-input').setValue('backup')
    const labels = wrapper.findAll('.cmdk-item-text').map((n) => n.text())
    expect(labels).toContain('Backup & Restore')
    expect(labels).not.toContain('Overview')
  })

  it('emits navigate on section click', async () => {
    const wrapper = mount(CommandPalette, {
      props: { open: true, admin: true },
      global: { stubs: { teleport: true } },
    })
    await wrapper.find('.cmdk-input').setValue('faults')
    const firstItem = wrapper.findAll('.cmdk-item')[0]
    expect(firstItem).toBeDefined()
    await firstItem!.trigger('click')
    expect(wrapper.emitted('navigate')![0]).toEqual(['faults'])
    expect(wrapper.emitted('update:open')?.at(-1)).toEqual([false])
  })

  it('emits action for palette actions', async () => {
    const wrapper = mount(CommandPalette, {
      props: { open: true, admin: true },
      global: { stubs: { teleport: true } },
    })
    await wrapper.find('.cmdk-input').setValue('back to all devices')
    const firstItem = wrapper.findAll('.cmdk-item')[0]
    expect(firstItem).toBeDefined()
    await firstItem!.trigger('click')
    expect(wrapper.emitted('action')![0]).toEqual(['back-to-devices'])
  })
})