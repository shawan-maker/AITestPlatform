/**
 * 解析接口多源合并自测。用法: node scripts/test_parsed_interface_merge.mjs
 */
import assert from 'node:assert/strict'
import { mergeParsedInterfaceItems } from '../frontend/src/utils/parsedInterfaceMerge.js'

const slim = [{ method: 'GET', path: '/ping', summary: 'ping' }]
const rich = [
  {
    method: 'GET',
    path: '/ping',
    summary: 'ping',
    request_modules: 'query: verbose',
    api_path: 'Health',
  },
]

const merged = mergeParsedInterfaceItems(slim, rich)
assert.equal(merged.length, 1)
assert.equal(merged[0].method, 'GET')
assert.equal(merged[0].request_modules, 'query: verbose')
assert.equal(merged[0].api_path, 'Health')

const reversed = mergeParsedInterfaceItems(rich, slim)
assert.equal(reversed[0].request_modules, 'query: verbose')

console.log('parsed interface merge tests passed')
