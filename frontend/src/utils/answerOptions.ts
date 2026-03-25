export interface AnswerOption {
  id: string
  key: string
  label: string
}

function toSafeLabel(value: unknown): string {
  if (typeof value === 'string') {
    return value.trim()
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  return ''
}

export function parseAnswerOptions(answerSpace: string): AnswerOption[] {
  const trimmed = answerSpace.trim()
  if (!trimmed) {
    return []
  }

  const normalized: Array<{ key: string; label: string }> = []
  const startsWithJsonToken = trimmed.startsWith('{') || trimmed.startsWith('[')
  let parsedJson = false

  if (startsWithJsonToken) {
    try {
      const parsed: unknown = JSON.parse(trimmed)
      parsedJson = true
      if (Array.isArray(parsed)) {
        for (let index = 0; index < parsed.length; index += 1) {
          const label = toSafeLabel(parsed[index])
          if (!label) {
            continue
          }
          normalized.push({ key: String(index + 1), label })
        }
      } else if (parsed && typeof parsed === 'object') {
        for (const [key, value] of Object.entries(parsed)) {
          const label = toSafeLabel(value)
          if (!label) {
            continue
          }
          normalized.push({ key: key.trim() || String(normalized.length + 1), label })
        }
      }
    } catch {
      parsedJson = false
    }
  }

  if (normalized.length === 0 && !parsedJson) {
    const lines = trimmed
      .split(/\r?\n/)
      .map((item) => item.trim())
      .filter((item) => item.length > 0)
    for (let index = 0; index < lines.length; index += 1) {
      normalized.push({ key: String(index + 1), label: lines[index] ?? '' })
    }
  }

  const unique: AnswerOption[] = []
  const seen = new Set<string>()
  for (let index = 0; index < normalized.length; index += 1) {
    const option = normalized[index]
    if (!option || !option.label) {
      continue
    }
    const fingerprint = `${option.key}\u0000${option.label}`
    if (seen.has(fingerprint)) {
      continue
    }
    seen.add(fingerprint)
    unique.push({
      id: `${option.key}-${index}`,
      key: option.key,
      label: option.label,
    })
  }

  return unique
}

export function matchPredictionToAnswerOptionId(predictionContent: string, options: AnswerOption[]): string {
  const target = predictionContent.trim()
  if (!target) {
    return ''
  }
  for (const option of options) {
    if (target === option.label || target === `${option.key}: ${option.label}` || target === option.key) {
      return option.id
    }
  }
  return ''
}
