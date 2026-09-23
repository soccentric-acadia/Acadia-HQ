<script setup lang="ts">
// Users — the device's local web-UI accounts, managed through the T-P20
// `users.*` commands (command-managed, not configuration). Password hashes
// never leave the device; an initial password is scrubbed from HQ once
// delivered.
import { onMounted, ref, watch } from 'vue'
import { api } from '@/lib/api'
import { runDeviceCommand } from '@/lib/deviceCommands'
import type { DeviceUserRow } from '@/lib/types'
import WcCallout from '@/components/wc/WcCallout.vue'
import WcCard from '@/components/wc/WcCard.vue'
import WcConfirmDialog from '@/components/wc/WcConfirmDialog.vue'
import WcEmptyState from '@/components/wc/WcEmptyState.vue'
import WcSkeleton from '@/components/wc/WcSkeleton.vue'

type Role = 'admin' | 'operator' | 'viewer'
const ROLES: Role[] = ['admin', 'operator', 'viewer']

const props = defineProps<{ deviceId: string }>()

const users = ref<DeviceUserRow[]>([])
const loading = ref(true)
const error = ref('')
const busy = ref(false)
const form = ref<{ username: string; role: Role; password: string }>({
  username: '',
  role: 'viewer',
  password: '',
})
const pendingDelete = ref<string | null>(null)

function take(payload: Record<string, unknown> | null | undefined) {
  const list = payload?.users
  if (Array.isArray(list)) users.value = list as DeviceUserRow[]
}

async function load() {
  loading.value = true
  error.value = ''
  const run = await runDeviceCommand(
    props.deviceId,
    'List users',
    () => api.commands.users(props.deviceId, { operation: 'users.list' }),
    { quiet: true },
  )
  if (run.ok) take(run.status?.payload)
  else error.value = 'The device did not answer (offline?). The list refreshes when it does.'
  loading.value = false
}

async function create() {
  busy.value = true
  const { username, role, password } = form.value
  const run = await runDeviceCommand(props.deviceId, `Create ${username}`, () =>
    api.commands.users(props.deviceId, { operation: 'users.create', username, role, password }),
  )
  if (run.ok) {
    take(run.status?.payload)
    form.value = { username: '', role: 'viewer', password: '' }
  }
  busy.value = false
}

async function setRole(username: string, role: Role) {
  busy.value = true
  const run = await runDeviceCommand(props.deviceId, `Set ${username} to ${role}`, () =>
    api.commands.users(props.deviceId, { operation: 'users.set_role', username, role }),
  )
  if (run.ok) take(run.status?.payload)
  busy.value = false
}

async function remove() {
  const username = pendingDelete.value
  if (!username) return
  busy.value = true
  const run = await runDeviceCommand(props.deviceId, `Delete ${username}`, () =>
    api.commands.users(props.deviceId, { operation: 'users.delete', username }),
  )
  if (run.ok) take(run.status?.payload)
  busy.value = false
  pendingDelete.value = null
}

watch(() => props.deviceId, load)
onMounted(load)
</script>

<template>
  <div v-if="loading">
    <WcSkeleton :lines="3" />
  </div>
  <div v-else class="page-surface">
    <WcCard title="Device accounts" subtitle="Local WebConfig users on this device.">
      <div v-if="error" class="error-text">{{ error }}</div>
      <WcEmptyState v-else-if="users.length === 0" title="No accounts" subtitle="First boot creates the admin." />
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>User</th><th>Role</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.username">
              <td><code>{{ u.username }}</code></td>
              <td>
                <select
                  class="input"
                  :value="u.role"
                  :disabled="busy"
                  :aria-label="`Role for ${u.username}`"
                  @change="setRole(u.username, ($event.target as HTMLSelectElement).value as Role)"
                >
                  <option v-for="r in ROLES" :key="r" :value="r">{{ r }}</option>
                </select>
              </td>
              <td>
                <div class="table-actions">
                  <button class="btn btn-destructive-outline btn-sm" :disabled="busy" @click="pendingDelete = u.username">
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </WcCard>

    <WcCard title="Add account" subtitle="The password is sent once and scrubbed from HQ after delivery.">
      <form class="stack" @submit.prevent="create">
        <input v-model="form.username" class="input" placeholder="username" aria-label="Username" required pattern="[A-Za-z0-9._-]+" />
        <select v-model="form.role" class="input" aria-label="Role">
          <option v-for="r in ROLES" :key="r" :value="r">{{ r }}</option>
        </select>
        <input v-model="form.password" class="input" type="password" minlength="8" placeholder="initial password (8+ characters)" aria-label="Initial password" required />
        <div><button class="btn btn-primary" :disabled="busy" type="submit">Create</button></div>
      </form>
    </WcCard>

    <WcCallout kind="info">The device refuses to delete or demote its last admin.</WcCallout>

    <WcConfirmDialog
      :open="pendingDelete !== null"
      :title="`Delete ${pendingDelete}?`"
      description="The account is removed from the device immediately."
      confirm-label="Delete"
      destructive
      @update:open="(v) => !v && (pendingDelete = null)"
      @confirm="remove"
    />
  </div>
</template>
