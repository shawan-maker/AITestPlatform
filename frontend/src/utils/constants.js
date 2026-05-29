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

export const INDEX_STATUS = ['pending', 'indexing', 'parsing', 'indexed', 'failed']

export const INDEX_STATUS_MAP = {
  pending: { type: 'info', label: 'pending' },
  indexing: { type: 'warning', label: 'indexing' },
  parsing: { type: 'warning', label: 'parsing' },
  indexed: { type: 'success', label: 'indexed' },
  failed: { type: 'danger', label: 'failed' },
}

export const DEFECT_STATUS = ['init', 'open', 'in_progress', 'resolved', 'closed']

export const DEFECT_STATUS_MAP = {
  init: { type: 'info', label: 'init' },
  open: { type: 'danger', label: 'open' },
  in_progress: { type: 'warning', label: 'in_progress' },
  resolved: { type: 'success', label: 'resolved' },
  closed: { type: 'info', label: 'closed' },
}

export const DEFECT_SEVERITY = ['一般', '严重', '致命']
export const DEFECT_PRIORITY = ['高', '中', '低']
export const DEFECT_CATEGORY = ['功能', '性能', '界面', '兼容', '安全', '其他']

export const RUN_STATUS = ['pending', 'running', 'completed', 'failed', 'cancelled']

export const RUN_STATUS_MAP = {
  pending: { type: 'info', label: 'pending' },
  running: { type: 'warning', label: 'running' },
  completed: { type: 'success', label: 'completed' },
  failed: { type: 'danger', label: 'failed' },
  cancelled: { type: 'info', label: 'cancelled' },
}

export const CONFIG_GROUP = ['base', 'headers', 'envs']
export const CONFIG_GROUPS = CONFIG_GROUP
export const CONFIG_TYPES = ['scalar', 'secret', 'file_ref']

export const CASE_RESULT_MAP = {
  success: { type: 'success', label: 'success' },
  pass: { type: 'success', label: 'pass' },
  fail: { type: 'danger', label: 'fail' },
  failed: { type: 'danger', label: 'failed' },
  error: { type: 'danger', label: 'error' },
  skip: { type: 'info', label: 'skip' },
  skipped: { type: 'info', label: 'skipped' },
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
