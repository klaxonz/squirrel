import { describe, expect, it } from 'vitest'
import { errorMessage } from './errorMessage'

describe('errorMessage', () => {
  it('removes Electron IPC internals from user-facing messages', () => {
    const error = new Error(
      "Error invoking remote method 'desktop:music': DesktopMusicServiceError: 请重新登录音乐账号后再播放",
    )

    expect(errorMessage(error, '播放失败')).toBe('请重新登录音乐账号后再播放')
  })

  it('keeps ordinary application errors and fallback behavior', () => {
    expect(errorMessage(new Error('加载失败'), '默认错误')).toBe('加载失败')
    expect(errorMessage({ message: 'not an Error' }, '默认错误')).toBe('默认错误')
  })
})
