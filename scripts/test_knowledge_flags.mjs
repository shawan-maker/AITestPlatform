/**
 * 知识库保存按钮逻辑自测。用法: node scripts/test_knowledge_flags.mjs
 */
import assert from 'node:assert/strict'
import {
  canSaveInterfaces,
  canSaveRequirement,
  documentTitleFromFileName,
  formatDocumentVersionTitle,
  normalizeParsedInterfaceItem,
} from '../frontend/src/utils/knowledge.js'

assert.equal(formatDocumentVersionTitle('需求说明', 'v1.0'), '需求说明_v1.0')
assert.equal(formatDocumentVersionTitle('需求说明_v1.0', 'v1.0'), '需求说明_v1.0')
assert.equal(formatDocumentVersionTitle('需求说明_v1.0', 'v1.1'), '需求说明_v1.1')
assert.equal(documentTitleFromFileName('demo-req.md'), 'demo-req')
assert.equal(documentTitleFromFileName('demo-req_v1.0.json'), 'demo-req')

assert.equal(canSaveRequirement({ doc_type: 'requirement', index_status: 'indexed' }), true)
assert.equal(
  canSaveRequirement({
    doc_type: 'requirement',
    index_status: 'indexed',
    requirement_saved: true,
  }),
  false,
)
assert.equal(
  canSaveRequirement({
    doc_type: 'requirement',
    index_status: 'indexed',
    can_save_requirement: true,
  }),
  true,
)
assert.equal(
  canSaveRequirement({
    doc_type: 'requirement',
    index_status: 'indexed',
    can_save_requirement: false,
  }),
  false,
)
assert.equal(
  canSaveRequirement({
    doc_type: 'requirement',
    index_status: 'indexing',
    can_save_requirement: true,
  }),
  false,
)

assert.equal(canSaveInterfaces({ doc_type: 'api_doc', parse_status: 'parsed' }), true)
assert.equal(
  canSaveInterfaces({
    doc_type: 'api_doc',
    parse_status: 'parsed',
    interfaces_saved: true,
  }),
  false,
)
assert.equal(
  canSaveInterfaces({
    doc_type: 'api_doc',
    parse_status: 'parsed',
    can_save_interfaces: true,
  }),
  true,
)
assert.equal(
  canSaveInterfaces({
    doc_type: 'api_doc',
    parse_status: 'parsed',
    can_save_interfaces: false,
  }),
  false,
)
assert.equal(
  canSaveInterfaces({
    doc_type: 'api_doc',
    parse_status: 'parsing',
    can_save_interfaces: true,
  }),
  false,
)

const normalized = normalizeParsedInterfaceItem({
  method: 'get',
  path: '/ping',
  summary: 'ping',
  request_modules: 'query: id',
  api_path: 'User',
})
assert.equal(normalized.method, 'GET')
assert.equal(normalized.path, '/ping')

console.log('knowledge flag tests passed')
