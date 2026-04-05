import { createHash } from 'node:crypto';

import { Innertube, Platform, UniversalCache } from 'youtubei.js/web';

import { SessionManager } from './build/session_manager.js';

const AUTHENTICATED_PLAYBACK_CLIENTS = ['TV', 'MWEB', 'WEB'];
const AUTHENTICATED_FULL_CLIENTS = ['TV', 'MWEB', 'WEB'];
const ANONYMOUS_CLIENTS = ['ANDROID'];
const YOUTUBE_WEB_ORIGIN = 'https://www.youtube.com';
const SESSION_CACHE = new Map();

Platform.shim.eval = async (data, env) => {
  const source = `${data.output}\nreturn process(${JSON.stringify(env.n || '')}, ${JSON.stringify(env.sp || '')}, ${JSON.stringify(env.sig || '')});`;
  return new Function(source)();
};

function normalizeRange(range) {
  if (!range || typeof range !== 'object') return null;
  const start = range.start ?? range.startMs ?? range.begin;
  const end = range.end ?? range.endMs ?? range.finish;
  if (start === undefined || end === undefined) return null;
  return { start, end };
}

async function resolveFormatUrl(format, player) {
  if (typeof format?.decipher === 'function' && player) {
    try {
      return await format.decipher(player);
    } catch {
      return format.url ?? null;
    }
  }
  return format?.url ?? null;
}

async function normalizeFormat(format, player) {
  return {
    itag: format.itag ?? null,
    mime_type: format.mime_type ?? null,
    quality_label: format.quality_label ?? format.quality ?? null,
    bitrate: format.bitrate ?? null,
    width: format.width ?? null,
    height: format.height ?? null,
    audio_quality: format.audio_quality ?? null,
    audio_sample_rate: format.audio_sample_rate ?? null,
    audio_channels: format.audio_channels ?? null,
    init_range: normalizeRange(format.init_range ?? format.initRange),
    index_range: normalizeRange(format.index_range ?? format.indexRange),
    content_length: format.content_length ?? null,
    language: format.language ?? null,
    has_audio: Boolean(format.has_audio),
    has_video: Boolean(format.has_video),
    url: await resolveFormatUrl(format, player),
  };
}

function buildFormatMetadata(format) {
  return {
    itag: format.itag ?? null,
    mime_type: format.mime_type ?? null,
    quality_label: format.quality_label ?? format.quality ?? null,
    bitrate: format.bitrate ?? null,
    width: format.width ?? null,
    height: format.height ?? null,
    audio_quality: format.audio_quality ?? null,
    audio_sample_rate: format.audio_sample_rate ?? null,
    audio_channels: format.audio_channels ?? null,
    init_range: normalizeRange(format.init_range ?? format.initRange),
    index_range: normalizeRange(format.index_range ?? format.indexRange),
    content_length: format.content_length ?? null,
    language: format.language ?? null,
    has_audio: Boolean(format.has_audio),
    has_video: Boolean(format.has_video),
    url: format.url ?? null,
  };
}

function sortPlaybackCandidates(formats, predicate) {
  return formats
    .map((format, index) => ({ format, index }))
    .filter(({ format }) => predicate(format))
    .sort((left, right) => {
      const leftScore = [(left.format.height ?? 0), (left.format.bitrate ?? 0)];
      const rightScore = [(right.format.height ?? 0), (right.format.bitrate ?? 0)];
      if (rightScore[0] !== leftScore[0]) {
        return rightScore[0] - leftScore[0];
      }
      return rightScore[1] - leftScore[1];
    })
    .map(({ index }) => index);
}

async function resolveBestPlayableUrl(indexes, rawFormats, formats, player) {
  for (const index of indexes) {
    if (formats[index]?.url) {
      return index;
    }
    const resolvedUrl = await resolveFormatUrl(rawFormats[index], player);
    if (!resolvedUrl) {
      continue;
    }
    formats[index].url = resolvedUrl;
    return index;
  }
  return null;
}

async function collectFormats(info, player, resolutionMode = 'playback') {
  const streamingData = info.streaming_data || {};
  const rawFormats = [
    ...(streamingData.formats || []),
    ...(streamingData.adaptive_formats || []),
  ];
  if (resolutionMode === 'all') {
    return Promise.all(rawFormats.map((format) => normalizeFormat(format, player)));
  }

  const formats = rawFormats.map((format) => buildFormatMetadata(format));
  const progressiveIndexes = sortPlaybackCandidates(formats, (format) => format.has_audio && format.has_video);
  const videoOnlyIndexes = sortPlaybackCandidates(formats, (format) => format.has_video && !format.has_audio);
  const audioOnlyIndexes = sortPlaybackCandidates(formats, (format) => format.has_audio && !format.has_video);

  await Promise.all([
    resolveBestPlayableUrl(progressiveIndexes, rawFormats, formats, player),
    resolveBestPlayableUrl(videoOnlyIndexes, rawFormats, formats, player),
    resolveBestPlayableUrl(audioOnlyIndexes, rawFormats, formats, player),
  ]);

  return formats;
}

function isPlayableFormatSet(formats) {
  const playable = formats.filter((item) => Boolean(item.url));
  const hasMuxed = playable.some((item) => item.has_audio && item.has_video);
  const hasVideoOnly = playable.some((item) => item.has_video && !item.has_audio);
  const hasAudioOnly = playable.some((item) => item.has_audio && !item.has_video);
  return playable.length > 0 && (hasMuxed || (hasVideoOnly && hasAudioOnly));
}

