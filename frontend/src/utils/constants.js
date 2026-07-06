export const PROJECT_ROLE = {
  VIEWER: 0,
  EDITOR: 1,
  OWNER: 2,
}

export const PROJECT_ROLE_LABEL = {
  [PROJECT_ROLE.VIEWER]: 'viewer',
  [PROJECT_ROLE.EDITOR]: 'editor',
  [PROJECT_ROLE.OWNER]: 'admin',
}

export const PROJECT_MEMBER_ROLES = [
  { value: PROJECT_ROLE.VIEWER, label: 'viewer' },
  { value: PROJECT_ROLE.EDITOR, label: 'editor' },
]

export const USER_STATUS = {
  ACTIVE: true,
  INACTIVE: false,
}

export const INDEX_STATUS = ['pending', 'indexing', 'parsing', 'indexed', 'failed', 'na']

export const INDEX_STATUS_TYPES = {
  pending: 'info',
  indexing: 'warning',
  parsing: 'warning',
  indexed: 'success',
  failed: 'danger',
  na: 'info',
}

/** @deprecated use INDEX_STATUS_TYPES + i18n indexStatus.* */
export const INDEX_STATUS_MAP = {
  pending: { type: 'info', label: 'pending' },
  indexing: { type: 'warning', label: 'indexing' },
  parsing: { type: 'warning', label: 'parsing' },
  indexed: { type: 'success', label: 'indexed' },
  failed: { type: 'danger', label: 'failed' },
  na: { type: 'info', label: 'na' },
}

export const DEFECT_STATUS = ['init', 'open', 'in_progress', 'resolved', 'closed']

export const DEFECT_STATUS_MAP = {
  init: { type: 'info', label: '新建' },
  open: { type: 'danger', label: '打开' },
  in_progress: { type: 'warning', label: '处理中' },
  resolved: { type: 'success', label: '已解决' },
  closed: { type: 'info', label: '已关闭' },
}

// 合法状态流转（与后端 transition.py ALLOWED_TRANSITIONS 一致）
export const DEFECT_ALLOWED_TRANSITIONS = {
  init: ['open'],
  open: ['in_progress', 'closed'],
  in_progress: ['open', 'resolved'],
  resolved: ['closed', 'in_progress'],
  closed: ['open'],
}

export const DEFECT_SEVERITY_MAP = { minor: '轻微', normal: '一般', serious: '严重', critical: '致命' }
export const DEFECT_PRIORITY_MAP = { high: '高', medium: '中', low: '低' }
export const DEFECT_CATEGORY_MAP = { functional: '功能', performance: '性能', ui: '界面', compatibility: '兼容', security: '安全', other: '其他' }

export const DEFECT_HISTORY_ACTION_MAP = {
  created: '创建缺陷',
  status_change: '状态变更',
  field_update: '字段修改',
  comment_added: '添加备注',
}

export const RUN_STATUS = ['pending', 'running', 'completed', 'failed', 'cancelled']

export const RUN_STATUS_MAP = {
  pending: { type: 'info', label: '待执行' },
  running: { type: 'warning', label: '执行中' },
  completed: { type: 'success', label: '已完成' },
  failed: { type: 'danger', label: '已失败' },
  cancelled: { type: 'info', label: '已停止' },
}

export const SUITE_TYPE_MAP = {
  api: { type: 'primary', label: 'API' },
  functional: { type: 'success', label: '功能' },
  ui: { type: 'warning', label: 'UI' },
}

export const TASK_TYPE_MAP = {
  api: { type: 'primary', label: 'API' },
  functional: { type: 'success', label: '手工' },
  manual: { type: 'info', label: '手工' },
  ui: { type: 'warning', label: 'UI' },
}

export const RUN_MODE_MAP = {
  serial: '串行',
  parallel: '并行',
}

export const CONFIG_GROUP = ['base', 'headers', 'envs']
export const CONFIG_GROUPS = CONFIG_GROUP
export const CONFIG_TYPES = ['scalar', 'secret', 'file_ref']

export const CASE_RESULT_MAP = {
  success: { type: 'success', label: '成功' },
  pass: { type: 'success', label: '通过' },
  fail: { type: 'danger', label: '失败' },
  failed: { type: 'danger', label: '失败' },
  error: { type: 'danger', label: '错误' },
  skip: { type: 'info', label: '跳过' },
  skipped: { type: 'info', label: '跳过' },
  pending: { type: 'info', label: '未开始' },
}

