import { createHash } from 'node:crypto';
import { mkdirSync } from 'node:fs';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { tmpdir } from 'node:os';

// Electron main is Node — use the node platform entry so UniversalCache is
// file-backed (FreeTube's PlayerCache equivalent). youtubei.js/web uses
// IndexedDB, which is unavailable in the main process and silently disables
// player script caching; that forces flaky decipher / "No valid URL" paths.
import { Constants, Innertube, Platform, UniversalCache } from 'youtubei.js';
import { buildSabrFormat } from 'googlevideo/utils';

import { youtubeOAuthStateFilePath } from '../../../constants.mjs';
import { SessionManager } from './build/session_manager.js';

// Official youtubei.js playback path:
//   remote WEB session (generate_session_locally: false) → MWEB player + poToken → toDash
//   → SABR + Shaka (primary), regular DASH + Shaka (fallback)
//
// Measured (youtubei.js 17.x, Electron main / node entry):
//   - FreeTube watch path boots WEB with *remote* session + retrieve_innertube_config.
//     Locally generated sessions (especially ANDROID bootstrap) make MWEB return
//     LOGIN_REQUIRED / empty streaming_data intermittently → progressive 360p collapse.
//   - MWEB: full ladder on a healthy remote session; distant byte ranges require
//     the video-bound poToken even when initial media bytes are accepted.
//   - IOS: clear adaptive URLs can start without pot, but long seeks 403 because
//     the generated token is not valid for IOS media URLs.
//   - ANDROID/WEB player clients: often SABR / "No valid URL to decipher" without pot
// OAuth WEB/TV is auth-gate only — not the primary streaming session.
//
// Order is success-rate order for toDash, not "feature completeness".
const OFFICIAL_PLAYBACK_CLIENTS = ['MWEB'];
// Last-resort clients (often progressive-only or SABR without cipher URLs).
const OFFICIAL_FALLBACK_CLIENTS = ['ANDROID', 'WEB'];
// OAuth-only clients used when anonymous hits LOGIN_REQUIRED / bot gate.
const AUTH_GATE_PLAYBACK_CLIENTS = ['TV', 'WEB'];
const CAPTIONS_ANONYMOUS_CLIENTS = ['ANDROID', 'WEB', 'MWEB'];
const CAPTIONS_AUTHENTICATED_CLIENTS = ['WEB', 'TV', 'MWEB'];
const YOUTUBE_WEB_ORIGIN = 'https://www.youtube.com';
const YOUTUBE_TV_ACTIVATION_URL = 'https://www.youtube.com/activate';
// Cap how many times we drop a poisoned SESSION_CACHE entry and rebuild.
const MAX_PLAYBACK_SESSION_REBUILDS = 1;

/** File-backed player / session cache (survives restarts; avoids IndexedDB). */
function resolvePlayerCacheDirectory() {
  const fromEnv = String(process.env.YOUTUBE_PLAYER_CACHE_DIR || '').trim();
  if (fromEnv) return fromEnv;
  const oauthFile = youtubeOAuthStateFilePath;
  if (oauthFile) {
    return join(dirname(oauthFile), 'youtubei-player-cache');
  }
  return join(tmpdir(), 'squirrel-desktop-youtubei-cache');
}

function createPlayerCache(persistent = true) {
  if (!persistent) {
    return new UniversalCache(false);
  }
  const cacheDir = resolvePlayerCacheDirectory();
  try {
    mkdirSync(cacheDir, { recursive: true });
  } catch (err) {
    console.debug('[squirrel-desktop] youtubei_core: player cache mkdir failed', err?.message || err);
  }
  return new UniversalCache(true, cacheDir);
}
class LRUMap {
  #max;
  #map;

  constructor(max) {
    this.#max = max;
    this.#map = new Map();
  }

  get(key) {
    if (!this.#map.has(key)) return undefined;
    const value = this.#map.get(key);
    this.#map.delete(key);
    this.#map.set(key, value);
    return value;
  }

  set(key, value) {
    if (this.#map.has(key)) this.#map.delete(key);
    this.#map.set(key, value);
    if (this.#map.size > this.#max) {
      const first = this.#map.keys().next().value;
      this.#map.delete(first);
    }
  }

  delete(key) {
    this.#map.delete(key);
  }

  clear() {
    this.#map.clear();
  }
}

const SESSION_CACHE = new LRUMap(3);
const PLAYBACK_RUNTIME_IN_FLIGHT = new Map();
const PO_TOKEN_MINTER_WARMUPS = new WeakMap();

// ── OAuth state helpers ─────────────────────────────────────────────────────

function getOAuthStateFilePath() {
  const fromEnv = String(process.env.YOUTUBE_OAUTH_STATE_FILE || '').trim();
  if (fromEnv) return fromEnv;
  // Default to the monorepo config path so desktop OAuth works without requiring
  // the launcher to inject YOUTUBE_OAUTH_STATE_FILE.
  return youtubeOAuthStateFilePath || null;
}

function loadOAuthState() {
  const stateFile = getOAuthStateFilePath();
  if (!stateFile) return null;
  try {
    return JSON.parse(readFileSync(stateFile, 'utf-8'));
  } catch {
    console.debug('[squirrel-desktop] youtubei_core: loadOAuthState failed', stateFile);
    return null;
  }
}

function saveOAuthState(state) {
  const stateFile = getOAuthStateFilePath();
  if (!stateFile) return;
  mkdirSync(resolve(stateFile, '..'), { recursive: true });
  writeFileSync(stateFile, JSON.stringify(state, null, 2), 'utf-8');
}

/**
 * youtubei.js emits `{ credentials: OAuth2Tokens }` on auth / update-credentials.
 * Older squirrel builds sometimes re-persisted that whole event object, producing
 * `state.credentials.credentials.access_token`. OAuth2.validateTokens only accepts
 * a flat token bag (access_token + refresh_token + expiry_date).
 */
function normalizeOAuthTokens(input) {
  let tokens = input;
  for (let depth = 0; depth < 4; depth += 1) {
    if (!tokens || typeof tokens !== 'object' || Array.isArray(tokens)) {
      return null;
    }
    if (typeof tokens.access_token === 'string' && tokens.access_token) {
      if (
        typeof tokens.refresh_token === 'string'
        && tokens.refresh_token
        && tokens.expiry_date
      ) {
        return tokens;
      }
      return null;
    }
    // Event payloads and double-wrapped state files.
    if (tokens.credentials && typeof tokens.credentials === 'object') {
      tokens = tokens.credentials;
      continue;
    }
    return null;
  }
  return null;
}

function oauthTokensFromSession(yt) {
  return normalizeOAuthTokens(yt?.session?.oauth?.oauth2_tokens)
    || normalizeOAuthTokens(yt?.session?.credentials);
}

/** Read flat OAuth2 tokens from disk; rewrite the file if it was double-wrapped. */
function readStoredOAuthTokens() {
  const state = loadOAuthState();
  if (!state || state.error) {
    return null;
  }
  const tokens = normalizeOAuthTokens(state.credentials);
  if (!tokens) {
    return null;
  }
  // Heal nested on-disk shape so subsequent signIn / cache-scope reads stay flat.
  if (state.credentials !== tokens) {
    try {
      saveOAuthState({
        pending: false,
        credentials: tokens,
        ...(state.account ? { account: state.account } : {}),
      });
    } catch (err) {
      console.debug('[squirrel-desktop] youtubei_core: heal OAuth state failed', err);
    }
  }
  return tokens;
}

function extractAccountInfo(yt) {
  try {
    const account =
      yt.account?.info?.name ||
      yt.session?.account?.name ||
      yt.account?.profile?.name ||
      '';
    const email =
      yt.account?.info?.email ||
      yt.session?.account?.email ||
      yt.account?.profile?.email ||
      '';
    const avatar =
      yt.account?.info?.photo ||
      yt.session?.account?.photo ||
      yt.account?.profile?.photo ||
      '';
    return { name: account, email, avatar };
  } catch {
    console.debug('[squirrel-desktop] youtubei_core: extractAccountInfo failed');
    return { name: '', email: '', avatar: '' };
  }
}

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
      // Adaptive formats from ANDROID/WEB/TV often have neither url nor cipher
      // ("No valid URL to decipher"). Prefer any pre-populated url, else skip.
      return format?.url ?? null;
    }
  }
  return format?.url ?? null;
}

