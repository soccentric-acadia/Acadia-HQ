<script setup lang="ts">
// Remote Updates (admin) — T-P21: OTA artifact store + staged rollouts.
// HQ verifies each uploaded bundle against its declared SHA-256; a rollout
// installs on a canary wave first and continues only while the canary's
// failure rate stays within the halt threshold. The device re-verifies the
// checksum and the SWUpdate signature before installing.
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '@/lib/api'
import type { Device, Rollout, UpdateArtifact } from '@/lib/types'
import { toast } from '@/stores/toasts'
import WcCallout from '@/components/wc/WcCallout.vue'
import WcCard from '@/components/wc/WcCard.vue'
import WcEmptyState from '@/components/wc/WcEmptyState.vue'
import WcSkeleton from '@/components/wc/WcSkeleton.vue'

const props = defineProps<{ deviceId: string }>()

const loading = ref(true)
const busy = ref(false)
const device = ref<Device | null>(null)
const artifacts = ref<UpdateArtifact[]>([])
const rollouts = ref<Rollout[]>([])

const upload = ref({ version: '', board: '', sha: '' })
const file = ref<File | null>(null)
const tagsText = ref('')

const plan = ref<{
  artifactId: string
  target: 'this' | 'tag' | 'all'
  tag: string
  canary: number
  halt: number
  activate: boolean
}>({ artifactId: '', target: 'this', tag: '', canary: 10, halt: 20, activate: true })

const installable = computed(() => artifacts.value.filter((a) => a.uploaded_at))
const mine = computed(() =>
  rollouts.value.filter((r) => r.devices.some((d) => d.device_id === props.deviceId)),
)

function fmtBytes(n: number | null): string {
  if (!n) return '—'
  return n < 1024 * 1024 ? `${(n / 1024).toFixed(1)} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`
}

async function load() {
  loading.value = true
  try {
    const [d, a, r] = await Promise.all([
      api.devices.get(props.deviceId),
      api.fleetUpdates.artifacts(),
      api.fleetUpdates.rollouts(),
    ])
    device.value = d
    tagsText.value = (d.tags ?? []).join(', ')
    artifacts.value = a.items
    rollouts.value = r.items
  } catch (e) {
    toast(e instanceof Error ? e.message : 'Could not load updates.', 'error')
  } finally {
    loading.value = false
  }
}

async function sha256(f: File): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', await f.arrayBuffer())
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

async function computeSha() {
  if (!file.value) return
  if (file.value.size > 2 * 1024 ** 3) {
    toast('Files over 2 GiB: paste the SHA-256 from the build checksum manifest.', 'info')
    return
  }
  busy.value = true
  upload.value.sha = await sha256(file.value)
  busy.value = false
}

async function uploadArtifact() {
  if (!file.value) return
  busy.value = true
  try {
    const art = await api.fleetUpdates.createArtifact({
      version: upload.value.version,
      target_board_rev: upload.value.board,
      checksum_sha256: upload.value.sha.trim().toLowerCase(),
    })
    await api.fleetUpdates.uploadContent(art.id, file.value)
    toast(`Artifact ${art.version} uploaded and verified.`, 'success')
    upload.value = { version: '', board: '', sha: '' }
    file.value = null
    await load()
  } catch (e) {
    toast(e instanceof Error ? e.message : 'Upload failed.', 'error')
  } finally {
    busy.value = false
  }
}

async function saveTags() {
  const tags = tagsText.value
    .split(',')
    .map((t) => t.trim())
    .filter(Boolean)
  try {
    await api.fleetUpdates.setTags(props.deviceId, tags)
    toast('Tags saved.', 'success')
    await load()
  } catch (e) {
    toast(e instanceof Error ? e.message : 'Could not save tags.', 'error')
  }
}

async function createRollout() {
  busy.value = true
  const p = plan.value
  try {
    const r = await api.fleetUpdates.createRollout({
      artifact_id: p.artifactId,
      target: p.target === 'this' ? 'specific_devices' : p.target === 'tag' ? 'device_group' : 'all',
      device_ids: p.target === 'this' ? [props.deviceId] : undefined,
      tag: p.target === 'tag' ? p.tag : undefined,
      canary_percent: p.canary,
      halt_failure_percent: p.halt,
      auto_activate: p.activate,
    })
    toast(`Rollout created for ${r.summary.total} device(s). Start it when ready.`, 'success')
    await load()
  } catch (e) {
    toast(e instanceof Error ? e.message : 'Could not create the rollout.', 'error')
  } finally {
    busy.value = false
  }
}

async function drive(r: Rollout, action: 'start' | 'halt' | 'resume') {
  busy.value = true
  try {
    await api.fleetUpdates.drive(r.id, action)
    await load()
  } catch (e) {
    toast(e instanceof Error ? e.message : `Could not ${action} the rollout.`, 'error')
  } finally {
    busy.value = false
  }
}

function myStatus(r: Rollout): string {
  return r.devices.find((d) => d.device_id === props.deviceId)?.status ?? '—'
}

