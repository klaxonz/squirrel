/**
 * Shaka transport bridge for googlevideo's MIT-licensed SABR adapter.
 *
 * Based on the upstream GoogleVideo Shaka example, but deliberately registers
 * only the `sabr:` scheme. The upstream example replaces Shaka's global
 * HTTP/HTTPS plugins; doing that in the desktop app would also affect other
 * providers and players.
 *
 * Upstream: https://github.com/LuanRT/GoogleVideo/tree/main/examples/sabr-shaka-example
 * License: MIT
 */

import shaka from 'shaka-player'
import {
  SabrUmpProcessor,
  type RequestFilter,
  type ResponseFilter,
  type SabrPlayerAdapter,
  type SabrRequestMetadata,
  type UmpProcessingResult,
} from 'googlevideo/sabr-streaming-adapter'
import type { SabrFormat } from 'googlevideo/shared-types'
import {
  FormatKeyUtils,
  isGoogleVideoURL,
  type CacheManager,
  type RequestMetadataManager,
} from 'googlevideo/utils'

type ShakaResponseWithRequest = shaka.extern.Response & {
  originalRequest: shaka.extern.Request
}

type AbortState = {
  canceled: boolean
  timedOut: boolean
}

type BinaryData = ArrayBuffer | ArrayBufferView<ArrayBufferLike>

const RequestType = shaka.net.NetworkingEngine.RequestType

const headersToObject = (headers: Headers): Record<string, string> => {
  const result: Record<string, string> = {}
  headers.forEach((value, key) => {
    result[key.trim()] = value
  })
  return result
}

const toArrayBuffer = (data: BinaryData): ArrayBuffer => {
  if (data instanceof ArrayBuffer) return data
  const bytes = new Uint8Array(data.buffer, data.byteOffset, data.byteLength)
  return bytes.slice().buffer as ArrayBuffer
}

const createNetworkError = (message: string, details?: unknown) => new shaka.util.Error(
  shaka.util.Error.Severity.RECOVERABLE,
  shaka.util.Error.Category.NETWORK,
  shaka.util.Error.Code.HTTP_ERROR,
  message,
  details,
)

export class SabrShakaPlayerAdapter implements SabrPlayerAdapter {
  private player: shaka.Player | null = null
  private requestMetadataManager: RequestMetadataManager | null = null
  private cacheManager: CacheManager | null = null
  private requestFilter: ((
    type: shaka.net.NetworkingEngine.RequestType,
    request: shaka.extern.Request,
    context?: shaka.extern.RequestContext,
  ) => Promise<void>) | null = null
  private responseFilter: ((
    type: shaka.net.NetworkingEngine.RequestType,
    response: shaka.extern.Response,
    context?: shaka.extern.RequestContext,
  ) => Promise<void>) | null = null
  private readonly requestTargets = new WeakMap<shaka.extern.Request, string>()
  private readonly abortControllers = new Set<AbortController>()
  private activeNetworkRequests = 0
  private readonly networkRequestWaiters: Array<() => void> = []

  initialize(
    player: shaka.Player,
    requestMetadataManager: RequestMetadataManager,
    cacheManager: CacheManager | null,
  ): void {
    this.player = player
    this.requestMetadataManager = requestMetadataManager
    this.cacheManager = cacheManager

    if (!shaka.net.HttpFetchPlugin.isSupported()) {
      throw new Error('The Fetch API is not supported in this browser')
    }

    shaka.net.NetworkingEngine.registerScheme(
      'sabr',
      this.parseRequest.bind(this),
      shaka.net.NetworkingEngine.PluginPriority.PREFERRED,
    )
  }

  private parseRequest(
    uri: string,
    request: shaka.extern.Request,
    requestType: shaka.net.NetworkingEngine.RequestType,
    progressUpdated: shaka.extern.ProgressUpdated,
    headersReceived: shaka.extern.HeadersReceived,
    config: shaka.extern.SchemePluginConfig,
  ): shaka.extern.IAbortableOperation<shaka.extern.Response> {
    const targetUrl = this.requestTargets.get(request)
    if (!targetUrl) {
      return shaka.util.AbortableOperation.failed(
        createNetworkError('SABR request was not initialized', { uri }),
      )
    }

    const headers = new Headers()
    for (const [key, value] of Object.entries(request.headers)) {
      headers.append(key, value)
    }

    const controller = new AbortController()
    const abortState: AbortState = { canceled: false, timedOut: false }
    this.abortControllers.add(controller)
    const timeoutMs = request.retryParameters.timeout
    const timeoutId = timeoutMs > 0
      ? window.setTimeout(() => {
        abortState.timedOut = true
        controller.abort()
      }, timeoutMs)
      : null

    const promise = this.request(
      targetUrl,
      request,
      requestType,
      {
        body: request.body ? toArrayBuffer(request.body) : undefined,
        headers,
        method: request.method,
        signal: controller.signal,
        credentials: request.allowCrossSiteCredentials ? 'include' : undefined,
      },
      controller,
      abortState,
      progressUpdated,
      headersReceived,
      config.minBytesForProgressEvents || 0,
    ).finally(() => {
      if (timeoutId !== null) window.clearTimeout(timeoutId)
      this.abortControllers.delete(controller)
      this.requestTargets.delete(request)
    })

    return new shaka.util.AbortableOperation(promise, () => {
      abortState.canceled = true
      controller.abort()
      return Promise.resolve()
    })
  }

