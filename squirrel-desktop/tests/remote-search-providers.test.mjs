import assert from 'node:assert/strict'
import test from 'node:test'

import { getRemoteChannel } from '../src/search/providers/remote-channel.mjs'
import { searchBilibiliVideos } from '../src/search/providers/bilibili.mjs'
import { searchRemoteVideos } from '../src/search/providers/index.mjs'
import { searchYouTubeVideos } from '../src/search/providers/youtube.mjs'

const jsonResponse = (payload) => new Response(JSON.stringify(payload), {
  status: 200,
  headers: { 'content-type': 'application/json' },
})

const htmlResponse = (html) => new Response(html, {
  status: 200,
  headers: { 'content-type': 'text/html' },
})

const buildCookieHeader = async () => 'SESSDATA=test'

test('desktop bilibili remote search maps api results', async () => {
  let requestedUrl = ''
  const items = await searchBilibiliVideos({
    query: 'demo',
    limit: 5,
    page: 2,
    buildCookieHeader,
    fetchImpl: async (url) => {
      if (url.includes('/x/web-interface/card')) {
        return jsonResponse({
          data: {
            card: {
              mid: '12345',
              name: 'Uploader',
              face: '//i0.hdslb.com/avatar.jpg',
            },
          },
        })
      }

      requestedUrl = url
      return jsonResponse({
        data: {
          result: [
            {
              bvid: 'BV1demo',
              title: '<em class="keyword">Demo</em> Video',
              arcurl: 'https://www.bilibili.com/video/BV1demo',
              pic: '//i0.hdslb.com/demo.jpg',
              duration: '01:02',
              pubdate: 1700000000,
              author: 'Uploader',
              mid: 12345,
              upic: '',
            },
          ],
        },
      })
    },
  })

  assert.equal(items.length, 1)
  assert.equal(items[0].site, 'bilibili')
  assert.equal(items[0].title, 'Demo Video')
  assert.equal(items[0].duration, 62)
  assert.equal(items[0].uploader_url, 'https://space.bilibili.com/12345')
  assert.equal(items[0].uploader_avatar, 'https://i0.hdslb.com/avatar.jpg')
  assert.deepEqual(items[0].subscriptions, [{
    id: 12345,
    type: 'CHANNEL',
    name: 'Uploader',
    url: 'https://space.bilibili.com/12345',
    avatar: 'https://i0.hdslb.com/avatar.jpg',
    is_nsfw: false,
  }])
  assert.equal(new URL(requestedUrl).searchParams.get('page'), '2')
})

test('desktop youtube remote search extracts video renderers', async () => {
  const initialData = {
    contents: {
      sectionListRenderer: {
        contents: [
          {
            itemSectionRenderer: {
              contents: [
                {
                  videoRenderer: {
                    videoId: 'abc123',
                    title: { runs: [{ text: 'Demo YouTube Video' }] },
                    thumbnail: { thumbnails: [{ url: 'https://i.ytimg.com/vi/abc123/hqdefault.jpg' }] },
                    lengthText: { simpleText: '1:03' },
                    ownerText: {
                      runs: [{
                        text: 'Demo Channel',
                        navigationEndpoint: {
                          browseEndpoint: { browseId: 'UCdemo', canonicalBaseUrl: '/@demo' },
                          commandMetadata: { webCommandMetadata: { url: '/@demo' } },
                        },
                      }],
                    },
                    channelThumbnailSupportedRenderers: {
                      channelThumbnailWithLinkRenderer: {
                        thumbnail: {
                          thumbnails: [{ url: 'https://yt3.ggpht.com/demo-avatar=s88-c-k-c0x00ffffff-no-rj' }],
                        },
                      },
                    },
                    publishedTimeText: { simpleText: '2 days ago' },
                  },
                },
              ],
            },
          },
        ],
      },
    },
  }

  const searchResult = await searchYouTubeVideos({
    query: 'demo',
    limit: 5,
    buildCookieHeader,
    fetchImpl: async () => htmlResponse(`
      <script>ytcfg.set({"INNERTUBE_API_KEY":"test-key","INNERTUBE_CONTEXT":{"client":{"clientName":"WEB","clientVersion":"1.0"}}});</script>
      <script>var ytInitialData = ${JSON.stringify(initialData)};</script>
    `),
  })

  const items = searchResult.items
  assert.equal(items.length, 1)
  assert.equal(items[0].site, 'youtube')
  assert.equal(items[0].url, 'https://www.youtube.com/watch?v=abc123')
  assert.equal(items[0].duration, 63)
  assert.equal(items[0].uploader_url, 'https://www.youtube.com/channel/UCdemo')
  assert.equal(items[0].uploader_avatar, 'https://yt3.ggpht.com/demo-avatar=s88-c-k-c0x00ffffff-no-rj')
  assert.deepEqual(items[0].subscriptions, [{
    id: 'UCdemo',
    type: 'CHANNEL',
    name: 'Demo Channel',
    url: 'https://www.youtube.com/channel/UCdemo',
    avatar: 'https://yt3.ggpht.com/demo-avatar=s88-c-k-c0x00ffffff-no-rj',
    is_nsfw: false,
  }])
  assert.equal(searchResult.has_more, false)
})

