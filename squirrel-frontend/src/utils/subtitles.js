// 字幕解析工具：提供 VTT/SRT 解析为 TextTrackCue 的方法

export function getCueClass() {
  if (typeof window === 'undefined') return null;
  return window.VTTCue || window.TextTrackCue || window.WebKitTextTrackCue || null;
}

function parseTimeCode(timeStr) {
  const parts = String(timeStr).split(':');
  const seconds = parseFloat(parts.pop());
  const minutes = parseInt(parts.pop() || 0, 10);
  const hours = parseInt(parts.pop() || 0, 10);
  return hours * 3600 + minutes * 60 + seconds;
}

export function parseVTT(vttText, track, options = {}) {
  if (!vttText || !track) return;
  const lines = vttText.split('\n');
  let i = 0;
  while (i < lines.length && !lines[i].includes('-->')) i++;

  const Cue = getCueClass();
  if (!Cue) return;

  const pos = options.position || 'bottom';

  while (i < lines.length) {
    const timeLine = lines[i];
    if (timeLine.includes('-->')) {
      const [startStr, endStr] = timeLine.split('-->').map((t) => String(t).trim());
      const start = parseTimeCode(startStr);
      const end = parseTimeCode(endStr);
      i++;

      let text = '';
      while (i < lines.length && lines[i].trim() !== '') {
        text += lines[i] + '\n';
        i++;
      }
      if (text.trim()) {
        const cue = new Cue(start, end, text.trim());
        try {
          cue.snapToLines = false;
          cue.line = pos === 'top' ? 10 : 90;
          cue.align = 'center';
        } catch (_) {}
        track.addCue(cue);
      }
    }
    i++;
  }
}

export function parseSRT(srtText, track, options = {}) {
  if (!srtText || !track) return;
  const blocks = srtText.replace(/\r/g, '').split(/\n\s*\n/);
  const timeRegex = /(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})/;

  const toSeconds = (h, m, s, ms) => {
    return parseInt(h, 10) * 3600 + parseInt(m, 10) * 60 + parseInt(s, 10) + parseInt(ms, 10) / 1000;
  };

  const Cue = getCueClass();
  if (!Cue) return;

  const pos = options.position || 'bottom';

  for (const block of blocks) {
    const lines = block.split('\n').filter((l) => l.trim().length > 0);
    if (lines.length < 2) continue;

    // 可选序号
    let cursor = 0;
    if (/^\d+$/.test(lines[0].trim())) cursor = 1;

    const timeLine = lines[cursor]?.trim();
    const match = timeRegex.exec(timeLine || '');
    if (!match) continue;

    const start = toSeconds(match[1], match[2], match[3], match[4]);
    const end = toSeconds(match[5], match[6], match[7], match[8]);
    const text = lines.slice(cursor + 1).join('\n').trim();
    if (!text) continue;

    const cue = new Cue(start, end, text);
    try {
      cue.snapToLines = false;
      cue.line = pos === 'top' ? 10 : 90;
      cue.align = 'center';
    } catch (_) {}
    track.addCue(cue);
  }
}

export default { getCueClass, parseVTT, parseSRT };

