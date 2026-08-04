import readline from 'node:readline';

import { resolveYoutubeiPayload } from './youtubei_core.mjs';

const rl = readline.createInterface({
  input: process.stdin,
  crlfDelay: Infinity,
});

for await (const line of rl) {
  if (!line.trim()) {
    continue;
  }

  let payload;
  try {
    payload = JSON.parse(line);
  } catch (error) {
    process.stdout.write(`${JSON.stringify({
      status: 'error',
      error: {
        type: error?.name || 'Error',
        message: error?.message || String(error),
      },
    })}\n`);
    continue;
  }

  try {
    const response = await resolveYoutubeiPayload(payload);
    process.stdout.write(`${JSON.stringify(response)}\n`);
  } catch (error) {
    process.stdout.write(`${JSON.stringify({
      status: 'error',
      error: {
        type: error?.name || 'Error',
        message: error?.message || String(error),
      },
    })}\n`);
  }
}