test('desktop youtube remote search extracts lockup view models', async () => {
  const initialData = {
    contents: {
      twoColumnSearchResultsRenderer: {
        primaryContents: {
          sectionListRenderer: {
            contents: [
              {
                itemSectionRenderer: {
                  contents: [
                    {
                      lockupViewModel: {
                        contentImage: {
                          thumbnailViewModel: {
                            image: {
                              sources: [{ url: 'https://i.ytimg.com/vi/lock123/hqdefault.jpg' }],
                            },
                            overlays: [
                              {
                                thumbnailBottomOverlayViewModel: {
                                  badges: [
                                    { thumbnailBadgeViewModel: { text: '05:41' } },
                                  ],
                                },
                              },
                            ],
                          },
                        },
                        metadata: {
                          lockupMetadataViewModel: {
                            title: { content: 'Lockup YouTube Video' },
                            metadata: {
                              contentMetadataViewModel: {
                                metadataRows: [
                                  {
                                    metadataParts: [
                                      {
                                        text: {
                                          content: 'Demo Channel',
                                          commandRuns: [
                                            {
                                              text: 'Demo Channel',
                                              onTap: {
                                                innertubeCommand: {
                                                  browseEndpoint: { browseId: 'UCdemo', canonicalBaseUrl: '/@demo' },
                                                  commandMetadata: { webCommandMetadata: { url: '/@demo' } },
                                                },
                                              },
                                            },
                                          ],
                                        },
                                      },
                                      { text: { content: '3 days ago' } },
                                    ],
                                  },
                                ],
                              },
                            },
                          },
                        },
                        rendererContext: {
                          commandContext: {
                            onTap: {
                              innertubeCommand: {
                                watchEndpoint: { videoId: 'lock123' },
                              },
                            },
                          },
                        },
                      },
                    },
                  ],
                },
              },
            ],
          },
        },
      },
    },
  }

  const searchResult = await searchYouTubeVideos({
    query: 'demo',
    limit: 5,
    buildCookieHeader,
    fetchImpl: async () => htmlResponse(`
      <script>ytcfg.set({"INNERTUBE_API_KEY":"test-key","INNERTUBE_CONTEXT":{"client":{"clientName":"WEB","clientVersion":"1.0"}}});</script>
      <script>var ytInitialData = ${JSON.stringify(initialData)};</script>
    `),
  })

  assert.equal(searchResult.items.length, 1)
  assert.equal(searchResult.items[0].title, 'Lockup YouTube Video')
  assert.equal(searchResult.items[0].url, 'https://www.youtube.com/watch?v=lock123')
  assert.equal(searchResult.items[0].duration, 341)
  assert.equal(searchResult.items[0].published_text, '3 days ago')
  assert.equal(searchResult.items[0].uploader_url, 'https://www.youtube.com/channel/UCdemo')
})

