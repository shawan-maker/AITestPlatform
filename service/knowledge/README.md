# 知识库模块

知识库用于管理**需求文档**与 **API 接口文档**，支持上传、版本、索引/解析，以及下游「保存需求」「保存接口」。

## 保存按钮显隐（单一真相源）

保存按钮状态由后端 `KnowledgeDocumentBrief` 四个布尔字段决定；**前端优先 `can_save_*` / `*_saved`，后端未返回时按 `indexed` / `parsed` 回退**，避免旧接口或缓存导致按钮永不出现。

计算逻辑见 [`save_state.py`](document/save_state.py) 的 `compute_version_save_state`，列表与详情共用。

**接口规范（Swagger/OpenAPI）**在上传/重传时会**同步解析**（`IndexWorker.start_processing`），上传响应返回时即可看到「保存接口」与解析列表；需求文档仍异步 RAG 索引。

### 保存需求（`doc_type = requirement`）

针对**当前版本** `current_version_id`：

| 场景 | `can_save_requirement` |
|------|------------------------|
| 索引中 / 失败 / 未就绪 | `false` |
| 已索引且该版本无 `RequirementDoc` | `true` |
| 该版本已有 `RequirementDoc`（知识库确认或需求页确认） | `false` |
| 重新上传新版本且新版本索引完成、未保存 | `true` |

`requirement_saved` = 是否存在 `RequirementDoc(source_document_id, source_document_version_id)`。

索引完成后会自动同步 **RequirementCandidate**（需求页「待确认」Tab 可见），但 `can_save_requirement` 仍为 `true`，知识库「保存需求」按钮保持显示，直至确认写入 `RequirementDoc`。

候选/保存对话框默认标题为 **`{文档名}_{版本号}`**（如 `需求说明_v1.0`），见 `default_candidate_title()`。

### 保存接口（`doc_type = api_doc`）

针对**当前版本**：

| 场景 | `can_save_interfaces` |
|------|------------------------|
| 解析中 / 失败 / 未就绪 | `false` |
| 已解析且该版本未导入 | `true` |
| 该版本已导入（marker 或 `ApiInterface` 关联） | `false` |
| 重新上传新版本且新版本解析完成、未导入 | `true` |

`interfaces_saved` 判定顺序：

1. 解析结果目录下存在 `.interfaces_imported` marker（见 [`import_marker.py`](document/import_marker.py)）
2. 存在 `ApiInterface` 且 `source_document_id` + `source_document_version_id` 匹配

导入成功时 [`downstream/import_service.py`](downstream/import_service.py) 会写入 marker；`skip` 模式也会更新已有接口的 source 字段。

接口文档即使用户选择 **AI 解析模式**，若文件内容为 Swagger/OpenAPI（`.json/.yaml/.yml`），后端 [`parse_router.py`](rules/parse_router.py) 仍会自动走结构化解析，从而设置 `parse_status=parsed` 与 `can_save_interfaces=true`。

## API 文档详情：解析接口列表（只读）

详情与 `parsed-interfaces` 接口统一经 [`parsed_interface_service.resolve_parsed_interfaces`](document/parsed_interface_service.py)：优先从源 Swagger/OpenAPI 文件 reparse，写回 enriched `parsed.json`，再合并已保存接口的模块/目录。

| 列 | 字段 | 说明 |
|----|------|------|
| 请求方法 | `method` | HTTP 方法 |
| 请求路径 | `path` | API path |
| 请求摘要 | `summary` | 可为空 |
| 请求所有模块 | `request_modules` | header/path/query/body 参数名汇总，可为空 |
| API 接口所在路径 | `api_path` | 优先 OpenAPI `tags`；无 tags 时从 URL 路径段推导 |

历史文档若在 tags 字段加入前上传，需**重新上传或 reindex** 后 `api_path` 才会完整。

备用只读接口：

- `GET .../versions/{vid}/parsed-interfaces`
- `POST .../import-interfaces/preview`（含 `request_modules` / `api_path`）

## 前端

- 按钮逻辑：[`frontend/src/utils/knowledge.js`](../../frontend/src/utils/knowledge.js)
- 列表页进入时 `onActivated` 会静默刷新，避免从需求页确认返回后按钮状态过期

## 自测

```bash
python scripts/knowledge_smoke_test.py
node scripts/test_knowledge_flags.mjs
```
