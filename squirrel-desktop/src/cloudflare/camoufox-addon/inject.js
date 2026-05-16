async function loadScripts() {
  try {
    const registryResponse = await fetch(chrome.runtime.getURL('scripts/registry.json'))
    const registry = await registryResponse.json()

    for (const scriptFile of registry) {
      const scriptResponse = await fetch(chrome.runtime.getURL(`scripts/${scriptFile}`))
      const scriptContent = await scriptResponse.text()
      const script = document.createElement('script')
      script.textContent = scriptContent
      document.documentElement.appendChild(script)
      script.remove()
    }
  } catch {
  }
}

void loadScripts()