test('desktop youtube remote search loads continuation pages', async () => {
  const requests = []
  const initialData = {
    contents: {
      twoColumnSearchResultsRenderer: {
        primaryContents: {
          sectionListRenderer: {
            contents: [
              {
                itemSectionRenderer: {
                  contents: [
                    {
                      videoRenderer: {
                        videoId: 'abc123',
                        title: { runs: [{ text: 'First Page Video' }] },
                      },
                    },
                  ],
                },
              },
              {
                continuationItemRenderer: {
                  continuationEndpoint: {
                    continuationCommand: { token: 'CONTINUATION_1' },
                  },
                },
              },
            ],
          },
        },
      },
    },
  }
  const continuationData = {
    onResponseReceivedCommands: [
      {
        appendContinuationItemsAction: {
          continuationItems: [
            {
              itemSectionRenderer: {
                contents: [
                  {
                    videoRenderer: {
                      videoId: 'def456',
                      title: { runs: [{ text: 'Second Page Video' }] },
                      lengthText: { simpleText: '02:34' },
                    },
                  },
                ],
              },
            },
            {
              continuationItemRenderer: {
                continuationEndpoint: {
                  continuationCommand: { token: 'CONTINUATION_2' },
                },
              },
            },
          ],
        },
      },
    ],
  }

  const searchResult = await searchYouTubeVideos({
    query: 'demo',
    limit: 1,
    page: 2,
    buildCookieHeader,
    fetchImpl: async (url, options = {}) => {
      requests.push({ url, options })
      if (String(url).includes('/youtubei/v1/search')) return jsonResponse(continuationData)
      return htmlResponse(`
        <script>ytcfg.set({"INNERTUBE_API_KEY":"test-key","INNERTUBE_CONTEXT":{"client":{"clientName":"WEB","clientVersion":"1.0"}}});</script>
        <script>var ytInitialData = ${JSON.stringify(initialData)};</script>
      `)
    },
  })

  assert.equal(requests[1].url, 'https://www.youtube.com/youtubei/v1/search?key=test-key')
  assert.equal(requests[1].options.method, 'POST')
  assert.equal(JSON.parse(requests[1].options.body).continuation, 'CONTINUATION_1')
  assert.equal(searchResult.items.length, 1)
  assert.equal(searchResult.items[0].url, 'https://www.youtube.com/watch?v=def456')
  assert.equal(searchResult.items[0].duration, 154)
  assert.equal(searchResult.has_more, true)
})

test('desktop remote search response carries pagination metadata', async () => {
  const searchResult = await searchRemoteVideos({
    query: 'demo',
    site: 'bilibili',
    limit: 1,
    page: 3,
    buildCookieHeader,
    loadDocumentHtml: async () => '',
    fetchImpl: async () => jsonResponse({
      data: {
        result: [
          {
            bvid: 'BV1demo',
            title: 'Demo Video',
            arcurl: 'https://www.bilibili.com/video/BV1demo',
          },
        ],
      },
    }),
  })

  assert.equal(searchResult.page, 3)
  assert.equal(searchResult.has_more, true)
  assert.equal(searchResult.items.length, 1)
})

