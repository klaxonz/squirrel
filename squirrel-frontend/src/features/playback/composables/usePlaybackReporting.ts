import type { Ref } from 'vue'
import type { VideoId } from '@/features/playback/types/videoPlayback'
import { Logger } from '@/shared/lib/logger'

type PlaybackReportVideo = {
  id?: VideoId
  isPlaying?: boolean
  if_read?: boolean
  is_read?: boolean
  last_position?: number | null
  duration?: number | null
  progress?: number
  [key: string]: unknown
}

type SendReportOptions = {
  force?: boolean
  includeMetadata?: boolean
  retryOnFailure?: boolean
}

type SendReport = (videoId: VideoId, currentTime: number, options?: SendReportOptions) => Promise<unknown>

type QueuedReport = {
  sessionId: number
  videoId: VideoId
  currentTime: number
  options: SendReportOptions
}

export default function usePlaybackReporting(videoRef: Ref<PlaybackReportVideo | null>, sendReport: SendReport) {
  let lastVideoId: VideoId | null = null
  let lastReportedTime = 0
  let lastObservedTime = 0
  let lastCommittedTime = 0
  let reportSessionId = 0
  let queuedReport: QueuedReport | null = null
  let inFlightReport: Promise<void> | null = null

  const maybeResetForNewVideo = () => {
    const currentId = videoRef.value?.id ?? null
    if (currentId !== lastVideoId) {
      lastVideoId = currentId
      lastReportedTime = 0
      lastObservedTime = 0
      lastCommittedTime = 0
      queuedReport = null
      reportSessionId += 1
    }
  }

  const syncLocalPlaybackPosition = (currentTime = lastObservedTime) => {
    const nextTime = Number(currentTime)
    if (!videoRef.value || !Number.isFinite(nextTime) || nextTime < 0) return
    videoRef.value.last_position = nextTime
  }

  const mergeReportOptions = (
    current: SendReportOptions = {},
    incoming: SendReportOptions = {}
  ): SendReportOptions => ({
    force: current.force === true || incoming.force === true,
    includeMetadata: current.includeMetadata === true || incoming.includeMetadata === true,
    retryOnFailure: current.retryOnFailure !== false || incoming.retryOnFailure !== false,
  })

  const drainQueuedReports = async () => {
    while (queuedReport) {
      const report = queuedReport
      queuedReport = null

      try {
        const response = await sendReport(report.videoId, report.currentTime, report.options)
        if (response === false) continue
        if (report.sessionId !== reportSessionId) continue

        lastCommittedTime = Math.max(lastCommittedTime, report.currentTime)
      } catch (err) {
        Logger.warn('[usePlaybackReporting] Failed to send report', err)
      }
    }
  }

  const ensureReportDrain = () => {
    if (inFlightReport) return inFlightReport

    inFlightReport = drainQueuedReports().finally(() => {
      inFlightReport = null
      if (queuedReport) {
        void ensureReportDrain()
      }
    })

    return inFlightReport
  }

  const queueReport = (currentTime: number, options: SendReportOptions = {}) => {
    maybeResetForNewVideo()

    const videoId = videoRef.value?.id
    const nextTime = Number(currentTime)
    if (videoId == null || !Number.isFinite(nextTime) || nextTime < 0) {
      return Promise.resolve()
    }

    const nextOptions = mergeReportOptions({ retryOnFailure: true }, options)
    if (nextOptions.force !== true && nextTime <= lastCommittedTime) {
      return inFlightReport ?? Promise.resolve()
    }

    if (!queuedReport || queuedReport.sessionId !== reportSessionId || queuedReport.videoId !== videoId) {
      queuedReport = {
        sessionId: reportSessionId,
        videoId,
        currentTime: nextTime,
        options: nextOptions,
      }
    } else {
      queuedReport.currentTime = Math.max(queuedReport.currentTime, nextTime)
      queuedReport.options = mergeReportOptions(queuedReport.options, nextOptions)
    }

    return ensureReportDrain()
  }

  const flushPendingReport = (currentTime = lastObservedTime, options: SendReportOptions = {}) => {
    const nextTime = Number(currentTime)
    if (!Number.isFinite(nextTime) || nextTime < 0) {
      return Promise.resolve()
    }

    syncLocalPlaybackPosition(nextTime)
    lastReportedTime = Math.max(lastReportedTime, Math.floor(nextTime))
    return queueReport(nextTime, { force: true, ...options })
  }

  const onVideoPlay = () => {
    maybeResetForNewVideo()
    if (videoRef.value) videoRef.value.isPlaying = true
  }

  const onVideoPause = () => {
    if (videoRef.value) videoRef.value.isPlaying = false
    void flushPendingReport()
  }

  const onVideoEnded = () => {
    const duration = Number(videoRef.value?.duration) || lastObservedTime
    if (videoRef.value) {
      videoRef.value.is_read = true
    }
    void flushPendingReport(duration, { force: true })
  }

  const onVideoTimeUpdate = (currentTime: number) => {
    maybeResetForNewVideo()
    if (!videoRef.value) return
    lastObservedTime = currentTime
    if (Math.floor(currentTime) - lastReportedTime < 2) return

    lastReportedTime = Math.floor(currentTime)
    void queueReport(currentTime)
  }

  return {
    flushPendingReport,
    onVideoPlay,
    onVideoPause,
    onVideoEnded,
    onVideoTimeUpdate,
  }
}


