import { Command } from 'commander';
import fs from 'node:fs';
import path from 'node:path';

import { SessionManager } from './session_manager.js';


let cachedir;
const homeDirectory = process.env.HOME || process.env.USERPROFILE;
const { XDG_CACHE_HOME } = process.env;
if (XDG_CACHE_HOME !== undefined) {
  cachedir = path.resolve(XDG_CACHE_HOME, 'bgutil-ytdlp-pot-provider');
} else if (homeDirectory) {
  cachedir = path.resolve(homeDirectory, '.cache', 'bgutil-ytdlp-pot-provider');
} else {
  cachedir = path.resolve(import.meta.dirname, '..');
}

if (!fs.existsSync(cachedir)) {
  fs.mkdirSync(cachedir, { recursive: true });
}

const CACHE_PATH = path.resolve(cachedir, 'cache.json');
const program = new Command()
  .option('-c, --content-binding <content-binding>')
  .option('-v, --visitor-data <visitordata>')
  .option('-d, --data-sync-id <data-sync-id>')
  .option('-p, --proxy <proxy-all>')
  .option('-b, --bypass-cache')
  .option('-s, --source-address <source-address>')
  .option('--innertube-context <innertube-context>')
  .option('--disable-tls-verification')
  .option('--version')
  .option('--verbose')
  .exitOverride();

try {
  program.parse();
} catch (err) {
  if (err.code === 'commander.unknownOption') {
    console.log();
    program.outputHelp();
  }
}

const options = program.opts();

(async () => {
  if (options.version) {
    console.log('1.3.1');
    process.exit(0);
  }

  if (options.dataSyncId) {
    console.error('Data sync id is deprecated, use --content-binding instead');
    process.exit(1);
  }

  if (options.visitorData) {
    console.error('Visitor data is deprecated, use --content-binding instead');
    process.exit(1);
  }

  const cache = {};
  if (fs.existsSync(CACHE_PATH)) {
    try {
      const parsedCaches = JSON.parse(fs.readFileSync(CACHE_PATH, 'utf8'));
      for (const contentBinding in parsedCaches) {
        const parsedCache = parsedCaches[contentBinding];
        if (!parsedCache) {
          continue;
        }
        const expiresAt = new Date(parsedCache.expiresAt);
        if (!Number.isNaN(expiresAt.getTime())) {
          cache[contentBinding] = {
            poToken: parsedCache.poToken,
            expiresAt,
            contentBinding,
          };
        }
      }
    } catch (err) {
      console.warn(`Error parsing cache. err = ${err}`);
    }
  }

  const sessionManager = new SessionManager(options.verbose || false, cache);

  try {
    const sessionData = await sessionManager.generatePoToken(
      options.contentBinding,
      options.proxy || '',
      options.bypassCache || false,
      options.sourceAddress,
      options.disableTlsVerification || false,
      undefined,
      options.innertubeContext !== undefined ? JSON.parse(options.innertubeContext) : undefined,
    );

    try {
      fs.writeFileSync(
        CACHE_PATH,
        JSON.stringify(sessionManager.getYoutubeSessionDataCaches(true)),
        'utf8',
      );
    } catch (err) {
      console.warn(`Error writing cache. err = ${err}`);
    } finally {
      console.log(JSON.stringify(sessionData));
    }
  } catch (err) {
    console.error(`Failed while generating POT. err = ${err}`);
    console.log(JSON.stringify({}));
    process.exit(1);
  }
})();