test('desktop all-site remote search interleaves lightweight site results before limiting', async () => {
  const searchResult = await searchRemoteVideos({
    query: 'demo',
    site: 'all',
    limit: 3,
    page: 1,
    buildCookieHeader,
    loadDocumentHtml: async () => '',
    fetchImpl: async (url) => {
      const targetUrl = new URL(url)
      if (targetUrl.hostname.includes('bilibili')) {
        return jsonResponse({
          data: {
            result: [
              { bvid: 'BV1', title: 'Bilibili 1', arcurl: 'https://www.bilibili.com/video/BV1' },
              { bvid: 'BV2', title: 'Bilibili 2', arcurl: 'https://www.bilibili.com/video/BV2' },
              { bvid: 'BV3', title: 'Bilibili 3', arcurl: 'https://www.bilibili.com/video/BV3' },
            ],
          },
        })
      }
      return htmlResponse('')
    },
  })

  assert.equal(searchResult.items.length, 3)
  assert.deepEqual(searchResult.items.map((item) => item.site), ['bilibili', 'bilibili', 'bilibili'])
  assert.deepEqual(searchResult.sites, ['bilibili', 'youtube'])
})


test('desktop remote search does not wait forever for a stalled site', async () => {
  const searchResult = await searchRemoteVideos({
    query: 'demo',
    site: 'all',
    limit: 3,
    page: 1,
    providerTimeoutMs: 20,
    buildCookieHeader,
    loadDocumentHtml: async () => new Promise(() => {}),
    fetchImpl: async (url) => {
      const targetUrl = new URL(url)
      if (targetUrl.hostname.includes('bilibili')) {
        return jsonResponse({
          data: {
            result: [
              { bvid: 'BV1', title: 'Bilibili 1', arcurl: 'https://www.bilibili.com/video/BV1' },
            ],
          },
        })
      }
      return htmlResponse('')
    },
  })

  assert.deepEqual(searchResult.items.map((item) => item.site), ['bilibili'])
  assert.equal(searchResult.has_more, false)
  assert.equal(searchResult.partial, false)
})

test('desktop all-site remote search returns initial ready sites without waiting for slow sites', async () => {
  const startedAt = Date.now()
  const searchResult = await searchRemoteVideos({
    query: 'demo',
    site: 'all',
    limit: 3,
    page: 1,
    providerTimeoutMs: 10000,
    buildCookieHeader,
    loadDocumentHtml: async () => new Promise(() => {}),
    fetchImpl: async (url) => {
      const targetUrl = new URL(url)
      if (targetUrl.hostname.includes('bilibili')) {
        return jsonResponse({
          data: {
            result: [
              { bvid: 'BV1', title: 'Bilibili 1', arcurl: 'https://www.bilibili.com/video/BV1' },
            ],
          },
        })
      }
      await new Promise((resolve) => setTimeout(resolve, 10000))
      return htmlResponse('')
    },
  })

  assert.ok(Date.now() - startedAt < 5000)
  assert.deepEqual(searchResult.items.map((item) => item.site), ['bilibili'])
  assert.equal(searchResult.has_more, false)
  assert.equal(searchResult.partial, true)
  assert.deepEqual(searchResult.pending_sites, ['youtube'])
})

test('desktop all-site remote search keeps later pages on lightweight sites', async () => {
  const searchResult = await searchRemoteVideos({
    query: 'demo',
    site: 'all',
    limit: 3,
    page: 2,
    providerTimeoutMs: 20,
    buildCookieHeader,
    loadDocumentHtml: async () => '',
    fetchImpl: async () => htmlResponse(''),
  })

  assert.deepEqual(searchResult.sites, ['bilibili', 'youtube'])
})


test('desktop all-site remote search returns later ready pages without waiting for slow sites', async () => {
  const startedAt = Date.now()
  const searchResult = await searchRemoteVideos({
    query: 'demo',
    site: 'all',
    limit: 3,
    page: 2,
    providerTimeoutMs: 10000,
    buildCookieHeader,
    loadDocumentHtml: async () => new Promise(() => {}),
    fetchImpl: async (url) => {
      const targetUrl = new URL(url)
      if (targetUrl.hostname.includes('bilibili')) {
        return jsonResponse({
          data: {
            result: [
              { bvid: 'BV2', title: 'Bilibili 2', arcurl: 'https://www.bilibili.com/video/BV2' },
            ],
          },
        })
      }
      await new Promise((resolve) => setTimeout(resolve, 10000))
      return htmlResponse('')
    },
  })

  assert.ok(Date.now() - startedAt < 5000)
  assert.deepEqual(searchResult.items.map((item) => item.site), ['bilibili'])
  assert.equal(searchResult.partial, true)
  assert.deepEqual(searchResult.pending_sites, ['youtube'])
})

