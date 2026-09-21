// Toast store — WebConfig-style toasts (bottom-right, dark, auto-dismiss).
import { reactive } from 'vue'

export type ToastKind = 'success' | 'error' | 'info'

export interface Toast {
  id: number
  message: string
  kind: ToastKind
}

const state = reactive<{ toasts: Toast[] }>({ toasts: [] })
let nextId = 1

export function useToasts() {
  return state
}

export function toast(message: string, kind: ToastKind = 'info', timeoutMs = 3500): void {
  const id = nextId++
  state.toasts.push({ id, message, kind })
  if (timeoutMs > 0) {
    setTimeout(() => dismiss(id), timeoutMs)
  }
}

export function dismiss(id: number): void {
  const index = state.toasts.findIndex((t) => t.id === id)
  if (index >= 0) state.toasts.splice(index, 1)
}