  private async request(
    uri: string,
    request: shaka.extern.Request,
    requestType: shaka.net.NetworkingEngine.RequestType,
    init: RequestInit,
    controller: AbortController,
    abortState: AbortState,
    progressUpdated: shaka.extern.ProgressUpdated,
    headersReceived: shaka.extern.HeadersReceived,
    minBytes: number,
  ): Promise<shaka.extern.Response> {
    let releaseNetworkSlot: (() => void) | null = null
    try {
      const metadata = this.requestMetadataManager?.getRequestMetadata(uri)
      if (metadata) {
        const cached = this.readCachedResponse(
          metadata,
          uri,
          request,
          requestType,
          progressUpdated,
          headersReceived,
        )
        if (cached) return cached
      }

      // Shaka asks for audio/video init and index ranges together. Sending all
      // four SABR calls at once makes YouTube respond with a multi-second
      // NextRequestPolicy backoff. Two in flight preserves A/V parallelism
      // without tripping that server-side startup throttle.
      releaseNetworkSlot = await this.acquireNetworkSlot()
      const response = await fetch(uri, init)
      const responseHeaders = headersToObject(response.headers)
      headersReceived(responseHeaders)

      if (
        metadata
        && init.method !== 'HEAD'
        && response.ok
        && String(response.headers.get('content-type') || '').includes('application/vnd.yt-ump')
      ) {
        return await this.processUmpResponse(
          response,
          metadata,
          uri,
          request,
          requestType,
          progressUpdated,
          controller,
          minBytes,
        )
      }

      const startedAt = performance.now()
      const data = await response.arrayBuffer()
      progressUpdated(performance.now() - startedAt, data.byteLength, 0)
      return this.createShakaResponse(response, uri, request, requestType, data)
    } catch (error) {
      if (abortState.canceled) {
        throw new shaka.util.Error(
          shaka.util.Error.Severity.RECOVERABLE,
          shaka.util.Error.Category.NETWORK,
          shaka.util.Error.Code.OPERATION_ABORTED,
          uri,
          requestType,
        )
      }
      if (abortState.timedOut) {
        throw new shaka.util.Error(
          shaka.util.Error.Severity.RECOVERABLE,
          shaka.util.Error.Category.NETWORK,
          shaka.util.Error.Code.TIMEOUT,
          uri,
          requestType,
        )
      }
      if (error instanceof shaka.util.Error) throw error
      throw createNetworkError(uri, error)
    } finally {
      releaseNetworkSlot?.()
    }
  }

  private async acquireNetworkSlot(): Promise<() => void> {
    if (this.activeNetworkRequests >= 2) {
      await new Promise<void>((resolve) => this.networkRequestWaiters.push(resolve))
    }
    this.activeNetworkRequests += 1

    let released = false
    return () => {
      if (released) return
      released = true
      this.activeNetworkRequests = Math.max(0, this.activeNetworkRequests - 1)
      this.networkRequestWaiters.shift()?.()
    }
  }

  private readCachedResponse(
    metadata: SabrRequestMetadata,
    uri: string,
    request: shaka.extern.Request,
    requestType: shaka.net.NetworkingEngine.RequestType,
    progressUpdated: shaka.extern.ProgressUpdated,
    headersReceived: shaka.extern.HeadersReceived,
  ): shaka.extern.Response | null {
    if (!metadata.byteRange || !this.cacheManager) return null

    const key = FormatKeyUtils.createSegmentCacheKeyFromMetadata(metadata)
    let bytes = metadata.isInit
      ? this.cacheManager.getInitSegment(key)
      : this.cacheManager.getSegment(key)
    if (!bytes) return null

    if (metadata.isInit) {
      bytes = bytes.slice(metadata.byteRange.start, metadata.byteRange.end + 1)
    }

    const headers = {
      'content-type': metadata.format?.mimeType?.split(';')[0] || '',
      'content-length': String(bytes.byteLength),
      'x-shaka-from-cache': 'true',
    }
    headersReceived(headers)
    progressUpdated(0, bytes.byteLength, 0)
    return this.makeResponse(headers, bytes, 200, uri, uri, request, requestType)
  }

