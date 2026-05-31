# Squirrel Music API

This sidecar runs MakcRe/KuGouMusicApi for Squirrel music search and playback URL resolution.

## Local Dev

```powershell
npm install
$env:PORT=8003
$env:HOST='127.0.0.1'
$env:platform='lite'
npm run start
```

Then set the backend environment:

```env
KUGOU_MUSIC_API_BASE_URL=http://127.0.0.1:8003
```

Some KuGou endpoints require a valid KuGou cookie:

```env
KUGOU_MUSIC_COOKIE=token=...;userid=...;dfid=...
```
