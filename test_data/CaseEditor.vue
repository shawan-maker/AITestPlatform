<template>
	<el-collapse :model-value="['1', '2', '4', '6']">
		<el-collapse-item name="1">
			<template #title>
				<div style="display: flex; align-items: center;">
					<img src="@/assets/icons/icon-api-b.png" width="20px" style="margin: 0 0 0 10px;" />
					<span style="margin: 0 0 0 10px;">{{ $t('debugRequestInfo') }}</span>
				</div>
			</template>
			<!-- 请求方法和URL -->
			<el-input v-model="caseData.interface.url" placeholder="Request URL">
				<template #prepend>
					<el-select v-model="caseData.interface.method" :placeholder="$t('debugMethodPlaceholder')" style="width: 115px" >
						<el-option label="GET" value="get" />
						<el-option label="POST" value="post" />
						<el-option label="PATCH" value="patch" />
						<el-option label="PUT" value="put" />
						<el-option label="DELETE" value="delete" />
					</el-select>
				</template>
			</el-input>
		</el-collapse-item>
		<el-collapse-item name="2">
			<template #title>
				<div style="display: flex; align-items: center;">
					<img src="@/assets/icons/more-four.png" width="20px" style="margin: 0 0 0 10px;" />
					<span style="margin: 0 0 0 10px;">{{ $t('caseEditorNameSection') }}</span>
				</div>
			</template>
			<el-form-item :label="$t('caseEditorNameLabel')" style="margin: 0;">
				<el-input v-model="caseData.title" :placeholder="$t('caseEditorNamePlaceholder')" />
			</el-form-item>
		</el-collapse-item>
		<el-collapse-item name="3">
			<template #title>
				<div style="display: flex; align-items: center;">
					<img src="@/assets/icons/magic-wand.png" width="20px" style="margin: 0 0 0 10px;" />
					<span style="margin: 0 0 0 10px;">{{ $t('debugTabSetupScript') }}</span>
				</div>
			</template>
			<div class="script_code">
				<div class="code">
					<Editor v-model="caseData.setup_script" lang="python" height="300px"></Editor>	
				</div>
				<div class="mod">
					<div class="add_code">
						<el-button plain @click="addSetupScript('env')">{{ $t('debugSetEnvVariable') }}</el-button>
					</div>
					<div class="add_code">
						<el-button plain @click="addSetupScript('global')">{{ $t('debugSetglobalVariable') }}</el-button>
					</div>
					<div class="add_code">
						<el-button plain @click="addSetupScript('sql')">{{ $t('debugExecuteSql') }}</el-button>
					</div>
					<div class="add_code">
						<el-button plain @click="addSetupScript('get_env')">{{ $t('debugGetEnvVariable') }}</el-button>
					</div>
					<div class="add_code">
						<el-button plain @click="addSetupScript('get_global')">{{ $t('debugGetGlobalVariable') }}</el-button>
					</div>
				</div>
			</div>
		</el-collapse-item>
		<el-collapse-item name="4">
			<template #title>
				<div style="display: flex; align-items: center;">
					<img src="@/assets/icons/point.png" width="20px" style="margin: 0 0 0 10px;" />
					<span style="margin: 0 0 0 10px;">{{ $t('debugTabHeaders') }}</span>
				</div>
			</template>
			<Editor v-model="caseData.headers" lang="json" height="300px"></Editor>	
		</el-collapse-item>
		<el-collapse-item name="5">
			<template #title>
				<div style="display: flex; align-items: center;">
					<img src="@/assets/icons/repair.png" width="20px" style="margin: 0 0 0 10px;" />
					<span style="margin: 0 0 0 10px;">{{ $t('debugTabParams') }}</span>
				</div>
			</template>
			<Editor lang="json" v-model="caseData.request.params" height='350px'></Editor>
		</el-collapse-item>
		<el-collapse-item name="6">
			<template #title>
				<div style="display: flex; align-items: center;">
					<img src="@/assets/icons/liucheng2.png" width="20px" style="margin: 0 0 0 10px;" />
					<span style="margin: 0 0 0 10px;">{{ $t('debugTabBody') }}</span>
				</div>
			</template>
			<el-radio-group v-model="bodyType">
			    <el-radio value="json">{{ $t('debugBodyJson') }}</el-radio>
			    <el-radio value="data">{{ $t('debugBodyUrlencoded') }}</el-radio>
			    <el-radio value="form-data">{{ $t('debugBodyFormData') }}</el-radio>
			</el-radio-group>
			<div v-if='bodyType==="json"'>
				<Editor lang="json" v-model="caseData.request.json" height='300px'></Editor>
			</div>
			<div v-else-if='bodyType==="data"'>
				<Editor lang="json" v-model="caseData.request.data" height='300px'></Editor>
			</div>
			<div v-else class="form-data-box">
				<p class="tip">{{ $t('debugBodyFileTip') }}</p>
				<el-form label-width="120px" class="form-data-form">
					<el-form-item :label="$t('fileName')">
						<el-input v-model="formFieldName" style="width: 220px" />
					</el-form-item>
					<el-form-item :label="$t('filePath')">
						<el-select
							v-model="selectedUploadId"
							filterable
							clearable
							style="width: 260px"
							:placeholder="$t('commonSelectFile')"
						>
							<el-option
								v-for="item in uploadFileOptions"
								:key="item.id"
								:label="displayFileOptionLabel(item)"
								:value="item.id"
							/>
						</el-select>
					</el-form-item>
				</el-form>
			</div>
		</el-collapse-item>
		<el-collapse-item name="7">
			<template #title>
				<div style="display: flex; align-items: center;">
					<img src="@/assets/icons/instruction.png" width="20px" style="margin: 0 0 0 10px;" />
					<span style="margin: 0 0 0 10px;">{{ $t('debugTabTeardownScript') }}</span>
				</div>
			</template>
			<div class="script_code">
				<div class="code">
					<Editor v-model="caseData.teardown_script" lang="python" height="300px"></Editor>
				</div>
				<div class="mod">
					<div class="add_code">
						<el-button plain @click="addTeardownScript('body')">{{ $t('debugGetResponseBody') }}</el-button>
					</div>
					<div class="add_code">
						<el-button plain @click="addTeardownScript('json')">{{ $t('debugGetJsonResponse') }}</el-button>
					</div>
					<div class="add_code">
						<el-button plain @click="addTeardownScript('json_res')">{{ $t('debugGetJsonPathSingle') }}</el-button>
					</div>
					<div class="add_code">
						<el-button plain @click="addTeardownScript('json_all')">{{ $t('debugGetJsonPathList') }}</el-button>
					</div>
					<div class="add_code">
						<el-button plain @click="addTeardownScript('re_res')">{{ $t('debugGetRegexSingle') }}</el-button>
					</div>
					<div class="add_code">
						<el-button plain @click="addTeardownScript('re_all')">{{ $t('debugGetRegexList') }}</el-button>
					</div>
					<div class="add_code">
						<el-button plain @click="addTeardownScript('result_assert')">{{ $t('debugAssertResult') }}</el-button>
					</div>
					<div class="add_code">
						<el-button plain @click="addTeardownScript('env')">{{ $t('debugSetEnvVariable') }}</el-button>
					</div>
					<div class="add_code">
						<el-button plain @click="addTeardownScript('global')">{{ $t('debugSetglobalVariable') }}</el-button>
					</div>
					<div class="add_code">
						<el-button plain @click="addTeardownScript('global2')">{{ $t('debugDeleteGlobalVariable') }}</el-button>
					</div>
					<div class="add_code">
						<el-button plain @click="addTeardownScript('sql')">{{ $t('debugExecuteSql') }}</el-button>
					</div>
					<div class="add_code">
						<el-button plain @click="addTeardownScript('get_env')">{{ $t('debugGetEnvVariable') }}</el-button>
					</div>
					<div class="add_code">
						<el-button plain @click="addTeardownScript('get_global')">{{ $t('debugGetGlobalVariable') }}</el-button>
					</div>
				</div>
			</div>
		</el-collapse-item>
	</el-collapse>
	<div class="btns">
		<el-affix :offset="80" position="bottom">
				<!-- <el-button type="primary" @click="addClick">添加</el-button> -->
				<el-button type="primary" @click="copyCase">{{ $t('commonCopy') }}</el-button>
				<el-button type="primary" @click="EditCase">{{ $t('commonSave') }}</el-button>
				<el-button type="primary" @click="runCase">{{ $t('commonRun') }}</el-button>
				<el-button type="danger" @click="deleteCase">{{ $t('commonDelete') }}</el-button>				
		</el-affix>
	</div>

	<el-drawer v-model="isShowDraw" size="40%">
		<template #header>
			<b>{{ $t('caseTestTitle') }}</b>
		</template>
		<!-- 响应信息部分 -->
		<template #default>
			<!-- 响应信息部分 -->
			<Result :result="responseData"></Result>
		</template>
	</el-drawer>

