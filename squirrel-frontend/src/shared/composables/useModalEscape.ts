/**
 * 模态栈：让全局 Esc 拦截器（`AppLayout.vue: handleKeydown`）知道当前顶层
 * 是否有模态/dialog/抽屉在打开。
 *
 * 之前 Esc 拦截用 `target.tagName === 'BODY' | 'MAIN' | 'DIV'` 这种粗粒度
 * 判断，会被设置行 / 歌单卡片等焦点元素误触发 goBack（UI-008）。
 *
 * 用法：
 *   - 任何 dialog / sheet / popover / drawer 在 mount 时调用
 *     `useModalEscape(openRef)`（最简），或者
 *   - 手动 push 一个 `ModalEscapeToken`（需要更细控制时）。
 *
 * `AppLayout` 的 Esc 处理只在栈顶非空时拦截（让 modal 自己的 dismiss 逻辑生效），
 * 栈空时才把 Esc 透传给 `useNavigationHistory.goBack()`。
 */
import { onBeforeUnmount, ref, watch, type Ref } from 'vue'

interface ModalEscapeApi {
  /** 注册一个 token；返回反注册函数。 */
  push(): () => void
  /** 当前是否至少有一个 modal 打开。 */
  hasOpen(): boolean
}

const stack = ref(0)
const api: ModalEscapeApi = {
  push: () => {
    stack.value += 1
    let released = false
    return () => {
      if (released) return
      released = true
      stack.value = Math.max(0, stack.value - 1)
    }
  },
  hasOpen: () => stack.value > 0,
}

export function provideModalEscape(): ModalEscapeApi {
  // 单一全局栈；调用多次仍返回同一实例（不同 layout 共用同一计数）。
  return api
}

export function useModalEscapeApi(): ModalEscapeApi {
  return api
}

/**
 * 把响应式 `open` ref 直接接进模态栈。`open` 变 true 时 push，
 * 变 false / 组件 unmount 时 pop（幂等）。
 */
export function useModalEscape(open: Ref<boolean>): void {
  let release: (() => void) | null = null
  watch(
    open,
    (next) => {
      if (next && !release) {
        release = api.push()
      } else if (!next && release) {
        release()
        release = null
      }
    },
    { immediate: true },
  )
  onBeforeUnmount(() => {
    if (release) {
      release()
      release = null
    }
  })
}