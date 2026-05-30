export function getCodecFamily(codec: string | null | undefined): string | null {
  if (!codec) return null
  const normalized = String(codec).toLowerCase()
  if (normalized.includes('av01') || normalized.includes('av1')) return 'av1'
  if (normalized.includes('vp09') || normalized.includes('vp9')) return 'vp9'
  if (normalized.includes('avc1') || normalized.includes('avc') || normalized.includes('h264')) return 'avc'
  if (normalized.includes('hev1') || normalized.includes('hvc1') || normalized.includes('hevc') || normalized.includes('h265')) return 'hevc'
  if (normalized.includes('mp4a') || normalized.includes('aac')) return 'aac'
  if (normalized.includes('opus')) return 'opus'
  return normalized
}

export const CODEC_FAMILY_ORDER = ['av1', 'vp9', 'avc'] as const

export function compareCodecFamilies(left: string, right: string): number {
  const leftIndex = CODEC_FAMILY_ORDER.indexOf(left as any)
  const rightIndex = CODEC_FAMILY_ORDER.indexOf(right as any)
  const safeLeftIndex = leftIndex >= 0 ? leftIndex : CODEC_FAMILY_ORDER.length
  const safeRightIndex = rightIndex >= 0 ? rightIndex : CODEC_FAMILY_ORDER.length
  if (safeLeftIndex !== safeRightIndex) return safeLeftIndex - safeRightIndex
  return left.localeCompare(right)
}