test('desktop bilibili remote channel returns profile and videos', async () => {
  const requestedUrls = []
  const documentUrls = []
  const channelResult = await getRemoteChannel({
    site: 'bilibili',
    url: 'https://space.bilibili.com/12345',
    limit: 5,
    page: 2,
    buildCookieHeader,
    loadDocumentHtml: async (url, options = {}) => {
      documentUrls.push(url)
      assert.equal(typeof options.evaluatePage, 'function')
      return options.evaluatePage(async (script) => {
        if (!script.includes('/x/space/wbi/arc/search')) {
          return {
            dm_img_list: '[]',
            dm_img_str: 'img-demo',
            dm_cover_img_str: 'cover-demo',
            dm_img_inter: '{"demo":true}',
            w_webid: 'webid-demo',
          }
        }

        const match = script.match(/fetch\("([^"]+)"/)
        if (match?.[1]) requestedUrls.push(match[1])
        return {
          status: 200,
          text: JSON.stringify({
            code: 0,
            data: {
              page: {
                count: 20,
              },
              list: {
                vlist: [
                  {
                    bvid: 'BVchannel',
                    title: 'Channel Video',
                    pic: '//i0.hdslb.com/video.jpg',
                    length: '02:03',
                    created: 1700000000,
                  },
                ],
              },
            },
          }),
        }
      })
    },
    fetchImpl: async (url) => {
      requestedUrls.push(url)
      if (url.includes('/x/web-interface/card')) {
        return jsonResponse({
          data: {
            card: {
              name: 'Demo Uploader',
              face: '//i0.hdslb.com/avatar.jpg',
              sign: 'Demo channel',
            },
          },
        })
      }
      if (url.includes('/x/web-interface/nav')) {
        return jsonResponse({
          data: {
            wbi_img: {
              img_url: 'https://i0.hdslb.com/bfs/wbi/0123456789abcdef0123456789abcdef.png',
              sub_url: 'https://i0.hdslb.com/bfs/wbi/fedcba9876543210fedcba9876543210.png',
            },
          },
        })
      }
      throw new Error(`Unexpected request: ${url}`)
    },
  })

  assert.equal(channelResult.site, 'bilibili')
  assert.equal(channelResult.profile.name, 'Demo Uploader')
  assert.equal(channelResult.profile.avatar, 'https://i0.hdslb.com/avatar.jpg')
  assert.equal(channelResult.profile.description, 'Demo channel')
  assert.equal(channelResult.items.length, 1)
  assert.equal(channelResult.items[0].url, 'https://www.bilibili.com/video/BVchannel')
  assert.equal(channelResult.items[0].duration, 123)
  assert.equal(channelResult.has_more, true)
  assert.equal(documentUrls.length, 1)
  const videoRequestUrl = new URL(requestedUrls.find((url) => url.includes('/x/space/wbi/arc/search')))
  assert.equal(videoRequestUrl.searchParams.get('pn'), '2')
  assert.equal(videoRequestUrl.searchParams.get('dm_img_str'), 'img-demo')
  assert.equal(videoRequestUrl.searchParams.get('dm_cover_img_str'), 'cover-demo')
  assert.equal(videoRequestUrl.searchParams.get('dm_img_inter'), '{"demo":true}')
  assert.equal(videoRequestUrl.searchParams.get('w_webid'), 'webid-demo')
  assert.equal(videoRequestUrl.searchParams.has('w_rid'), true)
})

