type VideoId = string | number

type VideoSeed = {
  id?: VideoId
  [key: string]: unknown
}

const MAX_SEEDS = 20
const playbackSeeds = new Map<string, VideoSeed>()

const normalizeVideoId = (videoId: VideoId | null | undefined) => String(videoId ?? '').trim()

const cloneSeed = <T extends VideoSeed | null>(seed: T): T => {
  if (!seed || typeof seed !== 'object') {
    return seed
  }

  return { ...seed } as T
}

const trimSeeds = () => {
  while (playbackSeeds.size > MAX_SEEDS) {
    const oldestKey = playbackSeeds.keys().next().value
    if (!oldestKey) {
      return
    }
    playbackSeeds.delete(oldestKey)
  }
}

export const rememberVideoPlaybackSeed = (video: VideoSeed | null | undefined) => {
  const key = normalizeVideoId(video?.id)
  if (!key) return

  playbackSeeds.set(key, cloneSeed(video))
  trimSeeds()
}

export const peekVideoPlaybackSeed = (videoId: VideoId | null | undefined) => {
  const key = normalizeVideoId(videoId)
  if (!key) return null
  return cloneSeed(playbackSeeds.get(key) || null)
}

export const consumeVideoPlaybackSeed = (videoId: VideoId | null | undefined) => {
  const key = normalizeVideoId(videoId)
  if (!key) return null

  const seed = playbackSeeds.get(key) || null
  playbackSeeds.delete(key)
  return cloneSeed(seed)
}
