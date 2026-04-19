import { createHash } from 'node:crypto';
import { mkdirSync } from 'node:fs';
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { Innertube, Platform, UniversalCache } from 'youtubei.js/web';

import { SessionManager } from './build/session_manager.js';

const AUTHENTICATED_PLAYBACK_CLIENTS = ['TV', 'MWEB', 'WEB'];
const AUTHENTICATED_FULL_CLIENTS = ['TV', 'MWEB', 'WEB'];
const ANONYMOUS_CLIENTS = ['ANDROID'];
const CAPTIONS_ANONYMOUS_CLIENTS = ['ANDROID'];
const CAPTIONS_AUTHENTICATED_CLIENTS = ['WEB', 'TV', 'MWEB'];
const YOUTUBE_WEB_ORIGIN = 'https://www.youtube.com';
const SESSION_CACHE = new Map();

// OAuth state file path (passed via environment variable from Python side)
const OAUTH_STATE_FILE = process.env.YOUTUBE_OAUTH_STATE_FILE || '';

// ── OAuth state helpers ─────────────────────────────────────────────────────

function getOAuthStateFilePath() {
  return OAUTH_STATE_FILE || null;
}

function loadOAuthState() {
  const stateFile = getOAuthStateFilePath();
  if (!stateFile) return null;
  try {
    return JSON.parse(readFileSync(stateFile, 'utf-8'));
  } catch {
    return null;
  }
}

