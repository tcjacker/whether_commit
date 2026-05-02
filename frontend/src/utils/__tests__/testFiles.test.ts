import { describe, expect, it } from 'vitest'
import { isTestFile } from '../testFiles'

describe('isTestFile', () => {
  it('detects test file paths consistently', () => {
    expect(isTestFile('tests/client.js')).toBe(true)
    expect(isTestFile('__tests__/client.js')).toBe(true)
    expect(isTestFile('src/__tests__/client.test.tsx')).toBe(true)
    expect(isTestFile('frontend/src/api/client.spec.ts')).toBe(true)
    expect(isTestFile('frontend/src/api/client.test.js')).toBe(true)
    expect(isTestFile('backend/tests/test_main.py')).toBe(true)
    expect(isTestFile('backend/app/main.py')).toBe(false)
  })
})