async function decipherManifestUrl(url, player, poToken, isDash) {
  if (!url || !player || typeof player.decipher !== 'function') {
    return url ?? null;
  }

  try {
    const urlObject = new URL(url);

    if (urlObject.searchParams.size > 0) {
      if (poToken) {
        urlObject.searchParams.set('pot', poToken);
      }
      if (isDash) {
        urlObject.searchParams.set('mpd_version', '7');
      }
      return await player.decipher(urlObject.toString());
    }

    const pathPrefix = isDash ? '/api/manifest/dash' : '/api/manifest/hls_variant';
    const pathParts = urlObject.pathname
      .replace(pathPrefix, '')
      .split('/')
      .filter((part) => part.length > 0);

    urlObject.pathname = pathPrefix;

    for (let index = 0; index + 1 < pathParts.length; index += 2) {
      urlObject.searchParams.set(pathParts[index], decodeURIComponent(pathParts[index + 1]));
    }

    if (poToken) {
      urlObject.searchParams.set('pot', poToken);
    }
    if (isDash) {
      urlObject.searchParams.set('mpd_version', '7');
    }

    const deciphered = await player.decipher(urlObject.toString());
    const decipheredUrlObject = new URL(deciphered);

    for (const [key, value] of decipheredUrlObject.searchParams) {
      decipheredUrlObject.pathname += `/${key}/${encodeURIComponent(value)}`;
    }

    decipheredUrlObject.search = '';
    return decipheredUrlObject.toString();
  } catch {
    console.warn('[squirrel-desktop] youtubei_core: decipherManifestUrl failed');
    return url ?? null;
  }
}

async function normalizeStreamingData(info, player, poToken) {
  const streamingData = info?.streaming_data || {};

  const dashManifestUrl = typeof streamingData.dash_manifest_url === 'string'
    ? await decipherManifestUrl(streamingData.dash_manifest_url, player, poToken, true)
    : null;
  const hlsManifestUrl = typeof streamingData.hls_manifest_url === 'string'
    ? await decipherManifestUrl(streamingData.hls_manifest_url, player, poToken, false)
    : null;

  return {
    dash_manifest_url: dashManifestUrl,
    hls_manifest_url: hlsManifestUrl,
    expires: streamingData.expires ?? null,
  };
}

/**
 * Official youtubei.js path: VideoInfo.toDash().
 * Do not hand-build MPD XML — SegmentBase / AdaptationSet grouping from
 * youtubei.js is what dash.js needs for smooth ABR.
 */
function formatIdentity(format) {
  return [
    format?.itag ?? '',
    format?.last_modified_ms ?? format?.lastModified ?? '',
    format?.xtags ?? '',
    format?.audio_track?.id ?? format?.audioTrackId ?? '',
  ].join('|');
}

/**
 * YouTube now returns every auto-dub language in adaptive_formats. Feeding all
 * of them to Shaka creates hundreds of audio/video variants and makes it fetch
 * dozens of init/index segments before the first frame. Keep the complete
 * video ladder, but expose only creator-original, non-DRC audio in playback
 * manifests. This also makes the native audio choice deterministic.
 */
function selectPlaybackAdaptiveFormats(videoInfo) {
  const adaptiveFormats = Array.isArray(videoInfo?.streaming_data?.adaptive_formats)
    ? videoInfo.streaming_data.adaptive_formats
    : [];
  const videoFormats = adaptiveFormats.filter((format) => Boolean(format?.has_video));
  const audioFormats = adaptiveFormats.filter((format) => Boolean(format?.has_audio));
  const creatorOriginal = audioFormats.filter((format) => Boolean(format?.is_original));
  const nonDubbed = audioFormats.filter((format) => !(
    format?.is_auto_dubbed
    || format?.is_dubbed
    || format?.is_descriptive
    || format?.is_secondary
  ));
  const preferredAudio = creatorOriginal.length > 0 ? creatorOriginal : nonDubbed;
  const cleanAudio = preferredAudio.filter((format) => !(format?.is_drc || format?.is_vb));
  const selectedAudio = cleanAudio.length > 0
    ? cleanAudio
    : (preferredAudio.length > 0 ? preferredAudio : audioFormats);

  return [...videoFormats, ...selectedAudio];
}

