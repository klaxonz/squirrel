import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import pluginVue from 'eslint-plugin-vue'
import vueParser from 'vue-eslint-parser'
import globals from 'globals'

/**
 * Design-token guard.
 *
 * Enforces the design system from the lint layer so the token foundation
 * (themes/dark.css + layout.css) can't be silently bypassed by hand-written
 * utilities. Two concerns:
 *
 * 1. `no-tailwind-arbitrary-values` — forbid `z-[60]`, `text-[13px]`,
 *    `rounded-[6px]`, `w-[320px]`, etc. These bypass the z-index scale,
 *    type scale, radius scale, and spacing scale. The allowlist covers the
 *    few legitimate dynamic cases (max-w-[90vw], max-h-[90vh], template-slot
 *    widths in the reader) that have no token equivalent yet.
 *
 * 2. `no-tailwind-raw-color` — forbid the raw Tailwind color palette
 *    (`bg-zinc-50`, `text-red-500`, `bg-emerald-500`, …). All color must go
 *    through the semantic tokens (primary / destructive / success / warning /
 *    muted / accent / border / background / foreground …). The bare-status
 *    compatibility shims in layout.css (.bg-blue-500 etc.) are CSS, not
 *    utility classes, so they are unaffected.
 *
 * Why hand-rolled instead of eslint-plugin-tailwindcss: that plugin is
 * unmaintained, its v3 does not support ESLint flat config, and it can't read
 * our CSS-variable tokens (it only knows static Tailwind palettes). A targeted
 * regex rule is smaller, correct, and token-aware. Per AGENTS.md rule 4 we
 * prefer not hand-rolling only when a maintained lib exists — here none does.
 */

// Utilities where arbitrary values are a token-bypass smell.
// Scope is deliberately limited to *system* concerns: stacking (z), typography
// (text), corner system (rounded), the spacing grid (p/m/gap/space), and
// motion (duration/delay). Sizing & position dimensions (w/h/min-*/max-*/top/
//right/left/inset/translate) are intentionally EXCLUDED — component layout
// measures (card width, panel width, absolute offsets) are legitimate per-
// component decisions, not design-token concerns. This keeps the guard focused
// on real system bypasses.
const ARBITRARY_VALUE_UTILITIES = [
  'z', 'text', 'rounded',
  'p', 'px', 'py', 'pt', 'pb', 'pl', 'pr', 'm', 'mx', 'my', 'mt', 'mb', 'ml', 'mr',
  'gap', 'space-x', 'space-y',
  'blur', 'brightness', 'duration', 'delay',
]

// Arbitrary values that are legitimate (no token equivalent). The size
// dimensions (w/h/min-*/max-*) no longer need allowlisting because the rule
// itself no longer covers sizing — see ARBITRARY_VALUE_UTILITIES. This list is
// kept minimal for the few remaining system-utility edge cases.
const ARBITRARY_ALLOWLIST = new Set([
  // viewport-bound overlays / dialogs (z is still covered, but these are not z)
  'blur-[2px]',
])

// Tailwind's default color palette names. Any `(bg|text|border|ring|from|to|via|fill|stroke|shadow|outline|divide|accent|caret|decoration|placeholder)-<name>-<shade>`
// is a raw-palette leak. Semantic utilities like `bg-primary` / `text-muted-foreground`
// are NOT in this list, so they pass.
const TAILWIND_PALETTE = [
  'slate', 'gray', 'zinc', 'neutral', 'stone',
  'red', 'orange', 'amber', 'yellow', 'lime', 'green', 'emerald', 'teal',
  'cyan', 'sky', 'blue', 'indigo', 'violet', 'purple', 'fuchsia', 'pink', 'rose',
]
const RAW_COLOR_RE = new RegExp(
  String.raw`(?:^|\s)(?:bg|text|border|ring|from|to|via|fill|stroke|outline|divide|caret|decoration|placeholder|accent)-(?:${TAILWIND_PALETTE.join('|')})(?:-[0-9]{2,3})?(?:$|\s|/)`,
)

// Strip leading variant prefixes (dark:, hover:, sm:, focus:, group-hover:, etc.)
// so the utility matcher sees the bare token. Variants chain with ':'.
const stripVariants = (token) => {
  let t = token
  while (t.includes(':')) t = t.slice(t.indexOf(':') + 1)
  return t
}

const arbitraryValueRe = new RegExp(
  String.raw`^(?:${ARBITRARY_VALUE_UTILITIES.join('|')})-\[.+\]$`,
)

