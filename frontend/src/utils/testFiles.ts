export function isTestFile(path: string): boolean {
  const normalized = path.replaceAll('\\', '/').toLowerCase()
  const basename = normalized.split('/').pop() ?? normalized

  return (
    normalized.includes('/tests/')
    || normalized.includes('/__tests__/')
    || basename.startsWith('test_')
    || basename.endsWith('_test.py')
    || basename.includes('.test.')
    || basename.includes('.spec.')
  )
}