</template>

<script setup>
	import Editor from '@/components/Editor.vue'
	import Result from '@/components/Result.vue'
	import {ref,reactive,defineProps,watch,onMounted} from 'vue'
	import {ProjectStore} from '@/stores/module/ProjectStore.js'
	import api from '@/api/index'
	import { ElNotification,ElMessageBox,ElMessage } from 'element-plus'
	import { safeJsonParse } from '@/utils/globalTools';
	import { useI18n } from 'vue-i18n'
	
	// =====================定义页面的数据参数==========================
	// 获取ProjectStore的pinia对象
	const pstore = ProjectStore()
	// 定义prop接收用Id
	const prop = defineProps({
		case_id : ""
	})
	// 定义用例详情页面各个字段的数据
	const caseData = reactive({
		title: "",
		interface: {
			url: "/",
			method: "get"
		},
		catalog: null,
		headers: "{}",
		request: {
			 json: "{}",
			 data: "{}",
			 params: "{}"
		},
		file: [],
		setup_script: "",
		teardown_script: ""
	})
	let bodyType = ref("json")
	// form-data 选择已上传文件
	const uploadFileOptions = ref([])
	const formFieldName = ref('file')
	const selectedUploadId = ref(null)
	// 定义用例详情对象
	let caseObj = {}
	// 初始化用例数据（独立函数，方便切换用例时重置）
	const initCaseData = () => {
		return reactive({
			title: "",
			interface: {
				url: "/",
				method: "get"
			},
			catalog: null,
			headers: "{}",
			request: {
				json: "{}",
				data: "{}",
				params: "{}"
			},
			file: [],
			setup_script: "",
			teardown_script: ""
		});
	};

	// 下拉选项显示文件名（支持中文：优先 info[0]，否则解码 path）
	const displayFileOptionLabel = (item) => {
		if (!item) return ''
		if (item.info && Array.isArray(item.info) && item.info[0]) return item.info[0]
		const path = item.file
		if (!path) return ''
		try {
			const urlPath = path.indexOf('://') >= 0 ? new URL(path).pathname : path
			const parts = urlPath.replace(/\\/g, '/').split('/').filter(Boolean)
			const last = parts[parts.length - 1] || ''
			return decodeURIComponent(last)
		} catch {
			const parts = String(path).split(/[\\/]/)
			return decodeURIComponent(parts[parts.length - 1] || '') || parts[parts.length - 1] || ''
		}
	}

	const loadUploadFiles = async () => {
		if (!pstore.pro || !pstore.pro.id) {
			uploadFileOptions.value = []
			return
		}
		const res = await api.getFileListApi({ project: pstore.pro.id })
		if (res.status === 200) {
			uploadFileOptions.value = res.data || []
		}
	}

	// =====================定义前置脚本的操作模版展示==========================
	function addSetupScript(item) {
		if (item === "env") {
			caseData.setup_script += "\n# 设置临时变量 \ntest.save_env_variable('var_name',var_value)"
		} else if (item === "global") {
			caseData.setup_script += "\n# 设置环境变量 \ntest.save_global_variable('var_name',var_value)"
		} else if (item === "sql") {
			caseData.setup_script += "\n# 执行sql语句 \nvar_name = db.连接名.execute_all('sql语句')"
		} else if (item === "get_env") {
			caseData.setup_script += "\n# 获取临时变量 \nvar_name = test.get_env_variable('var_name', default_value)"
		} else if (item === "get_global") {
			caseData.setup_script += "\n# 获取环境变量 \nvar_name = test.get_global_variable('var_name', default_value)"
		}
	}
	// =====================定义前置脚本的操作模版展示==========================
	function addTeardownScript(item) {
		if (item === "env") {
			caseData.teardown_script += "\n# 设置临时变量 \ntest.save_env_variable('var_name',var_value)"
		} else if (item === "global") {
			caseData.teardown_script += "\n# 设置环境变量 \ntest.save_global_variable('var_name',var_value)"
		} else if (item === "sql") {
			caseData.teardown_script += "\n# 执行sql语句 \nvar_name = db.连接名.execute_all('sql语句')"
		} else if (item === "global2") {
			caseData.teardown_script += "\n# 删除环境变量 \ntest.del_global_variable('var_name')"
		} else if (item === "body") {
			caseData.teardown_script += "\n# 获取响应体 \nvar_name = response.data"
		} else if (item === "json") {
			caseData.teardown_script += "\n# 获取json响应 \nvar_name = response.json()"
		} else if (item === "json_res") {
			caseData.teardown_script += "\n# jsonpath提取单个数据 \nvar_name = test.json_extract(json响应,jsonpath表达式)"
		} else if (item === "json_all") {
			caseData.teardown_script += "\n# jsonpath提取一组数据 \nvar_name = test.json_extract_list(json响应,jsonpath表达式)"
		} else if (item === "re_res") {
			caseData.teardown_script += "\n# 正则表达式方式提取单个数据 \nvar_name = test.re_extract(响应体数据,正则表达式)"
		} else if (item === "re_all") {
			caseData.teardown_script += "\n# 正则表达式方式提取一组数据 \nvar_name = test.re_extract_list(响应体数据,正则表达式)"
		} else if (item === "result_assert") {
			caseData.teardown_script += "\n# 对响应结果进行断言 \n# 比较方式可以选择：相等、相等忽略大小写、不相等、包含、不包含、大于、小于、大于等于、小于等于、正则匹配 \ntest.assertion('比较方式',预期结果,实际结果)"
		} else if (item === "get_env") {
			caseData.teardown_script += "\n# 获取临时变量 \nvar_name = test.get_env_variable('var_name', default_value)"
		} else if (item === "get_global") {
			caseData.teardown_script += "\n# 获取环境变量 \nvar_name = test.get_global_variable('var_name', default_value)"
		}
	}
	
	// =====================核心校验函数（统一校验JSON格式）==========================
	/**
	 * 校验所有JSON字段是否合法
	 * @returns {boolean} 校验是否通过
	 */
	const validateJsonFields = () => {
		// 1. 校验请求头
		const headersResult = safeJsonParse(caseData.headers);
		if (!headersResult.valid) return false;

		// 2. 校验查询参数
		const paramsResult = safeJsonParse(caseData.request.params);
		if (!paramsResult.valid) return false;

		// 3. 按需校验请求体
		if (bodyType.value === "json") {
			const jsonResult = safeJsonParse(caseData.request.json);
			if (!jsonResult.valid) return false;
		} else if (bodyType.value === "data") {
			const dataResult = safeJsonParse(caseData.request.data);
			if (!dataResult.valid) return false;
		}

		// 4. 校验用例名称（非空）
		if (!caseData.title.trim()) {
			ElNotification({
				title: t('caseValidationFailTitle'),
				message: t('caseNameRequired'),
				type: "error"
			});
			return false;
		}

		return true;
	};
	const { t } = useI18n()
	// =====================获取用例详情==========================
	onMounted(() => {
		if (prop.case_id){
			getCaseDetail(prop.case_id)
		}
		loadUploadFiles()
	})
	// 定义获取用例详情的方法
	async function getCaseDetail(caseId){
		// 重置用例数据与 form-data 相关状态
		Object.assign(caseData, initCaseData());
		bodyType.value = "json";
		formFieldName.value = "file";
		selectedUploadId.value = null;
		const res = await api.getCaseDetailApi(caseId)
		if (res.status===200){
			// 保存用例对象
			caseObj = res.data || {}
			// 把用例数据添加到用例编辑页面
			caseData.title = caseObj.title || "”"
			// 有绑定接口时用 interface 的 url/method；无接口时用 request 中的 method、url（如导入用例）
			if (caseObj.interface) {
				caseData.interface = {
					url: caseObj.interface.url ?? "/",
					method: (caseObj.interface.method || "get").toString().toLowerCase()
				}
			} else {
				caseData.interface = {
					url: caseObj.request?.url ?? "/",
					method: (caseObj.request?.method || "get").toString().toLowerCase()
				}
			}
			caseData.catalog = caseObj.catalog || null
			caseData.setup_script = caseObj.setup_script || ""
			caseData.teardown_script = caseObj.teardown_script || ""
			caseData.file = caseObj.file || []
			caseData.headers = JSON.stringify(caseObj.headers || {})
			caseData.request.json = JSON.stringify(caseObj.request?.json || {})
			caseData.request.data = JSON.stringify(caseObj.request?.data || {})
			caseData.request.params = JSON.stringify(caseObj.request?.params || {})
			// 根据已保存的请求体/文件，智能推断当前 bodyType
			const req = caseObj.request || {}
			const hasJsonBody = req.json && Object.keys(req.json || {}).length > 0
			const hasDataBody = req.data && Object.keys(req.data || {}).length > 0
			const hasFiles = Array.isArray(caseObj.file) && caseObj.file.length > 0
			if (hasFiles) {
				bodyType.value = "form-data"
				const first = caseObj.file[0]
				if (first && first.field) {
					formFieldName.value = first.field
				}
				if (first && first.upload_id) {
					selectedUploadId.value = first.upload_id
				}
			} else if (hasDataBody) {
				bodyType.value = "data"
			} else if (hasJsonBody) {
				bodyType.value = "json"
			} else {
				bodyType.value = "json"
			}
		}
	}
	// 监听case_id的变化,如果获取到case_id则执行获取用例详情的方法
	watch(() => prop.case_id, (val) => {
		if (val !== '') {
			getCaseDetail(val)
		}
	})
	// =====================编辑并保存用例==========================
	async function EditCase(){
		// 第一步：前置校验，失败直接终止
		if (!validateJsonFields()) {
			return; // 校验失败，不执行后续保存逻辑
		}
		const params = {
			title: caseData.title,
			file: caseData.file,
			setup_script: caseData.setup_script,
			teardown_script: caseData.teardown_script,
			headers: safeJsonParse(caseData.headers).data,
			request: {
				method: (caseData.interface?.method || "get").toString().toLowerCase(),
				url: caseData.interface?.url ?? "/",
				params: safeJsonParse(caseData.request.params).data
			},
			interface: caseObj.interface ? caseObj.interface.id : null,
			catalog: caseData.catalog
		}
		if (bodyType.value==="json"){
			params.request.json = safeJsonParse(caseData.request.json).data
		} else if (bodyType.value==="data") {
			params.request.data = safeJsonParse(caseData.request.data).data
		} else if (bodyType.value==="form-data") {
			if (formFieldName.value && selectedUploadId.value) {
				const files = [
					{
						field: formFieldName.value,
						upload_id: selectedUploadId.value,
					}
				]
				params.file = files
				// 同步更新本地 caseData.file，保证保存后当前组件状态与后端一致
				caseData.file = files
			} else {
				params.file = []
				caseData.file = []
			}
		}
		const res = await api.modiftyCaseApi(prop.case_id,params)
		if (res.status === 200){
			// 重新获取用例列表，保持目录树与数据同步
			await pstore.getCaseList()
			ElNotification({
				title: t('caseSaveSuccess'),
				type: "success"
			})
		} else{
			ElNotification({
				title: t('caseSaveFail'),
				message: res.data,
				type: "error",
			})
		}
	}
	// =====================复制用例==========================
	// 点击复制按钮
	async function copyCase(){
		// 第一步：前置校验，失败直接终止
		if (!validateJsonFields()) {
			return; // 校验失败，不执行后续保存逻辑
		}
		// 现有用例的所有信息都保持不变，只修改用例标题
		// project 优先使用原用例的项目ID；若不存在则回退到当前选中项目
		let projectId = null
		if (caseObj.project) {
			projectId = typeof caseObj.project === 'object' ? caseObj.project.id : caseObj.project
		} else if (pstore.pro && pstore.pro.id) {
			projectId = pstore.pro.id
		}
		const params = {
			title: caseData.title + "_copy",
			file: caseData.file,
			setup_script: caseData.setup_script,
			teardown_script: caseData.teardown_script,
			headers: safeJsonParse(caseData.headers).data,
			request: {
				method: (caseData.interface?.method || "get").toString().toLowerCase(),
				url: caseData.interface?.url ?? "/",
				params: safeJsonParse(caseData.request.params).data
			},
			interface: caseObj.interface ? caseObj.interface.id : null,
			catalog: caseData.catalog,
			project: projectId
		}
		if (bodyType.value==="json"){
			params.request.json = safeJsonParse(caseData.request.json).data
		} else if (bodyType.value==="data") {
			params.request.data = safeJsonParse(caseData.request.data).data
		} else if (bodyType.value==="form-data") {
			if (formFieldName.value && selectedUploadId.value) {
				params.file = [
					{
						field: formFieldName.value,
						upload_id: selectedUploadId.value,
					}
				]
			} else {
				params.file = []
			}
		}
		const res = await api.addCaseApi(params)
		if (res.status === 201){
			// 重新获取用例列表，保证复制出的新用例体现在左侧目录树中
			await pstore.getCaseList()
			ElNotification({
				title: t('caseCopySuccess'),
				type: "success"
			})
		} else{
			ElNotification({
				title: t('caseCopyFail'),
				message: res.data,
				type: "error",
			})
		}
	}
	// =====================删除用例==========================
	async function deleteCase(){
		ElMessageBox.confirm(
		    t('caseDeleteConfirmText', { title: caseData.title }),
		    t('commonWarningTitle'),
		    {
		      confirmButtonText: t('commonConfirm'),
		      cancelButtonText: t('commonCancel'),
		      type: 'warning',
		    }
		  )
		    .then(async () => {
				// 调用删除的接口请求
				const res = await api.delCaseApi(prop.case_id)
				if (res.status === 204){
					ElMessage({
					  type: 'success',
					  message: t('caseDeleteSuccess', { title: caseData.title }),
					})
					// 重新获取用例列表，保持目录树与数据同步
					pstore.getCaseList()
				} else {
					ElMessage({
					  type: 'error',
					  message: t('caseDeleteFail', { title: caseData.title }),
					})
				}
		    })
		    .catch(() => {
		      ElMessage({
		        type: 'info',
		        message: t('caseDeleteCanceled'),
		      })
		    })
	}
	// =====================运行用例==========================
	let isShowDraw = ref(false)
	let responseData = ref({})
	async function runCase(){
		// 第一步：前置校验，失败直接终止
		if (!validateJsonFields()) {
			return; // 校验失败，不执行后续保存逻辑
		}
		// 确保已选择测试环境
		if (!pstore.env) {
			ElMessage({
				type: 'warning',
				message: t('selectEnvPlaceholder'),
				duration: 1500,
			});
			return;
		}
		// 获取请求数据（params 始终根据当前填写内容发送）
		const params = {
			env: pstore.env,
		    cases: {
				title: caseData.title,
			    interface: caseData.interface,
				headers: safeJsonParse(caseData.headers).data,
				request: {
					method: (caseData.interface?.method || "get").toString().toLowerCase(),
					url: caseData.interface?.url ?? "/",
					params: safeJsonParse(caseData.request.params).data
				},
				setup_script: caseData.setup_script || "",
				teardown_script: caseData.teardown_script || "",
			 }
		}
		if (bodyType.value==="json"){
			params.cases.request.json = safeJsonParse(caseData.request.json).data
		} else if (bodyType.value==="data") {
			params.cases.request.data = safeJsonParse(caseData.request.data).data
		} else if (bodyType.value==="form-data") {
			if (!formFieldName.value || !selectedUploadId.value) {
				return ElMessage({
					type: 'error',
					message: t('fileUploadFail') || '请选择文件字段名和已上传文件',
				})
			}
			params.cases.file = [
				{
					field: formFieldName.value,
					upload_id: selectedUploadId.value,
				}
			]
		}
		// 2、调用接口发送请求
		const res = await api.runInterfaceCase(params)
		// 3、根据返回结果决定展示方式
		if (res.status === 200) {
			// 接口调试引擎返回结构：单条用例的结果对象（包含 name/status/log_data 等）
			const data = res.data || {}
			responseData.value = data
			// 若状态为 error，提取第一条 ERROR 日志作为弹窗提示（比如环境变量缺失）
			if (data.status === 'error' && Array.isArray(data.log_data)) {
				const firstError = data.log_data.find(item => Array.isArray(item) && item[0] === 'ERROR')
				if (firstError && firstError[1]) {
					ElMessage({
						type: 'error',
						message: firstError[1],
						duration: 5000,
					})
				}
			}
			// 无论成功/失败，都展示结果抽屉（包含日志）
			isShowDraw.value = true
		} else {
			// 后端/拦截器已通过 ElMessage 提示错误，这里仅避免弹出空白结果抽屉
			isShowDraw.value = false
		}
	}
</script>

<style lang="scss" scoped>
	.script_code{
		display: flex;
		.code{
			flex: 1
		}
		.mod{
			width: 300px;
			// width: 100%;
			height: 300px; /* 继承外层mod的高度 */
			overflow-y: auto; /* 垂直方向溢出时显示滚动条，水平方向不滚动 */
			overflow-x: hidden; /* 隐藏水平滚动条，避免按钮换行导致横向滚动 */
			.add_code{
				margin: 0 0 10px 10px;
			}
		}
	}
	.form-data-box {
		margin-top: 10px;
		.tip {
			margin-bottom: 8px;
			color: #888;
			font-size: 13px;
		}
	}
	.btns{
		text-align: center;
	}
</style>