import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import pluginVue from 'eslint-plugin-vue'
import vueParser from 'vue-eslint-parser'
import globals from 'globals'

export default tseslint.config(
  {
    ignores: [
      'dist/**',
      'node_modules/**',
      'output/**',
      'public/**',
      '**/*.d.ts',
      'src/vite-env.d.ts',
    ],
  },

  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...pluginVue.configs['flat/recommended'],

  {
    files: ['**/*.vue'],
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
    files: ['**/*.{ts,tsx,vue,js,mjs}'],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
      // ponytail: unused-vars start at warn alongside no-explicit-any for
      // progressive convergence; flip to error once the backlog clears.
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      'no-console': 'error',
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

  // logger modules: console is the whole point
  {
    files: ['src/utils/logger.ts', 'src/components/video-player/core/logger.ts'],
    rules: { 'no-console': 'off' },
  },

  // --- progressive-convergence overrides (remove each block once clean) ---
  // ponytail: these start as warn so error-level doesn't block; flip to error
  // (or delete the override) once each area is fully typed. Tracked in the
  // frontend maintainability refactor (Phase 4).
  {
    // VideoPlayer.vue is a 2784-line component slated for a separate refactor epic;
    // keep its any-usage non-blocking until then.
    files: ['src/components/video-player/**/*.{vue,ts}'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'warn',
      'vue/no-mutating-props': 'warn',
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
      'src/components/video-player/adapters/**/*.{ts,vue}',
      'src/components/video-player/plugins/**/*.{ts,vue}',
    ],
    rules: { '@typescript-eslint/no-explicit-any': 'off' },
  },
  {
    // ponytail: shadcn-vue/reka generated primitives. Hand-editing these fights
    // upstream regenerations; their any usage stays non-blocking permanently.
    files: ['src/components/ui/**/*.{vue,ts}'],
    rules: { '@typescript-eslint/no-explicit-any': 'off' },
  },
)