test('desktop youtube remote channel parses channel page videos', async () => {
  const initialData = {
    metadata: {
      channelMetadataRenderer: {
        title: 'Demo Channel',
        externalId: 'UCdemo',
        description: 'Demo description',
      },
    },
    contents: {
      twoColumnBrowseResultsRenderer: {
        tabs: [
          {
            tabRenderer: {
              content: {
                richGridRenderer: {
                  contents: [
                    {
                      continuationItemRenderer: {
                        continuationEndpoint: {
                          continuationCommand: { token: 'CONTINUATION_1' },
                        },
                      },
                    },
                    {
                      richItemRenderer: {
                        content: {
                          videoRenderer: {
                            videoId: 'abc123',
                            title: { runs: [{ text: 'Channel Video' }] },
                            thumbnail: { thumbnails: [{ url: 'https://i.ytimg.com/vi/abc123/hqdefault.jpg' }] },
                            lengthText: { simpleText: '03:04' },
                            publishedTimeText: { simpleText: '1 day ago' },
                          },
                        },
                      },
                    },
                  ],
                },
              },
            },
          },
        ],
      },
    },
  }

  let requestedUrl = ''
  const channelResult = await getRemoteChannel({
    site: 'youtube',
    url: 'https://www.youtube.com/@demo',
    limit: 5,
    buildCookieHeader,
    fetchImpl: async (url) => {
      requestedUrl = url
      return htmlResponse(`
        <script>ytcfg.set({"INNERTUBE_API_KEY":"test-key","INNERTUBE_CONTEXT":{"client":{"clientName":"WEB","clientVersion":"1.0"}}});</script>
        <script>var ytInitialData = ${JSON.stringify(initialData)};</script>
      `)
    },
  })

  assert.equal(requestedUrl, 'https://www.youtube.com/@demo/videos')
  assert.equal(channelResult.profile.id, 'UCdemo')
  assert.equal(channelResult.profile.name, 'Demo Channel')
  assert.equal(channelResult.profile.description, 'Demo description')
  assert.equal(channelResult.items.length, 1)
  assert.equal(channelResult.items[0].url, 'https://www.youtube.com/watch?v=abc123')
  assert.equal(channelResult.items[0].duration, 184)
  assert.deepEqual(channelResult.items[0].subscriptions, [channelResult.profile])
  assert.equal(channelResult.has_more, true)
  assert.equal(channelResult.next_cursor.continuation, 'CONTINUATION_1')
})

test('desktop youtube remote channel parses lockup view model videos', async () => {
  const initialData = {
    metadata: {
      channelMetadataRenderer: {
        title: 'Modern Channel',
        externalId: 'UCmodern',
      },
    },
    contents: {
      richGridRenderer: {
        contents: [
          {
            richItemRenderer: {
              content: {
                lockupViewModel: {
                  contentImage: {
                    thumbnailViewModel: {
                      image: {
                        sources: [{ url: 'https://i.ytimg.com/vi/lock123/hqdefault.jpg' }],
                      },
                      overlays: [
                        {
                          thumbnailBottomOverlayViewModel: {
                            badges: [
                              { thumbnailBadgeViewModel: { text: '01:17' } },
                            ],
                          },
                        },
                      ],
                    },
                  },
                  metadata: {
                    lockupMetadataViewModel: {
                      title: { content: 'Modern Channel Video' },
                      metadata: {
                        contentMetadataViewModel: {
                          metadataRows: [
                            {
                              metadataParts: [
                                { text: { content: '2.5K views' } },
                                { text: { content: '8 days ago' } },
                              ],
                            },
                          ],
                        },
                      },
                    },
                  },
                  rendererContext: {
                    commandContext: {
                      onTap: {
                        innertubeCommand: {
                          watchEndpoint: { videoId: 'lock123' },
                        },
                      },
                    },
                  },
                },
              },
            },
          },
        ],
      },
    },
  }

  const channelResult = await getRemoteChannel({
    site: 'youtube',
    url: 'https://www.youtube.com/@modern',
    limit: 5,
    buildCookieHeader,
    fetchImpl: async () => htmlResponse(`
      <script>ytcfg.set({"INNERTUBE_API_KEY":"test-key","INNERTUBE_CONTEXT":{"client":{"clientName":"WEB","clientVersion":"1.0"}}});</script>
      <script>var ytInitialData = ${JSON.stringify(initialData)};</script>
    `),
  })

  assert.equal(channelResult.profile.id, 'UCmodern')
  assert.equal(channelResult.items.length, 1)
  assert.equal(channelResult.items[0].title, 'Modern Channel Video')
  assert.equal(channelResult.items[0].url, 'https://www.youtube.com/watch?v=lock123')
  assert.equal(channelResult.items[0].duration, 77)
  assert.equal(channelResult.items[0].published_text, '8 days ago')
})

