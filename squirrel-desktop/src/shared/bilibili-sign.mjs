import { createHash } from 'node:crypto'

const WBI_MIXIN_KEY_ENC_TAB = [
  46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
  33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
  61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
  36, 20, 34, 44, 52,
]

const getMixinKey = (value) => {
  return WBI_MIXIN_KEY_ENC_TAB
    .map((index) => value[index] || '')
    .join('')
    .slice(0, 32)
}

export const signBilibiliWbiParams = (params, { imgKey, subKey }) => {
  if (!imgKey || !subKey) throw new Error('Bilibili WBI keys are missing')

  const mixinKey = getMixinKey(`${imgKey}${subKey}`)
  const signedParams = {
    ...params,
    wts: String(Math.round(Date.now() / 1000)),
  }
  const sortedEntries = Object.entries(signedParams)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => [
      key,
      String(value).replace(/[!'()*]/g, ''),
    ])
  const query = new URLSearchParams(sortedEntries).toString()
  const wRid = createHash('md5').update(`${query}${mixinKey}`).digest('hex')
  return {
    ...Object.fromEntries(sortedEntries),
    w_rid: wRid,
  }
}