export const HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']

export const DB_TYPE = ['mysql', 'postgresql', 'oracle', 'sqlserver', 'sqlite']

export const DEFAULT_PAGE_SIZE = 20

export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  LOCALE: 'locale',
  CURRENT_PROJECT_ID: 'current_project_id',
}

export const TASK_TYPES = ['functional', 'manual', 'api']

export const CASE_KIND = {
  PRECONDITION: 'precondition',
  MAIN: 'main',
}

// ═══════════════════════════════════════════
// Dialog width constants
// ═══════════════════════════════════════════
export const DIALOG_SIZES = {
  small: 480,
  medium: 640,
  large: 960,
  contentHalf: '50vw',
}

// ═══════════════════════════════════════════
// Status color mapping (mirrors CSS tokens in variables.scss)
// For use in JS/template inline styles where SCSS variables are unavailable
// ═══════════════════════════════════════════
export const STATUS_COLORS = {
  success: '#219653',
  warning: '#F2994A',
  danger: '#EB5757',
  info: '#409EFF',
  primary: '#5B9BD5',
  neutral: '#909399',
}

export const METHOD_COLORS = {
  GET: '#219653',
  POST: '#409EFF',
  PUT: '#F2994A',
  PATCH: '#F2994A',
  DELETE: '#EB5757',
}

// ═══════════════════════════════════════════
// i18n-aware MAP functions
// Usage: const map = getDefectStatusMap(t)
// These return the same structure as the legacy MAP constants
// but with labels resolved through i18n.
// ═══════════════════════════════════════════

export const getDefectStatusMap = (t) => ({
  init: { type: 'info', label: t('defect.status.init') },
  open: { type: 'danger', label: t('defect.status.open') },
  in_progress: { type: 'warning', label: t('defect.status.in_progress') },
  resolved: { type: 'success', label: t('defect.status.resolved') },
  closed: { type: 'info', label: t('defect.status.closed') },
})

export const getDefectSeverityMap = (t) => ({
  minor: t('defect.severity.minor'),
  normal: t('defect.severity.normal'),
  serious: t('defect.severity.serious'),
  critical: t('defect.severity.critical'),
})

export const getDefectPriorityMap = (t) => ({
  high: t('defect.priority.high'),
  medium: t('defect.priority.medium'),
  low: t('defect.priority.low'),
})

export const getDefectCategoryMap = (t) => ({
  functional: t('defect.category.functional'),
  performance: t('defect.category.performance'),
  ui: t('defect.category.ui'),
  compatibility: t('defect.category.compatibility'),
  security: t('defect.category.security'),
  other: t('defect.category.other'),
})

export const getDefectHistoryActionMap = (t) => ({
  created: t('defect.history.created'),
  status_change: t('defect_history.statusChange'),
  field_update: t('defect_history.fieldUpdate'),
  comment_added: t('defect_history.commentAdded'),
})

export const getRunStatusMap = (t) => ({
  pending: { type: 'info', label: t('status.exec.pending') },
  running: { type: 'warning', label: t('status.exec.running') },
  completed: { type: 'success', label: t('status.exec.completed') },
  failed: { type: 'danger', label: t('status.exec.failed') },
  cancelled: { type: 'info', label: t('status.exec.cancelled') },
})

export const getCaseResultMap = (t) => ({
  success: { type: 'success', label: t('status.result.success') },
  pass: { type: 'success', label: t('status.result.pass') },
  fail: { type: 'danger', label: t('status.result.fail') },
  failed: { type: 'danger', label: t('status.result.failed') },
  error: { type: 'danger', label: t('status.result.error') },
  skip: { type: 'info', label: t('status.result.skip') },
  skipped: { type: 'info', label: t('status.result.skipped') },
  pending: { type: 'info', label: t('status.result.pending') },
})

export const getSuiteTypeMap = (t) => ({
  api: { type: 'primary', label: 'API' },
  functional: { type: 'success', label: t('suite.type.functional') },
  ui: { type: 'warning', label: 'UI' },
})

export const getTaskTypeMap = (t) => ({
  api: { type: 'primary', label: 'API' },
  functional: { type: 'success', label: t('task.type.functional') },
  manual: { type: 'info', label: t('task.type.manual') },
  ui: { type: 'warning', label: 'UI' },
})

export const getRunModeMap = (t) => ({
  serial: t('runMode.serial'),
  parallel: t('runMode.parallel'),
})