  private async processUmpResponse(
    response: Response,
    metadata: SabrRequestMetadata,
    uri: string,
    request: shaka.extern.Request,
    requestType: shaka.net.NetworkingEngine.RequestType,
    progressUpdated: shaka.extern.ProgressUpdated,
    controller: AbortController,
    minBytes: number,
  ): Promise<shaka.extern.Response> {
    const processor = new SabrUmpProcessor(metadata, this.cacheManager || undefined)
    let lastProgressAt = performance.now()
    let loaded = 0
    let lastLoaded = 0

    const validate = (result: UmpProcessingResult) => {
      const protectedStreamFailed = metadata.streamInfo?.streamProtectionStatus?.status === 3
      if (
        !result.data
        && (metadata.error || protectedStreamFailed)
        && !metadata.streamInfo?.sabrContextUpdate
      ) {
        throw createNetworkError('SABR server streaming error', metadata)
      }
    }
    const mayReturnEmpty = () => Boolean(
      metadata.isSABR
      && (
        metadata.streamInfo?.redirect
        || metadata.streamInfo?.sabrContextUpdate
        || metadata.streamInfo?.reloadPlaybackContext
      )
    )

    if (!response.body) {
      const data = new Uint8Array(await response.arrayBuffer())
      progressUpdated(performance.now() - lastProgressAt, data.byteLength, 0)
      const result = await processor.processChunk(data)
      if (result) {
        validate(result)
        return this.createShakaResponse(response, uri, request, requestType, result.data)
      }
      if (mayReturnEmpty()) {
        return this.createShakaResponse(response, uri, request, requestType)
      }
      throw createNetworkError('Empty SABR response without redirect information', metadata)
    }

    const reader = response.body.getReader()
    while (!controller.signal.aborted) {
      const { value, done } = await reader.read()
      if (done) {
        if (mayReturnEmpty()) {
          return this.createShakaResponse(response, uri, request, requestType)
        }
        throw createNetworkError('Empty SABR response without redirect information', metadata)
      }

      const result = await processor.processChunk(value)
      const segmentInfo = processor.getSegmentInfo()
      if (segmentInfo) {
        loaded += segmentInfo.lastChunkSize || 0
        segmentInfo.lastChunkSize = 0
      }

      const now = performance.now()
      const chunkSize = loaded - lastLoaded
      if ((now - lastProgressAt > 100 && chunkSize >= minBytes) || result) {
        if (result) validate(result)
        const contentLength = Number(segmentInfo?.mediaHeader.contentLength || 0)
        progressUpdated(
          now - lastProgressAt,
          chunkSize,
          result || !contentLength ? 0 : Math.max(0, contentLength - loaded),
        )
        lastLoaded = loaded
        lastProgressAt = now
      }

      if (result) {
        await reader.cancel().catch(() => undefined)
        return this.createShakaResponse(response, uri, request, requestType, result.data)
      }
    }

    throw createNetworkError('SABR stream was aborted before producing a segment', metadata)
  }

  private createShakaResponse(
    response: Response,
    uri: string,
    request: shaka.extern.Request,
    requestType: shaka.net.NetworkingEngine.RequestType,
    data?: BinaryData,
  ): shaka.extern.Response {
    return this.makeResponse(
      headersToObject(response.headers),
      data || new ArrayBuffer(0),
      response.status,
      uri,
      response.url,
      request,
      requestType,
    )
  }

  private makeResponse(
    headers: Record<string, string>,
    data: BinaryData,
    status: number,
    uri: string,
    responseUrl: string,
    request: shaka.extern.Request,
    requestType: shaka.net.NetworkingEngine.RequestType,
  ): ShakaResponseWithRequest {
    if (status < 200 || status > 299 || status === 202) {
      const severity = status === 401 || status === 403
        ? shaka.util.Error.Severity.CRITICAL
        : shaka.util.Error.Severity.RECOVERABLE
      throw new shaka.util.Error(
        severity,
        shaka.util.Error.Category.NETWORK,
        shaka.util.Error.Code.BAD_HTTP_STATUS,
        uri,
        status,
        headers,
        requestType,
        responseUrl || uri,
      )
    }

    return {
      uri: responseUrl || uri,
      originalUri: uri,
      data: toArrayBuffer(data),
      status,
      headers,
      originalRequest: request,
      fromCache: headers['x-shaka-from-cache'] === 'true',
    }
  }

  getPlayerTime(): number {
    return this.requirePlayer().getMediaElement()?.currentTime || 0
  }