watch(() => props.deviceId, load)
onMounted(load)
</script>

<template>
  <div v-if="loading">
    <WcSkeleton :lines="4" />
  </div>
  <div v-else class="page-surface">
    <WcCard title="Rollouts for this device" subtitle="Staged updates that include this device.">
      <WcEmptyState v-if="mine.length === 0" title="No rollouts yet" subtitle="Create one below." />
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>Version</th><th>Rollout</th><th>This device</th><th>Progress</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="r in mine" :key="r.id">
              <td><code>{{ r.artifact_version }}</code></td>
              <td>
                <span class="badge">{{ r.status }}</span>
                <div v-if="r.halted_reason" class="muted">{{ r.halted_reason }}</div>
              </td>
              <td>{{ myStatus(r) }}</td>
              <td class="muted">
                {{ r.summary.succeeded ?? 0 }} ok · {{ r.summary.failed ?? 0 }} failed ·
                {{ r.summary.total }} total
              </td>
              <td>
                <div class="table-actions">
                  <button v-if="r.status === 'pending'" class="btn btn-primary btn-sm" :disabled="busy" @click="drive(r, 'start')">Start</button>
                  <button v-if="r.status === 'in_progress'" class="btn btn-outline btn-sm" :disabled="busy" @click="drive(r, 'halt')">Halt</button>
                  <button v-if="r.status === 'halted'" class="btn btn-outline btn-sm" :disabled="busy" @click="drive(r, 'resume')">Resume</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </WcCard>

    <WcCard title="New rollout" subtitle="Canary wave first; the rest follows while failures stay under the threshold.">
      <form class="stack" @submit.prevent="createRollout">
        <select v-model="plan.artifactId" class="input" aria-label="Artifact" required>
          <option value="" disabled>Choose a verified artifact</option>
          <option v-for="a in installable" :key="a.id" :value="a.id">
            {{ a.version }} ({{ a.target_board_rev }})
          </option>
        </select>
        <select v-model="plan.target" class="input" aria-label="Target">
          <option value="this">This device</option>
          <option value="tag">Devices with tag…</option>
          <option value="all">All devices</option>
        </select>
        <input v-if="plan.target === 'tag'" v-model="plan.tag" class="input" placeholder="tag" aria-label="Tag" required />
        <label class="row">Canary % <input v-model.number="plan.canary" class="input" type="number" min="1" max="100" /></label>
        <label class="row">Halt when canary failures exceed % <input v-model.number="plan.halt" class="input" type="number" min="0" max="100" /></label>
        <label class="row"><input v-model="plan.activate" type="checkbox" /> Reboot into the new slot after a successful install</label>
        <div><button class="btn btn-primary" :disabled="busy || !plan.artifactId" type="submit">Create rollout</button></div>
      </form>
    </WcCard>

    <WcCard title="Artifacts" subtitle="Signed .swu bundles, verified by SHA-256 on upload.">
      <div class="table-wrap" v-if="artifacts.length">
        <table class="table">
          <thead><tr><th>Version</th><th>Board</th><th>Size</th><th>Status</th></tr></thead>
          <tbody>
            <tr v-for="a in artifacts" :key="a.id">
              <td><code>{{ a.version }}</code></td>
              <td>{{ a.target_board_rev }}</td>
              <td>{{ fmtBytes(a.size_bytes) }}</td>
              <td>{{ a.uploaded_at ? 'verified' : 'awaiting upload' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <form class="stack" @submit.prevent="uploadArtifact">
        <input class="input" type="file" accept=".swu" aria-label="Bundle file" @change="file = ($event.target as HTMLInputElement).files?.[0] ?? null" />
        <input v-model="upload.version" class="input" placeholder="version (e.g. 2026.09.23)" aria-label="Version" required pattern="[A-Za-z0-9._+-]+" />
        <input v-model="upload.board" class="input" placeholder="target board revision (e.g. rev-c)" aria-label="Board revision" required />
        <div class="row">
          <input v-model="upload.sha" class="input" placeholder="SHA-256" aria-label="SHA-256" required pattern="[0-9a-fA-F]{64}" />
          <button class="btn btn-outline btn-sm" type="button" :disabled="busy || !file" @click="computeSha">Compute</button>
        </div>
        <div><button class="btn btn-primary" :disabled="busy || !file" type="submit">Upload</button></div>
      </form>
    </WcCard>

    <WcCard title="Device tags" subtitle="Tags group devices for rollouts (comma-separated).">
      <form class="row" @submit.prevent="saveTags">
        <input v-model="tagsText" class="input" placeholder="canary, lab" aria-label="Tags" />
        <button class="btn btn-outline btn-sm" type="submit">Save</button>
      </form>
    </WcCard>

    <WcCallout kind="info">
      The device re-verifies the checksum and the SWUpdate signature, refuses downgrades, and
      confirms the new slot only after its boot health check passes; otherwise the firmware falls
      back to the previous slot.
    </WcCallout>
  </div>
</template>
