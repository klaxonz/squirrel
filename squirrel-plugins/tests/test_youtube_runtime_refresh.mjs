import assert from 'node:assert/strict';
import test from 'node:test';

import { __testing, resolveYoutubeiPayload } from '../youtube/src/squirrel_youtube/node/youtubei_core.mjs';

test('authenticated playback refreshes the cached runtime after a stale-session failure', async () => {
  const observedCalls = [];
  let runtimeVersion = 0;

  __testing.clearAllRuntimeCache();
  __testing.setRuntimeFactory(async () => {
    runtimeVersion += 1;
    const currentVersion = runtimeVersion;
    return {
      yt: {
        session: {
          context: {},
          player: null,
        },
        async getBasicInfo(videoId, requestOptions = {}) {
          observedCalls.push({
            runtimeVersion: currentVersion,
            videoId,
            client: requestOptions.client,
          });

          if (currentVersion === 1) {
            throw new Error('stale authenticated runtime');
          }

          return {
            streaming_data: {
              formats: [
                {
                  itag: 18,
                  mime_type: 'video/mp4; codecs="avc1.42001E, mp4a.40.2"',
                  quality_label: '360p',
                  has_audio: true,
                  has_video: true,
                  url: 'https://example.test/itag/18',
                },
              ],
            },
            playability_status: {
              status: 'OK',
            },
          };
        },
      },
      sessionManager: {
        async generatePoToken() {
          return {
            poToken: 'demo-token',
          };
        },
      },
    };
  });

  try {
    const result = await resolveYoutubeiPayload({
      video_id: 'demo-video',
      cookie: 'SAPISID=abc; SID=def',
    });

    assert.equal(result.status, 'ok');
    assert.equal(result.client, 'TV');
    assert.equal(runtimeVersion, 2);
    assert.deepEqual(
      observedCalls.map((entry) => entry.runtimeVersion),
      [1, 1, 1, 2],
    );
  } finally {
    __testing.resetRuntimeFactory();
    __testing.clearAllRuntimeCache();
  }
});

test('authenticated youtubei fetch does not force the logged-out bootstrap header', async () => {
  const originalFetch = globalThis.fetch;
  let capturedHeaders;

  globalThis.fetch = async (_input, init = {}) => {
    capturedHeaders = new Headers(init.headers);
    return {
      ok: true,
      status: 200,
      json: async () => ({}),
      text: async () => '',
    };
  };

  try {
    const authFetch = __testing.createYoutubeFetch(true);
    await authFetch('https://www.youtube.com/youtubei/v1/player', { headers: {} });

    assert.equal(capturedHeaders.get('X-Youtube-Bootstrap-Logged-In'), null);

    const anonFetch = __testing.createYoutubeFetch(false);
    await anonFetch('https://www.youtube.com/youtubei/v1/player', { headers: {} });

    assert.equal(capturedHeaders.get('X-Youtube-Bootstrap-Logged-In'), 'false');
  } finally {
    globalThis.fetch = originalFetch;
  }
});