  getPlaybackRate(): number {
    return this.requirePlayer().getPlaybackRate()
  }

  getBandwidthEstimate(): number {
    return this.requirePlayer().getStats().estimatedBandwidth
  }

  getActiveTrackFormats(
    activeFormat: SabrFormat,
    sabrFormats: SabrFormat[],
  ): { videoFormat?: SabrFormat; audioFormat?: SabrFormat } {
    const player = this.requirePlayer()
    const activeFormatId = FormatKeyUtils.getUniqueFormatId(activeFormat)
    const variant = player.getVariantTracks().find((track) =>
      activeFormatId === (activeFormat.width ? track.originalVideoId : track.originalAudioId),
    )
    if (!variant) return {}

    const byId = new Map(sabrFormats.map((format) => [
      FormatKeyUtils.getUniqueFormatId(format),
      format,
    ]))
    return {
      videoFormat: variant.originalVideoId ? byId.get(variant.originalVideoId) : undefined,
      audioFormat: variant.originalAudioId ? byId.get(variant.originalAudioId) : undefined,
    }
  }

  registerRequestInterceptor(interceptor: RequestFilter): void {
    const player = this.requirePlayer()
    const networkingEngine = player.getNetworkingEngine()
    if (!networkingEngine) return

    this.requestFilter = async (type, request, context) => {
      if (type !== RequestType.SEGMENT || !request.uris?.[0] || !isGoogleVideoURL(request.uris[0])) {
        return
      }

      const originalUrl = request.uris[0]
      const modified = await interceptor({
        headers: request.headers,
        url: originalUrl,
        method: request.method,
        segment: {
          getStartTime: () => context?.segment?.getStartTime() ?? null,
          isInit: () => !context?.segment,
        },
        body: request.body,
      })
      if (!modified) return

      request.method = modified.method || request.method
      request.headers = modified.headers || request.headers
      request.body = modified.body ?? request.body

      if (originalUrl.startsWith('sabr://')) {
        // Preserve the custom scheme so Shaka dispatches to parseRequest, but
        // retain the real URL (with SABR request number) out-of-band.
        this.requestTargets.set(request, modified.url)
      } else {
        request.uris = modified.url ? [modified.url] : request.uris
      }
    }
    networkingEngine.registerRequestFilter(this.requestFilter)
  }

  registerResponseInterceptor(interceptor: ResponseFilter): void {
    const player = this.requirePlayer()
    const networkingEngine = player.getNetworkingEngine()
    if (!networkingEngine) return

    this.responseFilter = async (type, response, context) => {
      if (type !== RequestType.SEGMENT || !response.uri || !isGoogleVideoURL(response.uri)) return

      const originalRequest = (response as ShakaResponseWithRequest).originalRequest
      const modified = await interceptor({
        // response.uri is the real server URL and carries rn=, which is the
        // metadata key used by googlevideo's response interceptor.
        url: response.uri,
        method: originalRequest?.method || 'POST',
        headers: response.headers,
        data: response.data,
        makeRequest: async (url, headers) => {
          const retryParameters = player.getConfiguration().streaming.retryParameters
          const nextRequest = shaka.net.NetworkingEngine.makeRequest([url], retryParameters)
          Object.assign(nextRequest.headers, headers)
          const operation = networkingEngine.request(type, nextRequest, context)
          const nextResponse = await operation.promise
          return {
            url: nextResponse.uri,
            method: nextResponse.originalRequest?.method || 'POST',
            headers: nextResponse.headers,
            data: nextResponse.data,
          }
        },
      })

      if (modified) {
        response.data = modified.data ?? response.data
        Object.assign(response.headers, modified.headers)
      }
    }
    networkingEngine.registerResponseFilter(this.responseFilter)
  }

  dispose(): void {
    for (const controller of this.abortControllers) controller.abort()
    this.abortControllers.clear()
    while (this.networkRequestWaiters.length > 0) {
      this.networkRequestWaiters.shift()?.()
    }
    this.activeNetworkRequests = 0

    const networkingEngine = this.player?.getNetworkingEngine()
    if (networkingEngine && this.requestFilter) {
      networkingEngine.unregisterRequestFilter(this.requestFilter)
    }
    if (networkingEngine && this.responseFilter) {
      networkingEngine.unregisterResponseFilter(this.responseFilter)
    }
    shaka.net.NetworkingEngine.unregisterScheme('sabr')

    this.requestFilter = null
    this.responseFilter = null
    this.requestMetadataManager = null
    this.cacheManager = null
    this.player = null
  }

  private requirePlayer(): shaka.Player {
    if (!this.player) throw new Error('SABR Shaka adapter is not initialized')
    return this.player
  }
}

export default SabrShakaPlayerAdapter