test('desktop youtube remote channel uses profile channel id for page requests', async () => {
  const initialData = {
    metadata: {
      channelMetadataRenderer: {
        title: 'Demo Channel',
        externalId: 'UCdemo',
      },
    },
    contents: {
      richGridRenderer: {
        contents: [],
      },
    },
  }

  let requestedUrl = ''
  await getRemoteChannel({
    site: 'youtube',
    url: 'https://www.youtube.com/@Demo Channel',
    limit: 5,
    profile: {
      id: 'UCdemo',
      name: 'Demo Channel',
      url: 'https://www.youtube.com/@Demo Channel',
      avatar: '',
    },
    buildCookieHeader,
    fetchImpl: async (url) => {
      requestedUrl = url
      return htmlResponse(`
        <script>ytcfg.set({"INNERTUBE_API_KEY":"test-key","INNERTUBE_CONTEXT":{"client":{"clientName":"WEB","clientVersion":"1.0"}}});</script>
        <script>var ytInitialData = ${JSON.stringify(initialData)};</script>
      `)
    },
  })

  assert.equal(requestedUrl, 'https://www.youtube.com/channel/UCdemo/videos')
})

test('desktop youtube remote channel loads continuation videos', async () => {
  const requests = []
  const channelResult = await getRemoteChannel({
    site: 'youtube',
    url: 'https://www.youtube.com/@demo',
    limit: 5,
    page: 2,
    cursor: {
      continuation: 'CONTINUATION_1',
      api_key: 'test-key',
      context: { client: { clientName: 'WEB', clientVersion: '1.0' } },
    },
    profile: {
      id: 'UCdemo',
      name: 'Demo Channel',
      url: 'https://www.youtube.com/@demo',
      avatar: '',
    },
    buildCookieHeader,
    fetchImpl: async (url, options = {}) => {
      requests.push({ url, options })
      return jsonResponse({
        onResponseReceivedActions: [
          {
            appendContinuationItemsAction: {
              continuationItems: [
                {
                  richItemRenderer: {
                    content: {
                      videoRenderer: {
                        videoId: 'def456',
                        title: { runs: [{ text: 'Continuation Video' }] },
                        thumbnail: { thumbnails: [{ url: 'https://i.ytimg.com/vi/def456/hqdefault.jpg' }] },
                        lengthText: { simpleText: '04:05' },
                      },
                    },
                  },
                },
                {
                  continuationItemRenderer: {
                    continuationEndpoint: {
                      continuationCommand: { token: 'CONTINUATION_2' },
                    },
                  },
                },
              ],
            },
          },
        ],
      })
    },
  })

  assert.equal(requests[0].url, 'https://www.youtube.com/youtubei/v1/browse?key=test-key')
  assert.equal(requests[0].options.method, 'POST')
  assert.equal(JSON.parse(requests[0].options.body).continuation, 'CONTINUATION_1')
  assert.equal(channelResult.items.length, 1)
  assert.equal(channelResult.items[0].url, 'https://www.youtube.com/watch?v=def456')
  assert.equal(channelResult.items[0].duration, 245)
  assert.equal(channelResult.has_more, true)
  assert.equal(channelResult.next_cursor.continuation, 'CONTINUATION_2')
})