function buildYoutubeFetch() {
  return async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input?.url || String(input);
    const inheritedHeaders =
      init.headers || (typeof input !== 'string' ? input.headers : undefined) || {};
    const headers = new Headers(inheritedHeaders);

    if (url.startsWith('https://www.youtube.com/youtubei/')) {
      headers.set('Referer', `${YOUTUBE_WEB_ORIGIN}/`);
      headers.set('Origin', YOUTUBE_WEB_ORIGIN);
      headers.set('Sec-Fetch-Site', 'same-origin');
      headers.set('Sec-Fetch-Mode', 'same-origin');
      headers.set('X-Youtube-Bootstrap-Logged-In', 'false');
    }

    return fetch(input, { ...init, headers });
  };
}

function sessionCacheKey(cookie) {
  if (!cookie) {
    return 'anon';
  }
  return `auth:${createHash('sha1').update(cookie).digest('hex')}`;
}

async function createRuntime(cookie) {
  const yt = await Innertube.create({
    cache: new UniversalCache(true),
    generate_session_locally: !cookie,
    retrieve_player: true,
    client_type: cookie ? 'MWEB' : 'ANDROID',
    fetch: buildYoutubeFetch(),
    ...(cookie ? { cookie } : {}),
  });

  return {
    yt,
    sessionManager: cookie ? new SessionManager(false, {}) : null,
  };
}

async function getRuntime(cookie) {
  const key = sessionCacheKey(cookie);
  let runtime = SESSION_CACHE.get(key);
  if (runtime) {
    return runtime;
  }

  runtime = await createRuntime(cookie);
  SESSION_CACHE.set(key, runtime);
  return runtime;
}

async function buildPoToken(videoId, runtime, attempts) {
  if (!runtime.sessionManager) {
    return null;
  }

  try {
    const tokenData = await runtime.sessionManager.generatePoToken(
      videoId,
      '',
      true,
      undefined,
      false,
      undefined,
      runtime.yt.session.context,
    );
    if (runtime.yt.session.player) {
      runtime.yt.session.player.po_token = tokenData.poToken;
    }
    return tokenData.poToken;
  } catch (error) {
    attempts.push({
      client: 'MWEB',
      po_token_error: error?.message || String(error),
    });
    return null;
  }
}

export async function prewarmYoutubeiRuntime(cookie = '') {
  await getRuntime(cookie);
  return {
    status: 'ok',
    prewarmed: true,
  };
}

export async function resolveYoutubeiPayload(payload) {
  const action = String(payload?.action || 'resolve');
  const cookie = typeof payload?.cookie === 'string' ? payload.cookie.trim() : '';

  if (action === 'prewarm') {
    return prewarmYoutubeiRuntime(cookie);
  }

  const videoId = String(payload?.video_id || '');
  if (!videoId) {
    throw new Error('video_id is required');
  }
  const resolutionMode = String(payload?.resolution_mode || 'playback').trim().toLowerCase() === 'all'
    ? 'all'
    : 'playback';
  const includeDebugTimings = Boolean(payload?.debug_timings);
  const timings = {};

  const requestedClients = Array.isArray(payload?.clients)
    ? payload.clients.map((item) => String(item || '').trim().toUpperCase()).filter(Boolean)
    : [];

  const clients = requestedClients.length
    ? requestedClients
    : (cookie
      ? (resolutionMode === 'all' ? AUTHENTICATED_FULL_CLIENTS : AUTHENTICATED_PLAYBACK_CLIENTS)
      : ANONYMOUS_CLIENTS);
  const attempts = [];
  const runtimeStart = performance.now();
  const runtime = await getRuntime(cookie);
  timings.get_runtime_ms = Number((performance.now() - runtimeStart).toFixed(1));
  let contentPoToken;

  for (const client of clients) {
    try {
      let requestOptions = { client };
      if (client === 'MWEB') {
        if (contentPoToken === undefined) {
          const poTokenStart = performance.now();
          contentPoToken = await buildPoToken(videoId, runtime, attempts);
          timings.build_po_token_ms = Number((performance.now() - poTokenStart).toFixed(1));
        }
        if (contentPoToken) {
          requestOptions = { client, po_token: contentPoToken };
        }
      }

      const infoStart = performance.now();
      const info = await runtime.yt.getBasicInfo(videoId, requestOptions);
      const infoMs = Number((performance.now() - infoStart).toFixed(1));
      const formatsStart = performance.now();
      const formats = await collectFormats(info, runtime.yt.session.player, resolutionMode);
      const formatsMs = Number((performance.now() - formatsStart).toFixed(1));
      const playabilityStatus = info.playability_status?.status || null;
      attempts.push({
        client,
        playability_status: playabilityStatus,
        format_count: formats.length,
        playable: isPlayableFormatSet(formats),
        get_basic_info_ms: infoMs,
        collect_formats_ms: formatsMs,
      });

      if (!isPlayableFormatSet(formats)) {
        continue;
      }

      const response = {
        status: 'ok',
        client,
        playability_status: playabilityStatus,
        formats,
      };
      if (includeDebugTimings) {
        response.timings = {
          ...timings,
          get_basic_info_ms: infoMs,
          collect_formats_ms: formatsMs,
        };
      }
      return response;
    } catch (error) {
      attempts.push({
        client,
        error: error?.message || String(error),
      });
    }
  }

  const errorResponse = {
    status: 'error',
    error: {
      type: 'PlaybackResolverError',
      message: 'youtubei worker did not return a complete format set',
    },
    attempts,
  };
  if (includeDebugTimings) {
    errorResponse.timings = timings;
  }
  return errorResponse;
}