function saveOAuthState(state) {
  const stateFile = getOAuthStateFilePath();
  if (!stateFile) return;
  mkdirSync(resolve(stateFile, '..'), { recursive: true });
  writeFileSync(stateFile, JSON.stringify(state, null, 2), 'utf-8');
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
  const clients = cookie ? CAPTIONS_AUTHENTICATED_CLIENTS : CAPTIONS_ANONYMOUS_CLIENTS;
  const attempts = [];

  for (const client of clients) {
    try {
      const info = await runtime.yt.getBasicInfo(videoId, { client });
      const captions = info.captions;
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

function oauthSessionCacheKey(oauthState) {
  if (!oauthState?.credentials) {
    return 'oauth:none';
  }
  return `oauth:${createHash('sha1').update(JSON.stringify(oauthState.credentials)).digest('hex')}`;
}

async function createRuntime(cookie, oauthCredentials = null) {
  const yt = await Innertube.create({
    cache: new UniversalCache(true),
    generate_session_locally: !cookie && !oauthCredentials,
    retrieve_player: true,
    client_type: oauthCredentials ? 'WEB' : cookie ? 'MWEB' : 'ANDROID',
    fetch: buildYoutubeFetch(),
    ...((cookie && !oauthCredentials) ? { cookie } : {}),
  });

  if (oauthCredentials) {
    try {
      await yt.session.signIn(oauthCredentials);
      return { yt, sessionManager: null, authMode: 'oauth' };
    } catch (err) {
      console.error(`[DEBUG] OAuth signIn failed (credentials will be skipped): ${err?.message || err}`);
      return createRuntime(cookie, null);
    }
  }

  return {
    yt,
    sessionManager: cookie ? new SessionManager(false, {}) : null,
    authMode: cookie ? 'cookie' : 'anonymous',
  };
}

async function getRuntime(cookie) {
  const oauthState = loadOAuthState();
  let oauthCredentials = oauthState?.credentials || null;

  // If OAuth credentials are present but stale, attempt to validate by creating a session
  if (oauthCredentials) {
    try {
      const testYt = await Innertube.create({
        cache: new UniversalCache(false),
        generate_session_locally: true,
        retrieve_player: false,
        client_type: 'WEB',
        fetch: buildYoutubeFetch(),
      });
      await testYt.session.signIn(oauthCredentials);
      // Sign-in succeeded, proceed with OAuth
    } catch {
      // OAuth credentials are invalid or expired, clear them
      oauthCredentials = null;
    }
  }

  const key = `${sessionCacheKey(cookie)}|${oauthSessionCacheKey(oauthState)}`;
  let runtime = SESSION_CACHE.get(key);
  if (runtime) {
    return runtime;
  }

  runtime = await createRuntime(cookie, oauthCredentials);
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

// ── OAuth in-flight flow tracker ──────────────────────────────────────────────

let _oauthFlowInFlight = null; // { yt, resolve, reject, settled }

export async function prewarmYoutubeiRuntime(cookie = '') {
  await getRuntime(cookie);
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
  const existing = loadOAuthState();
  if (existing?.credentials) {
    try {
      const validatorYt = await Innertube.create({
        cache: new UniversalCache(false),
        generate_session_locally: true,
        retrieve_player: false,
        client_type: 'WEB',
        fetch: buildYoutubeFetch(),
      });
      await validatorYt.session.signIn(existing.credentials);
      return {
        action: 'oauth-setup',
        status: 'authenticated',
        account: extractAccountInfo(validatorYt),
      };
    } catch {
      // Credentials are invalid/expired, clear the file and start fresh
      saveOAuthState({ pending: false, error: null });
    }
  }

  if (_oauthFlowInFlight?.settled === false) {
    const state = loadOAuthState();
    if (state?.pending) {
      return {
        action: 'oauth-setup',
        status: 'pending',
        verification_url: state.verification_url,
        user_code: state.user_code,
      };
    }
  }

  if (_oauthFlowInFlight) {
    _oauthFlowInFlight.yt.session.signOut?.();
    _oauthFlowInFlight = null;
  }

  const yt = await Innertube.create({
    cache: new UniversalCache(false),
    fetch: buildYoutubeFetch(),
  });

  return new Promise((resolve, reject) => {
    _oauthFlowInFlight = { yt, resolve, reject, settled: false };

    yt.session.on('auth-pending', (data) => {
      saveOAuthState({
        pending: true,
        verification_url: data.verification_url,
        user_code: data.user_code,
      });
      resolve({
        action: 'oauth-setup',
        status: 'pending',
        verification_url: data.verification_url,
        user_code: data.user_code,
      });
    });

    yt.session.on('auth', ({ credentials }) => {
      saveOAuthState({ pending: false, credentials });
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
        verification_url: state.verification_url,
        user_code: state.user_code,
      };
    }
    // In-flight but no pending in file → auth may have completed
  }

  if (!state?.credentials) {
    return { status: 'not_configured' };
  }

  if (state.error) {
    return { status: 'error', error: state.error };
  }

  // Fast path: check expiry_date before making a network request
  const expiry = state.credentials?.expiry_date;
  if (expiry) {
    try {
      const expiryMs = typeof expiry === 'number' ? expiry : Date.parse(String(expiry));
      if (!isNaN(expiryMs) && expiryMs < Date.now() - 60_000) {
        return { status: 'expired' };
      }
    } catch {
      // Fall through to network validation
    }
  }

  // Credentials exist in file — validate them (handles token refresh)
  try {
    const yt = await Innertube.create({
      cache: new UniversalCache(false),
      fetch: buildYoutubeFetch(),
    });
    await yt.session.signIn(state.credentials);
    const updatedCredentials = yt.session.credentials || state.credentials;
    saveOAuthState({ pending: false, credentials: updatedCredentials });
    return {
      status: 'authenticated',
      account: extractAccountInfo(yt),
    };
  } catch {
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

  const state = loadOAuthState();
  if (state?.credentials) {
    try {
      const yt = await Innertube.create({
        cache: new UniversalCache(false),
        fetch: buildYoutubeFetch(),
      });
      await yt.session.signIn(state.credentials);
      await yt.session.signOut();
    } catch {
      // Ignore errors
    }
  }

  try {
    const { unlinkSync } = await import('node:fs');
    unlinkSync(stateFile);
  } catch {
    // Ignore
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
  const runtime = await getRuntime(cookie);
  timings.get_runtime_ms = Number((performance.now() - runtimeStart).toFixed(1));
  const hasAuth = runtime.authMode === 'oauth' || runtime.authMode === 'cookie';
  const clients = requestedClients.length
    ? requestedClients
    : (hasAuth
      ? (resolutionMode === 'all' ? AUTHENTICATED_FULL_CLIENTS : AUTHENTICATED_PLAYBACK_CLIENTS)
      : ANONYMOUS_CLIENTS);
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