function mediaCodecFamily(format) {
  const mimeType = String(format?.mime_type || format?.mimeType || '').toLowerCase();
  if (/codecs="?(vp09|vp9)/.test(mimeType)) return 'vp9';
  if (/codecs="?(avc1|avc|h264)/.test(mimeType)) return 'avc';
  if (/codecs="?(av01|av1)/.test(mimeType)) return 'av1';
  if (/codecs="?opus/.test(mimeType)) return 'opus';
  if (/codecs="?(mp4a|aac)/.test(mimeType)) return 'aac';
  return 'other';
}

/**
 * A DASH SegmentBase MPD makes Shaka resolve the index for every exposed
 * representation before startup. Keep ONE representation per height for SABR
 * (plus one best stream per original audio track) so first-frame work stays
 * bounded. Prefer VP9 at a given height when YouTube offers it, but NEVER lock
 * the whole ladder to a single codec family — many uploads only ship AVC/AV1
 * above 360p, and a global VP9 filter collapses SABR to a single low rung
 * while the regular DASH fallback still has 720p/1080p.
 */
function sabrVideoCodecRank(format) {
  const family = mediaCodecFamily(format);
  if (family === 'vp9') return 3;
  if (family === 'avc') return 2;
  if (family === 'av1') return 1;
  return 0;
}

function selectSabrStartupFormats(playbackFormats) {
  const videoFormats = playbackFormats.filter((format) => Boolean(format?.has_video));
  const audioFormats = playbackFormats.filter((format) => Boolean(format?.has_audio));

  const videoByHeight = new Map();
  for (const format of videoFormats) {
    const height = Number(format?.height || 0);
    if (height <= 0) continue;
    const current = videoByHeight.get(height);
    if (!current) {
      videoByHeight.set(height, format);
      continue;
    }
    const formatScore = sabrVideoCodecRank(format) * 1_000_000_000
      + Number(format?.bitrate || 0);
    const currentScore = sabrVideoCodecRank(current) * 1_000_000_000
      + Number(current?.bitrate || 0);
    if (formatScore > currentScore) {
      videoByHeight.set(height, format);
    }
  }

  const audioByTrack = new Map();
  for (const format of audioFormats) {
    const trackId = String(format?.audio_track?.id || format?.audioTrackId || 'original');
    const current = audioByTrack.get(trackId);
    const formatScore = (mediaCodecFamily(format) === 'opus' ? 1_000_000_000 : 0)
      + Number(format?.bitrate || 0);
    const currentScore = current
      ? (mediaCodecFamily(current) === 'opus' ? 1_000_000_000 : 0) + Number(current?.bitrate || 0)
      : -1;
    if (formatScore > currentScore) {
      audioByTrack.set(trackId, format);
    }
  }

  return [...videoByHeight.values(), ...audioByTrack.values()];
}

async function buildLocalDashManifest(
  manifestInfo,
  { poToken, isSabr = false, allowedFormats = null } = {},
) {
  if (!manifestInfo || typeof manifestInfo.toDash !== 'function') {
    return null;
  }

  try {
    const options = {
      manifest_options: {
        include_thumbnails: false,
        ...(isSabr ? { is_sabr: true } : {}),
      },
    };
    if (Array.isArray(allowedFormats) && allowedFormats.length > 0) {
      const allowedKeys = new Set(allowedFormats.map((format) => formatIdentity(format)));
      options.format_filter = (format) => !allowedKeys.has(formatIdentity(format));
    }
    // SABR BaseURLs use the custom sabr: scheme. Its PO token is supplied by
    // SabrStreamingAdapter instead of being appended to an HTTP media URL.
    if (poToken && !isSabr) {
      options.url_transformer = (url) => {
        try {
          const next = new URL(String(url));
          if (!next.searchParams.has('pot')) {
            next.searchParams.set('pot', poToken);
          }
          return next;
        } catch {
          return url;
        }
      };
    }
    const manifest = await manifestInfo.toDash(options);
    return typeof manifest === 'string' && manifest.trim() ? manifest : null;
  } catch (error) {
    // Non-fatal: index.mjs falls back to streaming_data.dash_manifest_url or
    // progressive. Log the real reason for diagnostics.
    console.debug(
      '[squirrel-desktop] youtubei_core: official VideoInfo.toDash failed',
      error?.message || String(error),
    );
    return null;
  }
}

async function buildSabrPlayback(videoInfo, runtime, poToken, adaptiveFormats) {
  const streamingData = videoInfo?.streaming_data;
  const serverAbrStreamingUrl = streamingData?.server_abr_streaming_url;
  const ustreamerConfig = videoInfo?.player_config?.media_common_config
    ?.media_ustreamer_request_config?.video_playback_ustreamer_config;
  const basicInfo = videoInfo?.basic_info || {};

  if (
    !poToken
    || !serverAbrStreamingUrl
    || !ustreamerConfig
    || adaptiveFormats.length === 0
    || basicInfo.is_live
    || basicInfo.is_post_live_dvr
  ) {
    return null;
  }

  const player = runtime?.yt?.session?.player;
  if (!player || typeof player.decipher !== 'function') {
    return null;
  }

  try {
    const manifest = await buildLocalDashManifest(videoInfo, {
      isSabr: true,
      allowedFormats: adaptiveFormats,
    });
    if (!manifest) return null;

    const serverAbrUrl = await player.decipher(String(serverAbrStreamingUrl));
    const client = runtime?.yt?.session?.context?.client || {};
    const clientName = Number(Constants.CLIENT_NAME_IDS[client.clientName]);
    const formats = adaptiveFormats
      .map((format) => buildSabrFormat(format))
      .filter((format) => Number.isFinite(format?.itag) && Number.isFinite(format?.bitrate));

    if (!serverAbrUrl || !Number.isFinite(clientName) || formats.length === 0) {
      return null;
    }

    return {
      manifest,
      server_abr_url: String(serverAbrUrl),
      ustreamer_config: String(ustreamerConfig),
      formats,
      client_info: {
        clientName,
        clientVersion: String(client.clientVersion || ''),
        osName: String(client.osName || ''),
        osVersion: String(client.osVersion || ''),
      },
      po_token: poToken,
    };
  } catch (error) {
    // SABR is an optimization. A complete regular DASH manifest is generated
    // alongside it, so a protocol/API change can degrade safely.
    console.debug(
      '[squirrel-desktop] youtubei_core: SABR payload build failed',
      error?.message || String(error),
    );
    return null;
  }
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

async function collectFormats(streamInfo, player, resolutionMode = 'playback') {
  const streamingData = streamInfo.streaming_data || {};
  const rawFormats = [
    ...(streamingData.formats || []),
    ...(streamingData.adaptive_formats || []),
  ];
  if (resolutionMode === 'all') {
    const results = await Promise.allSettled(rawFormats.map((format) => normalizeFormat(format, player)));
    return results.filter((r) => r.status === 'fulfilled').map((r) => r.value);
  }

  const formats = rawFormats.map((format) => buildFormatMetadata(format));
  const progressiveIndexes = sortPlaybackCandidates(formats, (format) => format.has_audio && format.has_video);
  const videoOnlyIndexes = sortPlaybackCandidates(formats, (format) => format.has_video && !format.has_audio);
  const audioOnlyIndexes = sortPlaybackCandidates(formats, (format) => format.has_audio && !format.has_video);

  await Promise.allSettled([
    resolveBestPlayableUrl(progressiveIndexes, rawFormats, formats, player),
    resolveBestPlayableUrl(videoOnlyIndexes, rawFormats, formats, player),
    resolveBestPlayableUrl(audioOnlyIndexes, rawFormats, formats, player),
  ]);

  return formats;
}

function isPlayableFormatSet(formats) {
  return scoreFormatSet(formats) > 0;
}

/**
 * Score a resolved client so we prefer official youtubei.js toDash over bare
 * adaptive URLs / progressive. ANDROID/WEB frequently return only itag 18 or
 * adaptive metadata without decipherable URLs.
 *
 * 0 = unusable
 * 1 = progressive/muxed only
 * 2 = adaptive video+audio URLs (no official MPD yet)
 * 3 = official YouTube-hosted dash_manifest_url
 * 4 = official VideoInfo.toDash() body
 * 5 = official SABR manifest + session payload (best for Electron + Shaka)
 */
function scoreFormatSet(
  formats,
  { sabrPlayback = null, localDashManifest = null, dashManifestUrl = null } = {},
) {
  if (sabrPlayback) return 5;
  if (localDashManifest) return 4;
  if (dashManifestUrl) return 3;
  const playable = (formats || []).filter((item) => Boolean(item?.url));
  if (playable.length === 0) return 0;
  const hasMuxed = playable.some((item) => item.has_audio && item.has_video);
  const hasVideoOnly = playable.some((item) => item.has_video && !item.has_audio);
  const hasAudioOnly = playable.some((item) => item.has_audio && !item.has_video);
  if (hasVideoOnly && hasAudioOnly) return 2;
  if (hasMuxed) return 1;
  return 0;
}

function pickBasicInfo(basicInfo = {}) {
  const thumbnails = Array.isArray(basicInfo.thumbnail)
    ? basicInfo.thumbnail
    : (Array.isArray(basicInfo.thumbnails) ? basicInfo.thumbnails : null);

  return {
    title: basicInfo.title || null,
    duration: basicInfo.duration ?? null,
    channel_id: basicInfo.channel_id || null,
    author: basicInfo.author || basicInfo.channel?.name || null,
    channel: basicInfo.channel?.name || basicInfo.author || null,
    channel_url: basicInfo.channel?.url || basicInfo.channel_url || null,
    uploader: basicInfo.author || basicInfo.channel?.name || null,
    uploader_url: basicInfo.channel?.url || basicInfo.channel_url || null,
    thumbnails,
    is_live: Boolean(basicInfo.is_live),
    is_live_content: Boolean(basicInfo.is_live_content),
    is_post_live_dvr: Boolean(basicInfo.is_post_live_dvr),
    is_upcoming: Boolean(basicInfo.is_upcoming),
  };
}

function normalizeLanguageCode(value) {
  return String(value || '').trim();
}

function normalizeLanguageKey(value) {
  return normalizeLanguageCode(value).toLowerCase();
}

function languageCodesMatch(candidate, requested) {
  const candidateKey = normalizeLanguageKey(candidate);
  const requestedKey = normalizeLanguageKey(requested);
  if (!candidateKey || !requestedKey) {
    return false;
  }
  return candidateKey === requestedKey ||
    candidateKey.startsWith(`${requestedKey}-`) ||
    requestedKey.startsWith(`${candidateKey}-`);
}

function normalizeCaptionTrack(track) {
  return {
    language_code: normalizeLanguageCode(track?.language_code),
    language_name: track?.name?.toString?.() || '',
    kind: track?.kind || null,
    base_url: track?.base_url || null,
    is_generated: track?.kind === 'asr',
  };
}

function normalizeTranslationLanguage(language) {
  return {
    language_code: normalizeLanguageCode(language?.language_code),
    language_name: language?.language_name?.toString?.() || '',
  };
}

function trackPreferenceScore(track) {
  return track?.kind === 'asr' ? 0 : 1;
}

function pickDefaultCaptionTrack(captions) {
  const tracks = Array.isArray(captions?.caption_tracks) ? captions.caption_tracks : [];
  if (!tracks.length) {
    return null;
  }

  const audioTracks = Array.isArray(captions?.audio_tracks) ? captions.audio_tracks : [];
  const defaultAudioTrack = audioTracks[captions?.default_audio_track_index ?? 0];
  const preferredIndexes = Array.isArray(defaultAudioTrack?.caption_track_indices)
    ? defaultAudioTrack.caption_track_indices
    : [];
  const preferredTracks = preferredIndexes
    .map((index) => tracks[index])
    .filter(Boolean)
    .sort((left, right) => trackPreferenceScore(right) - trackPreferenceScore(left));

  if (preferredTracks.length) {
    return preferredTracks[0];
  }

  const manualTrack = tracks.find((track) => track?.kind !== 'asr');
  return manualTrack || tracks[0];
}

function pickCaptionTrack(captions, requestedLanguage) {
  const tracks = Array.isArray(captions?.caption_tracks) ? captions.caption_tracks : [];
  if (!tracks.length) {
    throw new Error('No subtitles available');
  }

  const preferredDefaultTrack = pickDefaultCaptionTrack(captions);
  const normalizedRequested = normalizeLanguageCode(requestedLanguage);
  if (!normalizedRequested) {
    return {
      track: preferredDefaultTrack,
      translated: false,
      requested_language_code: '',
      resolved_language_code: normalizeLanguageCode(preferredDefaultTrack?.language_code),
      resolved_language_name: preferredDefaultTrack?.name?.toString?.() || '',
    };
  }

  const matchingTracks = tracks
    .filter((track) => languageCodesMatch(track?.language_code, normalizedRequested))
    .sort((left, right) => trackPreferenceScore(right) - trackPreferenceScore(left));
  if (matchingTracks.length) {
    const selectedTrack = matchingTracks[0];
    return {
      track: selectedTrack,
      translated: false,
      requested_language_code: normalizedRequested,
      resolved_language_code: normalizeLanguageCode(selectedTrack?.language_code),
      resolved_language_name: selectedTrack?.name?.toString?.() || '',
    };
  }

  const translationLanguages = (captions?.translation_languages || [])
    .map(normalizeTranslationLanguage)
    .filter((language) => language.language_code);
  const translatedLanguage = translationLanguages.find((language) =>
    languageCodesMatch(language.language_code, normalizedRequested)
  );
  if (!translatedLanguage) {
    throw new Error(`No subtitles available for language: ${normalizedRequested}`);
  }

  return {
    track: preferredDefaultTrack,
    translated: true,
    requested_language_code: normalizedRequested,
    resolved_language_code: translatedLanguage.language_code,
    resolved_language_name: translatedLanguage.language_name,
  };
}

function buildCaptionUrl(track, requestedLanguage, translated, format = 'srv3') {
  const baseUrl = track?.base_url;
  if (!baseUrl) {
    throw new Error('Subtitle track URL is missing');
  }

  const url = new URL(baseUrl);
  url.searchParams.set('fmt', format);
  if (translated && requestedLanguage) {
    url.searchParams.set('tlang', requestedLanguage);
  }
  return url;
}

async function fetchCaptionXml(runtime, captionUrl) {
  const headers = {
    'User-Agent': runtime.yt.session.user_agent || 'Mozilla/5.0',
  };
  if (runtime.yt.session.cookie) {
    headers.Cookie = runtime.yt.session.cookie;
  }

  const response = await runtime.yt.session.http.fetch_function(captionUrl, {
    method: 'GET',
    headers,
  });
  const content = await response.text();
  if (!response.ok) {
    throw new Error(`Caption fetch failed with status ${response.status}`);
  }
  return content;
}

async function resolveCaptionPayload(payload) {
  const videoId = String(payload?.video_id || '');
  if (!videoId) {
    throw new Error('video_id is required');
  }

  const cookie = typeof payload?.cookie === 'string' ? payload.cookie.trim() : '';
  const requestedLanguage = normalizeLanguageCode(payload?.lang);
  const requestedFormat = String(payload?.format || 'srv3').trim().toLowerCase() || 'srv3';
  const runtime = await getRuntime(cookie);
  const hasAuth = runtime.authMode === 'oauth' || runtime.authMode === 'cookie';
  const clients = hasAuth ? CAPTIONS_AUTHENTICATED_CLIENTS : CAPTIONS_ANONYMOUS_CLIENTS;
  const attempts = [];

  for (const client of clients) {
    try {
      const captionsData = await runtime.yt.getBasicInfo(videoId, { client });
      const captions = captionsData.captions;
      if (!captions?.caption_tracks?.length) {
        attempts.push({
          client,
          error: 'No subtitles available',
        });
        continue;
      }

      const selection = pickCaptionTrack(captions, requestedLanguage);
      const captionUrl = buildCaptionUrl(
        selection.track,
        selection.resolved_language_code,
        selection.translated,
        requestedFormat,
      );
      const content = await fetchCaptionXml(runtime, captionUrl);

      return {
        status: 'ok',
        client,
        video_id: videoId,
        requested_language_code: selection.requested_language_code || null,
        language_code: selection.resolved_language_code || null,
        language_name: selection.resolved_language_name || null,
        translated: selection.translated,
        kind: selection.track?.kind || null,
        format: requestedFormat,
        content,
        tracks: (captions.caption_tracks || []).map(normalizeCaptionTrack),
        translation_languages: (captions.translation_languages || []).map(normalizeTranslationLanguage),
      };
    } catch (error) {
      attempts.push({
        client,
        error: error?.message || String(error),
      });
    }
  }

  throw new Error(JSON.stringify({
    message: 'No subtitles available',
    attempts,
  }));
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

function oauthSessionCacheKey(oauthTokens) {
  if (!oauthTokens) {
    return 'oauth:none';
  }
  return `oauth:${createHash('sha1').update(JSON.stringify(oauthTokens)).digest('hex')}`;
}

function persistOAuthCredentials(credentials) {
  const tokens = normalizeOAuthTokens(credentials);
  if (!tokens) return;
  saveOAuthState({ pending: false, credentials: tokens });
}

function attachOAuthCredentialPersistence(yt) {
  if (!yt?.session?.on) return;
  try {
    // youtubei.js emits the event object `{ credentials: oauth2_tokens }`.
    // Always unwrap — persisting the event itself double-nests the file and
    // makes every later signIn throw "Invalid tokens provided".
    yt.session.on('update-credentials', (event) => {
      persistOAuthCredentials(event);
    });
    yt.session.on('auth', (event) => {
      persistOAuthCredentials(event);
    });
  } catch (err) {
    console.debug('[squirrel-desktop] youtubei_core: attachOAuthCredentialPersistence failed', err);
  }
}

/**
 * Anonymous (or cookie) Innertube runtime used for official toDash playback.
 *
 * Matches FreeTube getLocalVideoInfo session shape:
 *   withPlayer + generateSessionLocally:false + default WEB client_type
 * so MWEB player calls inherit a real YouTube visitorData / config.
 * Locally generated sessions routinely gate MWEB with LOGIN_REQUIRED.
 */
async function createPlaybackRuntime(cookie = '') {
  const normalizedCookie = typeof cookie === 'string' ? cookie.trim() : '';
  const yt = await Innertube.create({
    // FreeTube: file PlayerCache when withPlayer; we use node UniversalCache.
    cache: createPlayerCache(true),
    // FreeTube disables cross-instance session reuse to limit tracking.
    enable_session_cache: false,
    // FreeTube watch path: remote session (sw.js_data / innertube config), not
    // a locally synthesised ANDROID visitor — required for stable MWEB toDash.
    generate_session_locally: false,
    retrieve_innertube_config: true,
    retrieve_player: true,
    client_type: 'WEB',
    fetch: buildYoutubeFetch(),
    ...(normalizedCookie ? { cookie: normalizedCookie } : {}),
  });

  return {
    yt,
    // poToken minting is required for MWEB media range authorization.
    sessionManager: new SessionManager(false, {}),
    authMode: normalizedCookie ? 'cookie' : 'anonymous',
  };
}

function playbackSessionKey(cookie = '') {
  return `playback|${sessionCacheKey(cookie)}`;
}

/** Drop a cached playback runtime so the next get rebuilds a fresh session. */
function invalidatePlaybackRuntime(cookie = '') {
  const key = playbackSessionKey(cookie);
  SESSION_CACHE.delete(key);
  PLAYBACK_RUNTIME_IN_FLIGHT.delete(key);
}

/**
 * OAuth-signed runtime for TV-code account actions and LOGIN_REQUIRED gates.
 * Not used as the primary streaming session — OAuth WEB sessions do not yield
 * decipherable adaptive URLs for toDash in current youtubei.js.
 */
async function createOAuthRuntime(oauthCredentials) {
  const tokens = normalizeOAuthTokens(oauthCredentials);
  if (!tokens) {
    throw new Error('Invalid YouTube OAuth tokens');
  }
  const yt = await Innertube.create({
    cache: createPlayerCache(true),
    enable_session_cache: false,
    generate_session_locally: true,
    retrieve_player: true,
    client_type: 'WEB',
    fetch: buildYoutubeFetch(),
  });

  attachOAuthCredentialPersistence(yt);
  await yt.session.signIn(tokens);
  // session.credentials is not a real getter on current youtubei.js — tokens live
  // on session.oauth.oauth2_tokens after a successful signIn / refresh.
  persistOAuthCredentials(oauthTokensFromSession(yt) || tokens);
  return {
    yt,
    sessionManager: new SessionManager(false, {}),
    authMode: 'oauth',
  };
}

async function getPlaybackRuntime(cookie = '') {
  const key = playbackSessionKey(cookie);
  const runtime = SESSION_CACHE.get(key);
  if (runtime) {
    return runtime;
  }

  const existing = PLAYBACK_RUNTIME_IN_FLIGHT.get(key);
  if (existing) {
    return existing;
  }

  let pending;
  pending = createPlaybackRuntime(cookie)
    .then((createdRuntime) => {
      // invalidatePlaybackRuntime may have deliberately detached this build
      // while it was in flight. Do not let a stale session repopulate the cache.
      if (PLAYBACK_RUNTIME_IN_FLIGHT.get(key) === pending) {
        SESSION_CACHE.set(key, createdRuntime);
      }
      return createdRuntime;
    })
    .finally(() => {
      if (PLAYBACK_RUNTIME_IN_FLIGHT.get(key) === pending) {
        PLAYBACK_RUNTIME_IN_FLIGHT.delete(key);
      }
    });
  PLAYBACK_RUNTIME_IN_FLIGHT.set(key, pending);
  return pending;
}

async function getOAuthRuntime() {
  const oauthCredentials = readStoredOAuthTokens();
  if (!oauthCredentials) {
    return null;
  }
  const key = `oauth|${oauthSessionCacheKey(oauthCredentials)}`;
  let runtime = SESSION_CACHE.get(key);
  if (runtime) {
    return runtime;
  }
  try {
    runtime = await createOAuthRuntime(oauthCredentials);
  } catch (err) {
    console.error(
      `[squirrel-desktop] youtubei_core: OAuth signIn failed: ${err?.message || err}`,
    );
    return null;
  }
  const healed = readStoredOAuthTokens() || oauthCredentials;
  const resolvedKey = `oauth|${oauthSessionCacheKey(healed)}`;
  SESSION_CACHE.set(resolvedKey, runtime);
  if (resolvedKey !== key) {
    SESSION_CACHE.set(key, runtime);
  }
  return runtime;
}

/**
 * Captions / account helpers may want OAuth when available; playback does not.
 */
async function getRuntime(cookie = '') {
  const oauthRuntime = await getOAuthRuntime();
  if (oauthRuntime) {
    return oauthRuntime;
  }
  return getPlaybackRuntime(cookie);
}

async function buildPoToken(videoId, runtime, attempts) {
  if (!runtime?.sessionManager) {
    return null;
  }

  try {
    // App startup primes the expensive BotGuard integrity-token minter. If a
    // user opens a video while that work is still running, join the same promise
    // instead of starting a second challenge / VM snapshot in parallel.
    try {
      await warmPoTokenMinter(runtime);
    } catch (error) {
      attempts.push({
        client: 'POTOKEN_WARMUP',
        po_token_error: error?.message || String(error),
      });
    }
    const tokenData = await runtime.sessionManager.generatePoToken(
      videoId,
      '',
      false,
      undefined,
      false,
      undefined,
      runtime.yt.session.context,
    );
    return tokenData?.poToken || null;
  } catch (error) {
    attempts.push({
      client: 'POTOKEN',
      po_token_error: error?.message || String(error),
    });
    return null;
  }
}

function hasFreshPoTokenMinter(runtime) {
  const minterCache = runtime?.sessionManager?.minterCache;
  if (!minterCache || typeof minterCache.values !== 'function') {
    return false;
  }
  const now = Date.now();
  for (const entry of minterCache.values()) {
    if (entry?.expiry && new Date(entry.expiry).getTime() > now) {
      return true;
    }
  }
  return false;
}

function warmPoTokenMinter(runtime) {
  if (!runtime?.sessionManager || !runtime?.yt?.session?.context) {
    return Promise.resolve();
  }
  const existing = PO_TOKEN_MINTER_WARMUPS.get(runtime);
  if (existing) {
    return existing;
  }
  if (hasFreshPoTokenMinter(runtime)) {
    return Promise.resolve();
  }

  const visitorData = runtime.yt.session.context.client?.visitorData;
  let pending;
  pending = runtime.sessionManager.generatePoToken(
    visitorData,
    '',
    false,
    undefined,
    false,
    undefined,
    runtime.yt.session.context,
  ).finally(() => {
    if (PO_TOKEN_MINTER_WARMUPS.get(runtime) === pending) {
      PO_TOKEN_MINTER_WARMUPS.delete(runtime);
    }
  });
  PO_TOKEN_MINTER_WARMUPS.set(runtime, pending);
  return pending;
}

// ── OAuth in-flight flow tracker ──────────────────────────────────────────────

let _oauthFlowInFlight = null; // { yt, resolve, reject, settled }

export async function prewarmYoutubeiRuntime(cookie = '') {
  // Warm both the remote WEB/player session and BotGuard token minter. The
  // per-video token itself stays video-bound, but minting it is sub-millisecond
  // once the integrity-token minter exists (and SessionManager keeps it fresh).
  // OAuth remains lazy because it is only needed for auth gates / account UI.
  const runtime = await getPlaybackRuntime(cookie);
  await warmPoTokenMinter(runtime);
  return {
    status: 'ok',
    prewarmed: true,
  };
}

async function resolveOAuthSetup() {
  const stateFile = getOAuthStateFilePath();
  if (!stateFile) {
    throw new Error('OAuth state file path not configured');
  }

  // If credentials exist, validate them before claiming "authenticated"
  const existingTokens = readStoredOAuthTokens();
  if (existingTokens) {
    try {
      const validatorYt = await Innertube.create({
        cache: createPlayerCache(false),
        generate_session_locally: true,
        retrieve_player: false,
        client_type: 'WEB',
        fetch: buildYoutubeFetch(),
      });
      attachOAuthCredentialPersistence(validatorYt);
      await validatorYt.session.signIn(existingTokens);
      persistOAuthCredentials(oauthTokensFromSession(validatorYt) || existingTokens);
      return {
        action: 'oauth-setup',
        status: 'authenticated',
        account: extractAccountInfo(validatorYt),
      };
    } catch {
      console.debug('[squirrel-desktop] youtubei_core: resolveOAuthSetup credentials invalid/expired');
      saveOAuthState({ pending: false, error: null });
    }
  }

  if (_oauthFlowInFlight?.settled === false) {
    const state = loadOAuthState();
    if (state?.pending) {
      return {
        action: 'oauth-setup',
        status: 'pending',
        verification_url: YOUTUBE_TV_ACTIVATION_URL,
        user_code: state.user_code,
      };
    }
  }

  if (_oauthFlowInFlight) {
    _oauthFlowInFlight.yt.session.signOut?.();
    _oauthFlowInFlight = null;
  }

  const yt = await Innertube.create({
    cache: createPlayerCache(false),
    fetch: buildYoutubeFetch(),
  });

  return new Promise((resolve, reject) => {
    _oauthFlowInFlight = { yt, resolve, reject, settled: false };

    yt.session.on('auth-pending', (data) => {
      saveOAuthState({
        pending: true,
        verification_url: YOUTUBE_TV_ACTIVATION_URL,
        user_code: data.user_code,
      });
      resolve({
        action: 'oauth-setup',
        status: 'pending',
        verification_url: YOUTUBE_TV_ACTIVATION_URL,
        user_code: data.user_code,
      });
    });

    yt.session.on('auth', (event) => {
      persistOAuthCredentials(event);
      if (_oauthFlowInFlight) {
        _oauthFlowInFlight.settled = true;
        _oauthFlowInFlight.resolve({
          action: 'oauth-setup',
          status: 'authenticated',
          account: extractAccountInfo(yt),
        });
        _oauthFlowInFlight = null;
      }
    });

    yt.session.on('auth-error', ({ error }) => {
      saveOAuthState({ pending: false, error: String(error) });
      if (_oauthFlowInFlight) {
        _oauthFlowInFlight.settled = true;
        _oauthFlowInFlight.reject(new Error(`OAuth error: ${error}`));
        _oauthFlowInFlight = null;
      }
    });

    yt.session.signIn().catch((err) => {
      if (_oauthFlowInFlight) {
        saveOAuthState({ pending: false, error: String(err) });
        _oauthFlowInFlight = null;
        reject(err);
      }
    });
  });
}

async function resolveOAuthStatus() {
  const stateFile = getOAuthStateFilePath();
  if (!stateFile) {
    return { status: 'not_configured' };
  }

  const state = loadOAuthState();

  // Check in-flight flow first (user is mid-authorization)
  if (_oauthFlowInFlight?.settled === false) {
    if (state?.pending) {
      return {
        status: 'pending',
        verification_url: YOUTUBE_TV_ACTIVATION_URL,
        user_code: state.user_code,
      };
    }
    // In-flight but no pending in file → auth may have completed
  }

  if (state?.error) {
    return { status: 'error', error: state.error };
  }

  const tokens = readStoredOAuthTokens();
  if (!tokens) {
    return { status: 'not_configured' };
  }

  // Credentials exist in file. Always validate them through sign-in so the
  // library can refresh access tokens when a refresh token is available.
  try {
    const yt = await Innertube.create({
      cache: createPlayerCache(false),
      fetch: buildYoutubeFetch(),
    });
    attachOAuthCredentialPersistence(yt);
    await yt.session.signIn(tokens);
    const updatedCredentials = oauthTokensFromSession(yt) || tokens;
    persistOAuthCredentials(updatedCredentials);
    return {
      status: 'authenticated',
      account: extractAccountInfo(yt),
    };
  } catch {
    console.debug('[squirrel-desktop] youtubei_core: resolveOAuthStatus signIn failed, expired');
    return { status: 'expired' };
  }
}

async function resolveOAuthRevoke() {
  const stateFile = getOAuthStateFilePath();
  if (!stateFile) {
    return { status: 'done' };
  }

  if (_oauthFlowInFlight) {
    _oauthFlowInFlight.yt.session.signOut?.();
    _oauthFlowInFlight = null;
  }

  const tokens = readStoredOAuthTokens();
  if (tokens) {
    try {
      const yt = await Innertube.create({
        cache: createPlayerCache(false),
        fetch: buildYoutubeFetch(),
      });
      await yt.session.signIn(tokens);
      await yt.session.signOut();
    } catch {
      console.debug('[squirrel-desktop] youtubei_core: resolveOAuthRevoke signOut failed');
    }
  }

  try {
    const { unlinkSync } = await import('node:fs');
    unlinkSync(stateFile);
  } catch {
    console.debug('[squirrel-desktop] youtubei_core: resolveOAuthRevoke unlink failed', stateFile);
  }

  return { status: 'done' };
}

export async function resolveYoutubeiPayload(payload) {
  const action = String(payload?.action || 'resolve');
  const cookie = typeof payload?.cookie === 'string' ? payload.cookie.trim() : '';

  if (action === 'oauth-setup') {
    return resolveOAuthSetup();
  }
  if (action === 'oauth-status') {
    return resolveOAuthStatus();
  }
  if (action === 'oauth-revoke') {
    return resolveOAuthRevoke();
  }

  if (action === 'prewarm') {
    return prewarmYoutubeiRuntime(cookie);
  }
  if (action === 'captions') {
    return resolveCaptionPayload(payload);
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
  const attempts = [];
  const runtimeStart = performance.now();

  // Official path always uses the anonymous/cookie playback runtime.
  // OAuth sessions are not used for streaming (SABR / no cipher URLs).
  let playbackRuntime = await getPlaybackRuntime(cookie);
  timings.get_runtime_ms = Number((performance.now() - runtimeStart).toFixed(1));

  // Reading persisted credentials is cheap. Constructing and signing in an
  // OAuth Innertube runtime is not, so defer that work unless anonymous
  // playback actually encounters an auth gate. Nested/invalid files must not
  // count as "has auth" — that would skip the login-required UX path.
  const hasOAuthCredentials = Boolean(readStoredOAuthTokens());
  const hasAuth = hasOAuthCredentials || playbackRuntime.authMode === 'cookie';

  // Primary: FreeTube-style official clients that produce VideoInfo.toDash().
  const primaryClients = requestedClients.length
    ? requestedClients
    : OFFICIAL_PLAYBACK_CLIENTS;

  let bestCandidate = null;
  let sessionRebuilds = 0;

  while (sessionRebuilds <= MAX_PLAYBACK_SESSION_REBUILDS) {
    const attemptLabelPrefix = sessionRebuilds === 0 ? 'official' : `official-retry${sessionRebuilds}`;
    bestCandidate = await resolveFormatsWithRuntime({
      runtime: playbackRuntime,
      videoId,
      clients: primaryClients,
      resolutionMode,
      attempts,
      timings,
      includeDebugTimings,
      attemptLabelPrefix,
      // YouTube may authorize the initial media bytes while rejecting distant
      // byte ranges. Mint the content-bound token before building the MPD so
      // seeks do not fail later with googlevideo 403 responses.
      preferPoToken: true,
    });

    if (bestCandidate && bestCandidate.score >= 4) {
      break;
    }

    // A poisoned / bot-gated visitor session makes every official client return
    // LOGIN_REQUIRED or empty streaming_data. Rebuild the remote WEB session once
    // before accepting progressive / SABR fallbacks.
    const recentOfficialAttempts = attempts.filter((item) =>
      String(item?.client || '').startsWith(attemptLabelPrefix),
    );
    const looksPoisoned = recentOfficialAttempts.length > 0
      && recentOfficialAttempts.every((item) =>
        attemptLooksLikeAuthGate(item)
        || Number(item?.format_score || 0) === 0
        || /Streaming data not available|No valid URL to decipher/i.test(String(item?.error || '')),
      );

    if (!looksPoisoned || sessionRebuilds >= MAX_PLAYBACK_SESSION_REBUILDS) {
      break;
    }

    sessionRebuilds += 1;
    invalidatePlaybackRuntime(cookie);
    const rebuildStart = performance.now();
    playbackRuntime = await getPlaybackRuntime(cookie);
    timings[`session_rebuild_${sessionRebuilds}_ms`] = Number(
      (performance.now() - rebuildStart).toFixed(1),
    );
    attempts.push({
      client: `SESSION_REBUILD_${sessionRebuilds}`,
      reason: 'official_clients_gated_or_empty',
    });
  }

  // Secondary: ANDROID/WEB on the same anonymous runtime (progressive / partial).
  // Only after official MWEB failed — never prefer these over a valid toDash.
  if (
    (!bestCandidate || bestCandidate.score < 4)
    && requestedClients.length === 0
  ) {
    const fallbackStart = performance.now();
    const fallbackBest = await resolveFormatsWithRuntime({
      runtime: playbackRuntime,
      videoId,
      clients: OFFICIAL_FALLBACK_CLIENTS,
      resolutionMode,
      attempts,
      timings,
      includeDebugTimings,
      attemptLabelPrefix: 'fallback',
      preferPoToken: false,
    });
    timings.official_fallback_ms = Number((performance.now() - fallbackStart).toFixed(1));
    if (fallbackBest && (!bestCandidate || fallbackBest.score > bestCandidate.score)) {
      bestCandidate = fallbackBest;
    }
  }

  // Auth gate only: when anonymous is LOGIN_REQUIRED / bot-blocked, try TV/WEB
  // with OAuth so age/members/bot gates can pass. Still prefer any toDash body.
  const authGated = (attempts || []).some((attempt) => attemptLooksLikeAuthGate(attempt));
  if (
    (!bestCandidate || bestCandidate.score < 4)
    && authGated
    && hasOAuthCredentials
    && requestedClients.length === 0
  ) {
    const authStart = performance.now();
    try {
      const oauthRuntime = await getOAuthRuntime();
      if (!oauthRuntime) {
        throw new Error('YouTube OAuth session is unavailable');
      }
      const authBest = await resolveFormatsWithRuntime({
        runtime: oauthRuntime,
        videoId,
        clients: AUTH_GATE_PLAYBACK_CLIENTS,
        resolutionMode,
        attempts,
        timings,
        includeDebugTimings,
        attemptLabelPrefix: 'auth-gate',
        preferPoToken: true,
      });
      timings.auth_gate_ms = Number((performance.now() - authStart).toFixed(1));
      if (authBest && (!bestCandidate || authBest.score > bestCandidate.score)) {
        bestCandidate = {
          score: authBest.score,
          response: {
            ...authBest.response,
            auth_fallback: 'oauth-gate',
          },
        };
      }
    } catch (error) {
      timings.auth_gate_ms = Number((performance.now() - authStart).toFixed(1));
      attempts.push({
        client: 'AUTH_GATE',
        error: error?.message || String(error),
      });
    }
  }

  if (bestCandidate) {
    return bestCandidate.response;
  }

  const errorResponse = {
    status: 'error',
    error: buildPlaybackFailureError(attempts, hasAuth),
    attempts,
  };
  if (includeDebugTimings) {
    errorResponse.timings = timings;
  }
  return errorResponse;
}

/**
 * Try a list of Innertube clients against one runtime and return the best
 * scored format set. Official success is VideoInfo.toDash() (score 4).
 */
async function resolveFormatsWithRuntime({
  runtime,
  videoId,
  clients,
  resolutionMode,
  attempts,
  timings,
  includeDebugTimings,
  attemptLabelPrefix = '',
  preferPoToken = false,
}) {
  let contentPoToken;
  let bestCandidate = null;

  for (const client of clients) {
    const attemptClient = attemptLabelPrefix ? `${attemptLabelPrefix}:${client}` : client;
    try {
      let requestOptions = { client };
      let activePoToken = null;
      // Player is cached across video resolves; never let a token bound to the
      // previous video or client leak into URL deciphering for this attempt.
      if (runtime.yt.session.player) {
        runtime.yt.session.player.po_token = undefined;
      }
      // The same content-bound token must authorize both the player request and
      // every URL emitted by toDash(). MWEB without it appears playable at byte
      // zero but distant ranges fail later with googlevideo 403 responses.
      const requiresPoToken = preferPoToken && (client === 'MWEB' || client === 'WEB');
      if (requiresPoToken) {
        if (contentPoToken === undefined) {
          const poTokenStart = performance.now();
          contentPoToken = await buildPoToken(videoId, runtime, attempts);
          timings.build_po_token_ms = Number((performance.now() - poTokenStart).toFixed(1));
        }
        if (!contentPoToken) {
          throw new Error(`Content-bound PO Token unavailable for ${client}`);
        }
        activePoToken = contentPoToken;
        requestOptions = { client, po_token: activePoToken };
        if (runtime.yt.session.player) {
          runtime.yt.session.player.po_token = activePoToken;
        }
      }

      const infoStart = performance.now();
      // getBasicInfo is the official youtubei.js player entry used by FreeTube
      // for streaming_data (getInfo is only needed for watch-page extras).
      const videoInfo = await runtime.yt.getBasicInfo(videoId, requestOptions);
      const infoMs = Number((performance.now() - infoStart).toFixed(1));
      const playbackAdaptiveFormats = selectPlaybackAdaptiveFormats(videoInfo);
      const sabrAdaptiveFormats = selectSabrStartupFormats(playbackAdaptiveFormats);

      // FreeTube chooses SABR XOR regular DASH, but its SABR path is a cheap
      // JSON manifest — not VideoInfo.toDash. Our SABR path still needs a
      // toDash(is_sabr) body for Shaka, and the player relies on
      // fallback_mpd_content when SABR attach fails. Run both toDash builds
      // in parallel so wall time is max(sabr, dash), not sum, and first frame
      // keeps an immediate DASH fallback without a second resolve round trip.
      const manifestStart = performance.now();
      const [sabrPlayback, localDashManifest] = await Promise.all([
        buildSabrPlayback(
          videoInfo,
          runtime,
          activePoToken,
          sabrAdaptiveFormats,
        ),
        buildLocalDashManifest(videoInfo, {
          poToken: activePoToken || undefined,
          allowedFormats: playbackAdaptiveFormats,
        }),
      ]);
      const parallelManifestMs = Number((performance.now() - manifestStart).toFixed(1));
      // Attribute the shared wall clock to both keys for existing log consumers.
      const sabrMs = parallelManifestMs;
      const localDashMs = parallelManifestMs;

      // Hosted dash/hls URLs are only needed when official toDash failed.
      let normalizedStreamingData = {
        dash_manifest_url: null,
        hls_manifest_url: null,
        expires: videoInfo?.streaming_data?.expires ?? null,
      };
      let streamingDataMs = 0;
      if (!sabrPlayback && !localDashManifest) {
        const streamingDataStart = performance.now();
        normalizedStreamingData = await normalizeStreamingData(
          videoInfo,
          runtime.yt.session.player,
          activePoToken,
        );
        streamingDataMs = Number((performance.now() - streamingDataStart).toFixed(1));
      }

      const formatsStart = performance.now();
      let formats;
      if (localDashManifest || sabrPlayback) {
        // Metadata-only ladder for the quality menu (heights/itags). No per-itag
        // decipher — MPD already carries playable BaseURLs from toDash / SABR.
        const streamingData = videoInfo.streaming_data || {};
        const rawFormats = [
          ...(streamingData.formats || []),
          ...(streamingData.adaptive_formats || []),
        ];
        formats = rawFormats.map((format) => buildFormatMetadata(format));
      } else {
        formats = await collectFormats(videoInfo, runtime.yt.session.player, resolutionMode);
      }
      const formatsMs = Number((performance.now() - formatsStart).toFixed(1));

      const playabilityStatus = videoInfo.playability_status?.status || null;
      const playabilityReason = videoInfo.playability_status?.reason
        || videoInfo.playability_status?.error_screen?.reason?.text
        || null;
      const basicInfo = videoInfo.basic_info || {};
      const score = scoreFormatSet(formats, {
        sabrPlayback,
        localDashManifest,
        dashManifestUrl: normalizedStreamingData?.dash_manifest_url || null,
      });
      attempts.push({
        client: attemptClient,
        playability_status: playabilityStatus,
        playability_reason: playabilityReason,
        format_count: formats.length,
        playable: score > 0,
        format_score: score,
        sabr: Boolean(sabrPlayback),
        sabr_format_count: sabrPlayback?.formats?.length || 0,
        official_todash: Boolean(localDashManifest),
        po_token: Boolean(activePoToken && requestOptions.po_token),
        get_info_ms: infoMs,
        collect_formats_ms: formatsMs,
        normalize_streaming_data_ms: streamingDataMs,
        build_sabr_ms: sabrMs,
        build_local_dash_ms: localDashMs,
      });

      if (score === 0) {
        continue;
      }

      const response = {
        status: 'ok',
        client,
        playability_status: playabilityStatus,
        formats,
        streaming_data: normalizedStreamingData,
        sabr_playback: sabrPlayback,
        local_dash_manifest: localDashManifest,
        basic_info: pickBasicInfo(basicInfo),
      };
      if (includeDebugTimings) {
        response.timings = {
          ...timings,
          get_info_ms: infoMs,
          collect_formats_ms: formatsMs,
          normalize_streaming_data_ms: streamingDataMs,
          build_sabr_ms: sabrMs,
          build_local_dash_ms: localDashMs,
        };
      }

      if (!bestCandidate || score > bestCandidate.score) {
        bestCandidate = { score, response };
      }
      // A complete official manifest is sufficient; SABR scores above regular
      // DASH when the same client exposes both.
      if (score >= 4) {
        return bestCandidate;
      }
    } catch (error) {
      const playability = error?.info || error?.playability_status || null;
      const subreason = playability?.error_screen?.subreason?.text
        || playability?.error_screen?.reason?.text
        || null;
      attempts.push({
        client: attemptClient,
        error: error?.message || String(error),
        playability_status: playability?.status || null,
        playability_reason: playability?.reason || subreason || null,
        playability_subreason: subreason,
      });
    }
  }

  return bestCandidate;
}

function attemptLooksLikeAuthGate(attempt) {
  const status = String(attempt?.playability_status || '').toUpperCase();
  const reason = String(
    attempt?.playability_reason
    || attempt?.playability_subreason
    || attempt?.error
    || '',
  );
  if (status === 'LOGIN_REQUIRED' || (status === 'UNPLAYABLE' && /sign in|login/i.test(reason))) {
    return true;
  }
  return /sign in to confirm|not a bot|login required|auth.?required|please sign in/i.test(reason);
}

function attemptLooksLikePermanentUnavailability(attempt) {
  const status = String(attempt?.playability_status || '').toUpperCase();
  const reason = String(
    attempt?.playability_reason
    || attempt?.playability_subreason
    || attempt?.error
    || '',
  );
  if (status === 'LOGIN_REQUIRED') {
    return false;
  }
  return /this video is unavailable|video unavailable|has been removed|removed by the uploader|private video|video has been deleted|account associated with this video has been terminated/i
    .test(reason);
}

function buildPlaybackFailureError(attempts, hasAuth) {
  const authGated = (attempts || []).some((attempt) => attemptLooksLikeAuthGate(attempt));
  if (authGated && !hasAuth) {
    return {
      type: 'PlaybackAuthRequired',
      code: 'YOUTUBE_LOGIN_REQUIRED',
      message: 'YouTube 要求登录后才能播放（机器人验证/登录门禁）。请在设置中完成 YouTube TV 授权后重试。',
    };
  }
  if (authGated && hasAuth) {
    return {
      type: 'PlaybackAuthRequired',
      code: 'YOUTUBE_AUTH_EXPIRED',
      message: 'YouTube 授权可能已失效，请在设置中重新完成 YouTube TV 授权后重试。',
    };
  }

  const permanent = (attempts || []).find((attempt) => attemptLooksLikePermanentUnavailability(attempt));
  if (permanent) {
    const detail = String(
      permanent.playability_subreason
      || permanent.playability_reason
      || permanent.error
      || '',
    ).trim();
    return {
      type: 'PlaybackResolverError',
      code: 'YOUTUBE_VIDEO_UNAVAILABLE',
      message: detail && !/^this video is unavailable$/i.test(detail)
        ? `该 YouTube 视频不可播放：${detail}`
        : '该 YouTube 视频不可播放（已删除、设为私密或对当前地区不可用）。',
    };
  }

  return {
    type: 'PlaybackResolverError',
    code: 'YOUTUBE_NO_FORMAT_SET',
    message: hasAuth
      ? '无法获取可播放的 YouTube 流（所有客户端均未返回完整格式），请稍后重试。'
      : '无法获取可播放的 YouTube 流。YouTube 可能暂时限制了匿名访问，请先在「站点」中登录 YouTube 后重试。',
  };
}
