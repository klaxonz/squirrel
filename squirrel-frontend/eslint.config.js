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

  // logger modules: console is the whole point. Repointed to the feature-based
  // layout after the src/{utils,components}/* → src/{features,shared}/* move;
  // the old paths silently stopped matching and re-introduced 8 no-console errors.
  {
    files: [
      'src/shared/lib/logger.ts',
      'src/features/playback/components/video-player/core/logger.ts',
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
    files: ['src/features/playback/components/video-player/**/*.{vue,ts}'],
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
      'src/features/playback/components/video-player/adapters/**/*.{ts,vue}',
      'src/features/playback/components/video-player/plugins/**/*.{ts,vue}',
    ],
    rules: { '@typescript-eslint/no-explicit-any': 'off' },
  },
  {
    // ponytail: shadcn-vue/reka generated primitives. Hand-editing these fights
    // upstream regenerations; their any usage stays non-blocking permanently.
    files: ['src/shared/ui/**/*.{vue,ts}'],
    rules: { '@typescript-eslint/no-explicit-any': 'off' },
  },
)
