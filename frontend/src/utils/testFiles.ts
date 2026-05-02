export function isTestFile(path: string): boolean {
  const normalized = path.replaceAll('\\', '/').toLowerCase()
  const basename = normalized.split('/').pop() ?? normalized

  return (
    normalized.startsWith('tests/')
    || normalized.includes('/tests/')
    || normalized.startsWith('__tests__/')
    || normalized.includes('/__tests__/')
    || basename.startsWith('test_')
    || basename.endsWith('_test.py')
    || basename.includes('.test.')
    || basename.includes('.spec.')
  )
}