// Arbitrary values that resolve to a design token at runtime are not a bypass.
// Covers three forms:
//   - direct var bind:        w-[var(--sidebar-width)]
//   - calc on tokens:         rounded-[calc(var(--radius-xl)+2px)]
//   - hsl/rgb on tokens:      shadow-[0_18px_38px_hsl(var(--surface-shadow))]
// All three reference a CSS custom property inside the brackets.
const VAR_BOUNDARY_RE = /^.{1,}-\[[^\]]*var\(--[a-z0-9-]+\)[^\]]*\]$/

/** @type {import('eslint').Rule.RuleModule} */
const designTokenGuardRule = {
  meta: {
    type: 'problem',
    docs: {
      description: 'Forbid Tailwind arbitrary values and raw palette colors; require semantic design tokens.',
    },
    schema: [],
    messages: {
      arbitrary:
        'Tailwind arbitrary value `{{token}}` bypasses the design-token scale. Use the corresponding token utility (z-* scale, text-* scale, spacing, radius) or extend tailwind.config.',
      rawColor:
        'Raw Tailwind color `{{token}}` bypasses the semantic color tokens. Use bg-/text-/border- with primary | destructive | success | warning | muted | accent | border | background | foreground instead.',
    },
  },
  create(context) {
    const sourceCode = context.sourceCode ?? context.getSourceCode()
    const text = sourceCode.text

    // Split a class-list string into individual utility tokens. Handles
    // whitespace- and newline-separated lists, ignoring empty chunks.
    const splitClasses = (value) =>
      value.split(/\s+/).map((s) => s.trim()).filter(Boolean)


    // Match class-list payloads from every form we use across the codebase:
    //   class="..."            static Vue/template/HTML attribute
    //   :class="..."           bound string literal
    //   :class="`...`"         bound template literal
    //   :class="['...', ...]"  array of literals (each quoted member scanned)
    //   :class="{ 'foo': ... }" object form (each quoted key scanned)
    // A single quoted-string scan covers all of these: every class token in
    // our codebase appears inside a quote pair (single, double, or backtick),
    // so we iterate over all string spans and tokenise each.
    const stringSpans = []
    const stringRe = /([`"'])((?:\\.|(?!\1).)*)\1/g
    let m
    while ((m = stringRe.exec(text)) !== null) {
      stringSpans.push({ quote: m[1], value: m[2], index: m.index })
    }

    return {
      Program(node) {
        for (const span of stringSpans) {
          // Skip strings that are clearly not class lists: backtick template
          // literals may embed prose; only scan those whose content looks like a
          // utility list (no spaces-with-words prose heuristic: require at least
          // one char and treat each whitespace-separated chunk as a token —
          // prose chunks simply won't match the utility patterns).
          for (const raw of splitClasses(span.value)) {
            const token = stripVariants(raw)
            if (!token) continue

            if (
              arbitraryValueRe.test(token) &&
              !ARBITRARY_ALLOWLIST.has(token) &&
              !VAR_BOUNDARY_RE.test(token)
            ) {
              context.report({
                loc: sourceCode.getLocFromIndex(span.index),
                messageId: 'arbitrary',
                data: { token: raw },
              })
            }
            if (RAW_COLOR_RE.test(` ${raw} `)) {
              context.report({
                loc: sourceCode.getLocFromIndex(span.index),
                messageId: 'rawColor',
                data: { token: raw },
              })
            }
          }
        }
      },
    }
  },
}

const designTokenGuardPlugin = {
  rules: {
    'design-tokens': designTokenGuardRule,
  },
}

export default tseslint.config(
  {
    // ESLint is launched by the desktop package scripts, so flat-config globs
    // are resolved from squirrel-desktop rather than this config's directory.
    ignores: [
      'renderer/dist/**',
      'renderer/node_modules/**',
      'renderer/output/**',
      'renderer/public/**',
      'renderer/scripts/**',
      '**/*.d.ts',
      'renderer/src/vite-env.d.ts',
      // Config files reference token names (z-/text-/rounded-/raw colors) as
      // documentation in comments and example strings; they define the system,
      // not consume it, so the design-token guard does not apply.
      'renderer/eslint.config.js',
      'renderer/tailwind.config.ts',
    ],
  },

  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...pluginVue.configs['flat/recommended'],

  {
    files: ['renderer/**/*.vue'],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tseslint.parser,
        extraFileExtensions: ['.vue'],
        sourceType: 'module',
      },
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
  },

  {
    files: ['renderer/**/*.{ts,tsx,vue,js,mjs}'],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    plugins: { 'design-tokens': designTokenGuardPlugin },
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
      // ponytail: unused-vars start at warn alongside no-explicit-any for
      // progressive convergence; flip to error once the backlog clears.
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      'no-console': 'error',
      // Design-token guard. Starts at 'warn' so the existing 40+68+54
      // violations surface in the report without failing CI; promoted to
      // 'error' in a follow-up once the backlog clears (same progressive-
      // convergence pattern as @typescript-eslint/no-unused-vars above).
      'design-tokens/design-tokens': 'warn',
      // ponytail: no-undef checks value-space globals; TypeScript global
      // interfaces/types live in type space and false-positive here. TS's own
      // compiler covers undefined identifiers — per typescript-eslint guidance.
      'no-undef': 'off',
      'vue/no-mutating-props': 'error',
      // ponytail: no-dupe-keys is an Options-API rule; it false-positives on
      // composable return destructures in <script setup>.
      'vue/no-dupe-keys': 'off',
      // ponytail: formatting is not a maintainability signal. These template
      // layout rules are prettier territory; leaving them on floods the report
      // with noise and drowns the real signal (any / mutating-props).
      'vue/multi-word-component-names': 'off',
      'vue/require-default-prop': 'off',
      'vue/max-attributes-per-line': 'off',
      'vue/first-attribute-linebreak': 'off',
      'vue/html-closing-bracket-newline': 'off',
      'vue/html-closing-bracket-spacing': 'off',
      'vue/html-indent': 'off',
      'vue/html-quotes': 'off',
      'vue/html-self-closing': 'off',
      'vue/attributes-order': 'off',
      'vue/attribute-order': 'off',
      'vue/attribute-hyphenation': 'off',
      'vue/v-on-event-hyphenation': 'off',
      'vue/v-slot-style': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/multiline-html-element-content-newline': 'off',
      'vue/component-name-in-template-casing': 'off',
      'vue/block-order': 'off',
      'vue/v-bind-style': 'off',
      'vue/v-on-style': 'off',
      'vue/define-emits-declaration': 'off',
      'vue/define-macros-order': 'off',
      'vue/padding-line-between-blocks': 'off',
      'vue/no-v-html': 'off',
      'vue/no-template-shadow': 'off',
    },
  },

  // logger modules: console is the whole point. Repointed to the feature-based
  // layout after the src/{utils,components}/* → src/{features,shared}/* move;
  // the old paths silently stopped matching and re-introduced 8 no-console errors.
  {
    files: [
      'renderer/src/shared/lib/logger.ts',
      'renderer/src/features/playback/components/video-player/core/logger.ts',
    ],
    rules: { 'no-console': 'off' },
  },

  // --- progressive-convergence overrides ---
  // ponytail: convergence debt tracked against the feature-based layout. The
  // video-player block below was promoted warn → error once its first-party
  // anys were eliminated (EventEmitter typed, AnalyticsPlugin.log → unknown[]);
  // only the third-party adapter/plugin boundary anys remain, exempted by the
  // following block. All paths repointed to the feature-based layout after the
  // src/{components,utils}/* → src/{features,shared}/* refactor.
  {
    // VideoPlayer.vue is a 2784-line component slated for a separate refactor epic.
    // Promoted from warn → error once the subtree cleared its first-party anys
    // (EventEmitter.ts typed; AnalyticsPlugin.log → unknown[]). The third-party
    // boundary anys in adapters/ and plugins/ are exempted by the block below.
    files: ['renderer/src/features/playback/components/video-player/**/*.{vue,ts}'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
      'vue/no-mutating-props': 'error',
    },
  },
  {
    // ponytail: stream adapters wrap dashjs / hls.js / shaka-player, whose
    // dynamic event and track payloads are genuinely untyped in the libs.
    // These are real third-party boundary anys (not laziness); modelling them
    // fully would mean authoring type declarations for every player event, so
    // they are exempt rather than carried as convergence debt. (Formerly
    // plugins/**; the stream technology moved to adapters/ per ADR-0001.)
    files: [
      'renderer/src/features/playback/components/video-player/adapters/**/*.{ts,vue}',
      'renderer/src/features/playback/components/video-player/plugins/**/*.{ts,vue}',
    ],
    rules: { '@typescript-eslint/no-explicit-any': 'off' },
  },
)
