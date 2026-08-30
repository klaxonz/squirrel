import { beforeEach, describe, expect, it, vi } from 'vitest'
import { request } from './request'

const axiosRequest = vi.hoisted(() => vi.fn())

vi.mock('./axios', () => ({
  default: { request: axiosRequest },
}))

describe('request response boundary', () => {
  beforeEach(() => axiosRequest.mockReset())

  it('unwraps a successful JSON envelope to its data payload', async () => {
    axiosRequest.mockResolvedValue({ status: 200, data: { code: 0, data: { id: 7 } } })

    await expect(request<{ id: number }>({ url: '/tasks', method: 'get' })).resolves.toEqual({ id: 7 })
  })

  it('rejects a failed JSON envelope as an ApiError', async () => {
    axiosRequest.mockResolvedValue({ status: 200, data: { code: 4001, msg: '任务无效' } })

    await expect(request({ url: '/tasks', method: 'post' })).rejects.toMatchObject({
      message: '任务无效',
      status: 200,
      data: { code: 4001, msg: '任务无效' },
    })
  })

  it('returns non-JSON responses raw without interpreting a code field', async () => {
    const raw = JSON.stringify({ code: 0, data: 'literal response' })
    axiosRequest.mockResolvedValue({ status: 200, data: raw })

    await expect(request<string>({ url: '/subtitles', method: 'get', responseType: 'text' })).resolves.toBe(raw)
  })
})
