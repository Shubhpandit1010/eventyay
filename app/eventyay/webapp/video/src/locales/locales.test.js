import test from 'node:test'
import assert from 'node:assert/strict'
import {
	locales,
	resolveLanguageOptions,
	resolveCurrentLanguage,
} from './index.js'

test('resolveLanguageOptions returns all locales by default', () => {
	const result = resolveLanguageOptions()
	assert.equal(result.length, locales.length)
	assert.ok(result.some(l => l.code === 'en'))
})

test('resolveLanguageOptions filters by array of string codes and normalizes case/underscores', () => {
	const result = resolveLanguageOptions(['DE', 'en_US', 'FR'])
	assert.equal(result.length, 3)
	assert.deepEqual(
		result.map(l => l.code).sort(),
		['de', 'en-us', 'fr'].sort()
	)
})

test('resolveLanguageOptions falls back to all locales if string array contains no matches', () => {
	const result = resolveLanguageOptions(['non_existent_1', 'non_existent_2'])
	assert.equal(result.length, locales.length)
})

test('resolveLanguageOptions preserves object array configuration', () => {
	const custom = [
		{ code: 'custom-1', label: 'Custom 1' },
		{ code: 'custom-2', nativeLabel: 'Custom 2 Native' }
	]
	const result = resolveLanguageOptions(custom)
	assert.equal(result.length, 2)
	assert.equal(result[0].code, 'custom-1')
	assert.equal(result[0].nativeLabel, 'Custom 1')
	assert.equal(result[1].code, 'custom-2')
	assert.equal(result[1].nativeLabel, 'Custom 2 Native')
})

test('resolveCurrentLanguage matches exact language code case-insensitively', () => {
	const available = [
		{ code: 'en', nativeLabel: 'English' },
		{ code: 'de', nativeLabel: 'Deutsch' },
		{ code: 'fr', nativeLabel: 'Français' },
	]
	assert.equal(resolveCurrentLanguage(available, 'DE'), 'de')
	assert.equal(resolveCurrentLanguage(available, 'en'), 'en')
	assert.equal(resolveCurrentLanguage(available, 'fr'), 'fr')
})

test('resolveCurrentLanguage normalizes underscores to hyphens', () => {
	const available = [
		{ code: 'en', nativeLabel: 'English' },
		{ code: 'de-formal', nativeLabel: 'Deutsch (formal)' },
		{ code: 'zh-hant', nativeLabel: '繁體中文' },
	]
	assert.equal(resolveCurrentLanguage(available, 'de_formal'), 'de-formal')
	assert.equal(resolveCurrentLanguage(available, 'ZH_HANT'), 'zh-hant')
})

test('resolveCurrentLanguage matches shorter subtag progressively', () => {
	const available = [
		{ code: 'en', nativeLabel: 'English' },
		{ code: 'zh-hant', nativeLabel: '繁體中文' },
	]
	assert.equal(resolveCurrentLanguage(available, 'zh-hant-hk'), 'zh-hant')
})

test('resolveCurrentLanguage matches base language when regional variant not present', () => {
	const available = [
		{ code: 'en', nativeLabel: 'English' },
		{ code: 'fr', nativeLabel: 'Français' },
	]
	assert.equal(resolveCurrentLanguage(available, 'fr-ca'), 'fr')
	assert.equal(resolveCurrentLanguage(available, 'fr_FR'), 'fr')
})

test('resolveCurrentLanguage matches variant starting with base prefix if exact base not present', () => {
	const available = [
		{ code: 'es', nativeLabel: 'Español' },
		{ code: 'de-formal', nativeLabel: 'Deutsch (formal)' },
	]
	assert.equal(resolveCurrentLanguage(available, 'de'), 'de-formal')
})

test('resolveCurrentLanguage falls back to en when preferred is not found and en is available', () => {
	const available = [
		{ code: 'en', nativeLabel: 'English' },
		{ code: 'de', nativeLabel: 'Deutsch' },
	]
	assert.equal(resolveCurrentLanguage(available, 'ja'), 'en')
})

test('resolveCurrentLanguage falls back to first available language when en is not available', () => {
	const available = [
		{ code: 'de', nativeLabel: 'Deutsch' },
		{ code: 'fr', nativeLabel: 'Français' },
	]
	assert.equal(resolveCurrentLanguage(available, 'ja'), 'de')
	assert.equal(resolveCurrentLanguage(available, null), 'de')
})

test('resolveCurrentLanguage falls back gracefully with empty or null inputs', () => {
	assert.equal(resolveCurrentLanguage(null, null), 'en')
	assert.equal(resolveCurrentLanguage([], null), 'en')
	assert.equal(resolveCurrentLanguage(null, 'de'), 'de')
})

test('interface language resolution always produces a valid option code in availableLanguages', () => {
	const available = [
		{ code: 'de', nativeLabel: 'Deutsch' },
		{ code: 'fr', nativeLabel: 'Français' },
	]
	// Simulating resolveInitialLanguage in GreetingPrompt/preferences
	const resolveInitial = (langs, preferred) => {
		if (!langs || !langs.length) return null
		return resolveCurrentLanguage(langs, preferred)
	}

	// Case 1: languages is empty -> returns null to allow placeholder rendering
	assert.equal(resolveInitial([], 'en'), null)
	assert.equal(resolveInitial(null, 'en'), null)

	// Case 2: preferred language is available -> resolves to it
	const code1 = resolveInitial(available, 'de')
	assert.equal(code1, 'de')
	assert.ok(available.some(opt => opt.code === code1))

	// Case 3: preferred language is not available -> resolves to valid fallback in available
	const code2 = resolveInitial(available, 'en')
	assert.equal(code2, 'de')
	assert.ok(available.some(opt => opt.code === code2))

	// Case 4: stale/orphaned code re-resolution check
	let currentSelection = 'it' // Not in available
	const hasCurrent = available.some(l => l && l.code === currentSelection)
	assert.equal(hasCurrent, false)
	if (!hasCurrent && available.length) {
		currentSelection = resolveInitial(available, 'fr')
	}
	assert.equal(currentSelection, 'fr')
	assert.ok(available.some(opt => opt.code === currentSelection))
})
