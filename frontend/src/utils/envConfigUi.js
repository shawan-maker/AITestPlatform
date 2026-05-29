export const MASKED_SECRET = '***'

export function parseFileId(value) {
  if (!value) return null
  try {
    const obj = JSON.parse(value)
    const id = obj?.file_id
    return typeof id === 'number' ? id : null
  } catch {
    return null
  }
}

export function isFileValue(value) {
  return parseFileId(value) != null
}

export function toUiRow(config, { headersOnly = false } = {}) {
  const row = {
    id: config.id,
    name: config.name ?? '',
    uiType: 'string',
    encrypted: false,
    fileId: null,
    stringValue: '',
    remark: config.remark ?? '',
    config_group: config.config_group,
    isNew: false,
  }

  if (headersOnly) {
    row.stringValue = config.value === MASKED_SECRET ? '' : (config.value ?? '')
    return row
  }

  if (config.config_type === 'secret') {
    row.encrypted = true
    row.stringValue = config.value === MASKED_SECRET ? '' : (config.value ?? '')
    return row
  }

  const fileId = parseFileId(config.value)
  if (fileId != null) {
    row.uiType = 'file'
    row.fileId = fileId
    return row
  }

  row.stringValue = config.value ?? ''
  return row
}

export function createEmptyUiRow(configGroup = 'envs') {
  return {
    id: null,
    name: '',
    uiType: 'string',
    encrypted: false,
    fileId: null,
    stringValue: '',
    remark: '',
    config_group: configGroup,
    isNew: true,
  }
}

export function toApiPayload(uiRow, { headersOnly = false, includeName = true } = {}) {
  const payload = {}
  if (includeName) {
    payload.name = uiRow.name?.trim()
  }

  if (headersOnly || uiRow.uiType === 'string' && !uiRow.encrypted) {
    payload.config_type = 'scalar'
    payload.value = uiRow.stringValue ?? ''
  } else if (uiRow.uiType === 'file') {
    payload.config_type = 'scalar'
    payload.value = uiRow.fileId ? JSON.stringify({ file_id: uiRow.fileId }) : ''
  } else if (uiRow.encrypted) {
    payload.config_type = 'secret'
    if (uiRow.stringValue && uiRow.stringValue !== MASKED_SECRET) {
      payload.value = uiRow.stringValue
    }
  } else {
    payload.config_type = 'scalar'
    payload.value = uiRow.stringValue ?? ''
  }

  payload.remark = uiRow.remark || undefined
  return payload
}

export function buildUpdatePayload(uiRow, options) {
  const payload = toApiPayload(uiRow, options)
  if (uiRow.encrypted && !uiRow.stringValue) {
    delete payload.value
  }
  return payload
}
