import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const readSource = (relativePath: string) =>
  readFileSync(new URL(relativePath, import.meta.url), 'utf8')

const authCard = readSource('./components/AuthEntryCard.vue')
const authStyles = readSource('./styles/auth-entry.css')
const entryViews = [
  readSource('./views/Login.vue'),
  readSource('./views/Register.vue'),
  readSource('../settings/views/ServerConfig.vue'),
]

describe('Aura auth entry contract', () => {
  it('uses one centered Card composition for every unauthenticated entry form', () => {
    expect(authCard).toContain('<PrimeCard')
    expect(authCard).toContain('<header class="auth-entry__header">')
    expect(authCard).toContain('<div class="auth-entry__content">')
    expect(authStyles).toMatch(/\.auth-entry\s*\{[^}]*place-items:\s*center;/s)
    expect(authStyles).toMatch(/\.auth-entry__stack\s*\{[^}]*width:\s*min\(100%,\s*24rem\);/s)

    for (const source of entryViews) {
      expect(source).toContain('<AuthEntryCard')
    }
  })

  it('does not restore the old editorial split or atmospheric decoration', () => {
    const combined = [authCard, authStyles, ...entryViews].join('\n')

    expect(combined).not.toMatch(/auth-brand|auth-shell__layout|auth-shell__atmosphere/)
    expect(authStyles).not.toMatch(/(?:linear|radial)-gradient|@keyframes/)
  })

  it('keeps form controls on shared PrimeVue-backed adapters', () => {
    const login = entryViews[0]
    const register = entryViews[1]
    const serverConfig = entryViews[2]

    expect(login).toContain("import { Checkbox } from '@/shared/ui/checkbox'")
    expect(login).toContain("import { Input } from '@/shared/ui/input'")
    expect(register).toContain("import { Button } from '@/shared/ui/button'")
    expect(serverConfig).toContain('class="auth-server-field"')
    expect(serverConfig).toContain('severity="secondary" outlined')
  })
})
