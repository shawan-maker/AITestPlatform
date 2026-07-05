## 黑马理财系统

### 系统信息

- 系统路径：http://user-p2p-test.itheima.net



### 登录注册

#### 获取图片验证码

##### 基本信息

- `Path：/common/public/verifycode1/{r}`
- `Method:GET`
- 接口描述:

##### 请求参数

**URL参数**

- r: 随机数，示例：0.1426580900762553

##### 返回数据

- 响应状态码：200
- 返回数据：图片



#### 获取短信验证码

##### 基本信息

- `Path：/member/public/sendSms`
- `Method:POST`
- 接口描述:

##### 请求参数

**headers**

| 参数名称     | 参数值                            | 是否必填 | 示例 | 备注 |
| ------------ | --------------------------------- | -------- | ---- | ---- |
| Content-Type | application/x-www-form-urlencoded |          |      |      |
| Cookie       | JSESSIONID=99679F2B755D2C         |          |      |      |

**body**

| 参数名称      | 类型   | 是否必填 | 示例 | 备注           |
| ------------- | ------ | -------- | ---- | -------------- |
| phone         | string | 是       |      | 手机号         |
| imgVerifyCode | string | 是       |      | 验证码         |
| type          | string | 是       | reg  | 类型[reg:注册] |



##### 返回数据

- 响应状态码：200

- 状态码描述：

  - 200：短信发送成功
  - 100：图片验证码错误

  ```python
  发送成功：{"status":200,"description":"短信发送成功"}
  发送失败：{"status":100,"description":"图片验证码错误"}
  ```



#### 注册

##### 基本信息

- `Path：/member/public/reg`
- `Method:POST`
- 接口描述:

##### 请求参数

**headers**

| 参数名称     | 参数值                            | 是否必填 | 示例 | 备注 |
| ------------ | --------------------------------- | -------- | ---- | ---- |
| Content-Type | application/x-www-form-urlencoded |          |      |      |
| Cookie       | JSESSIONID=99679F2B755D2C         |          |      |      |

**body**

| 参数名称     | 类型   | 是否必填 | 默认值 | 备注                 |
| ------------ | ------ | -------- | ------ | -------------------- |
| phone        | string | 是       |        | 手机号               |
| password     | string | 是       |        | 密码                 |
| verifycode   | string | 是       |        | 图片验证码           |
| phone_code   | string | 是       |        | 手机验证码           |
| dy_server    | string | 是       | on     | 是否同意协议[on/off] |
| invite_phone | string | 否       |        | 邀请人               |



##### 返回数据

- 响应状态码：200

- 状态码描述：

  - 200：注册成功，`{"status":200,"description":"注册成功"}`
  - 100：图片验证码错误，`{"status":100,"description":"验证码错误!"}`
  - 100：短信验证码错误，`{"status":100,"description":"验证码错误"}`
  - 100：手机已存在，`{"status":100,"description":"手机已存在!"}`
  - 100：密码不能为空，`{"status":100,"description":"密码不能为空"}`
  - 100：请同意我们的条款，`{"status":100,"description":"请同意我们的条款"}`
  
  
  
  

#### 登录

##### 基本信息

- `Path：/member/public/login`
- `Method:POST`
- 接口描述:

##### 请求参数

**headers**

| 参数名称     | 参数值                            | 是否必填 | 示例 | 备注 |
| ------------ | --------------------------------- | -------- | ---- | ---- |
| Content-Type | application/x-www-form-urlencoded |          |      |      |

**body**

| 参数名称 | 类型   | 是否必填 | 示例 | 备注   |
| -------- | ------ | -------- | ---- | ------ |
| keywords | string | 是       |      | 手机号 |
| password | string | 是       |      | 密码   |



##### 返回数据

- 响应状态码：200

- 状态码描述：

  - 200：登录成功，`{"status":200,"description":"登录成功"}`
  - 100：用户不存在，`{"status":100,"description":"用户不存在"}`
  - 100：密码不能为空，`{"status":100,"description":"密码不能为空"}`
  - 100：密码错误1次，`{"status":100,"description":"密码错误1次,达到3次将锁定账户"}`
  - 100：密码错误2次，`{"status":100,"description":"密码错误2次,达到3次将锁定账户"}`
  - 100：密码错误3次，`{"status":100,"description":"由于连续输入错误密码达到上限，账号已被锁定，请于1.0分钟后重新登录"}`



#### 是否登录

##### 基本信息

- `Path：/member/public/islogin`
- `Method:POST`
- 接口描述:判断是否登录

##### 返回数据

- 响应状态码：200

- 状态码描述：

  - 200：已登录，`{"status":200,"description":"OK"}`

  - 250：未登陆，`{"status":250,"description":"您未登陆！"}`

  



### 开通账户

#### 实名认证

##### 基本信息

- `Path：/member/realname/approverealname`
- `Method:POST`
- 接口描述:

##### 请求参数

**headers**

| 参数名称     | 参数值                    | 是否必填 | 示例 | 备注 |
| ------------ | ------------------------- | -------- | ---- | ---- |
| Content-Type | multipart/form-data       |          |      |      |
| Cookie       | JSESSIONID=99679F2B755D2C |          |      |      |

**body**

| 参数名称 | 类型   | 是否必填 | 默认值 | 备注     |
| -------- | ------ | -------- | ------ | -------- |
| realname | string | 是       |        | 真实姓名 |
| card_id  | string | 是       |        | 身份证号 |

##### 返回数据

- 响应状态码：200

- 状态码描述：

  - 200：提交成功，`{"status":200,"data":{"card_id":"110****21X","realname":"李**"},"description":"提交成功!"}`
  - 100：姓名不能为空，`{"status":100,"description":"姓名不能为空"}`
  - 100：身份证号不能为空，`{"status":100,"description":"身份证号不能为空"}`
  
  

#### 获取认证信息

##### 基本信息

- `Path：/member/member/getapprove`
- `Method:POST`
- 接口描述:

##### 请求参数

- 无


##### 返回数据

- 响应状态码：200

- 响应数据：

  ```json
  {
    "is_email_open": "-1",
      "lastlogin_time": "1581056542",
      "group_status": "",
      "is_auth_user": "-1",
      "is_realname_open": "2",
      "is_corp": "-1",
      "business_license": "",
      "realname_remark": "sadf",
      "card_id": "513****049",
      "realname": "莫**",
      "isCert": "2",
      "realname_card": "1",
      "pay_pwd": "",
      "phone": "130****5678",
      "realname_status": "1",
      "trustType": "chinapnr",
      "pwd": "1",
      "email": "",
      "is_trust": "1"
  }
  ```



#### 开户

##### 基本信息

- `Path：/trust/trust/register`
- `Method:POST`
- 接口描述:

##### 请求参数

- 无

##### 返回数据

- 响应状态码：200

- 返回响应数据：

  ```json
{
  	"status": 200,
  	"description": {
  		"form": "<form name='easypaysubmit' id='easypaysubmit' target='_blank' method='post' action='http://mertest.chinapnr.com/muser/publicRequests'><input name='Version' type='hidden' value='10'/><input name='CmdId' type='hidden' value='UserRegister'/><input name='MerCustId' type='hidden' value='6000060007313892'/><input name='BgRetUrl' type='hidden' value='https://www.baidu.com/'/><input name='RetUrl' type='hidden' value='http://dev-www.zcbk.deayou.com/trust/chinapnr/register/return/20011318124917315444'/><input name='UsrId' type='hidden' value=''/><input name='UsrName' type='hidden' value=''/><input name='IdType' type='hidden' value='00'/><input name='IdNo' type='hidden' value='51343620000113288X'/><input name='UsrMp' type='hidden' value='13210001001'/><input name='UsrEmail' type='hidden' value=''/><input name='MerPriv' type='hidden' value='20011318124917315444'/><input name='ChkValue' type='hidden' value='1784F61D7A6FDB0C900808DEA6DCEA882A138E731234473B84CB2829DF2B66FF032E40697D9668DC4B054A2790BDCF1EF32D2DB4B807CAF7F89829BE7C10520C3AF44DEF8EA2DDD07141C49DDEC147ECEC6A3D8E7E3B751D5308171AB3131668D19822D7F05E2E7CAAC5DB1F5744821B4A8B439E9A4335614B6A2CD8E3467DE5'/><input name='CharSet' type='hidden' value='UTF-8'/></form><script>document.forms['easypaysubmit'].submit();</script>"
  	}
  }
  ```



#### 第三方开户接口

##### 基本信息

- `Path：http://mertest.chinapnr.com/muser/publicRequests`
- `Method:POST`
- 接口描述:

##### 请求参数

**headers**

| 参数名称     | 参数值                            | 是否必填 | 示例 | 备注 |
| ------------ | --------------------------------- | -------- | ---- | ---- |
| Content-Type | application/x-www-form-urlencoded |          |      |      |

**body**

| 参数名称 | 类型   | 是否必填 | 示例         | 备注     |
| -------- | ------ | -------- | ------------ | -------- |
| Version  | string | 是       | 10           | 版本号   |
| CmdId    | string | 是       | UserRegister | 消息类型 |
| ...      | ...    |          |              |          |



##### 返回数据

- 响应状态码：200



### 充值提现

#### 获取充值验证码

##### 基本信息

- `Path：/common/public/verifycode/{r}`
- `Method:GET`
- 接口描述:

##### 请求参数

**URL参数**

- r: 随机数，示例：0.1426580900762553

##### 返回数据

- 响应状态码：200
- 返回数据：图片



#### 充值

##### 基本信息

- `Path：/trust/trust/recharge`
- `Method:POST`
- 接口描述:

##### 请求参数

**headers**

| 参数名称     | 参数值                            | 是否必填 | 示例 | 备注 |
| ------------ | --------------------------------- | -------- | ---- | ---- |
| Content-Type | application/x-www-form-urlencoded |          |      |      |
| Cookie       | JSESSIONID=99679F2B755D2C         |          |      |      |

**body**

| 参数名称    | 类型   | 是否必填 | 默认值        | 备注     |
| ----------- | ------ | -------- | ------------- | -------- |
| paymentType | string | 是       | chinapnrTrust | 充值类型 |
| amount      | string | 是       |               | 充值金额 |
| formStr     | string | 是       | reForm        |          |
| valicode    | string | 是       |               | 验证码   |



##### 返回数据

- 响应状态码：200

- 状态码描述：

  - 200：
  - 100：验证码错误

  ```json
  {
  	"status": 200,
  	"description": {
  		"form": "<form name='easypaysubmit' id='easypaysubmit' target='_blank' method='post' action='http://mertest.chinapnr.com/muser/publicRequests'><input name='Version' type='hidden' value='10'/><input name='CmdId' type='hidden' value='NetSave'/><input name='MerCustId' type='hidden' value='6000060007313892'/><input name='UsrCustId' type='hidden' value='6000060011480141'/><input name='OrdId' type='hidden' value='20011216062778381338'/><input name='OrdDate' type='hidden' value='20200112'/><input name='GateBusiId' type='hidden' value='B2C'/><input name='OpenBankId' type='hidden' value=''/><input name='DcFlag' type='hidden' value='D'/><input name='TransAmt' type='hidden' value='100.00'/><input name='RetUrl' type='hidden' value='http://112.126.69.227:8101/trust/chinapnr/recharge/return/20011216062778381338'/><input name='BgRetUrl' type='hidden' value='https://www.baidu.com/'/><input name='OpenAcctId' type='hidden' value=''/><input name='CertId' type='hidden' value=''/><input name='MerPriv' type='hidden' value='238'/><input name='ChkValue' type='hidden' value='-101'/><input name='CharSet' type='hidden' value='UTF-8'/></form><script>document.forms['easypaysubmit'].submit();</script>"
  	}
  }
  ```



### 投资

#### 投资产品详情

##### 基本信息

- `Path：/common/loan/loaninfo`
- `Method:POST`
- 接口描述:

##### 请求参数

**headers**

| 参数名称     | 参数值                            | 是否必填 | 示例 | 备注 |
| ------------ | --------------------------------- | -------- | ---- | ---- |
| Content-Type | application/x-www-form-urlencoded |          |      |      |
| Cookie       | JSESSIONID=99679F2B755D2C         |          |      |      |

**body**

| 参数名称 | 类型 | 是否必填 | 默认值 | 备注   |
| -------- | ---- | -------- | ------ | ------ |
| id       | int  | 是       |        | 产品id |

##### 返回数据

- 响应状态码：200

- 状态码描述：

  - 200：OK
  - 

  ```json
  {
  	"status": 200,
  	"data": {
  		"attachment_ids": "",
  		"loan_info": {
  			"tender_count": "0",
  			"add_date": "2019-10-29",
  			"tender_amount_min": 10.00,
  			"wait_amount": "5000.00",
  			"use": "周转",
  			"period_name": "5个月",
  			"award_status": -1,
  			"additional_amount_max": 0.00,
  			"serialno": "201910290017",
  			"isCert": "2",
  			"overdue_time": "1970-01-01 08:00:00",
  			"password": "xiuzheng17",
  			"password_status": true,
  			"category_id": "6",
  			"additional_name": "null+0.00%",
  			"id": "56",
  			"catePic": "http://112.126.69.227:8085/loan/borrowtype/20170720/8c0db873b42eabe4c3d495b96996156d.gif",
  			"validate": 0,
  			"member_id": "213",
  			"period": "5",
  			"apr": "5.00",
  			"amount": "5000.00",
  			"status_name": "流转中",
  			"category_type": "3",
  			"deposit_certificate": "-1",
  			"additional_status": -1,
  			"member_name": "15831017062",
  			"vouch_company_id": "1",
  			"is_auto": -1,
  			"hits": 19,
  			"contents": "1",
  			"credited_amount": "0.00",
  			"name": "TBD",
  			"progress": "0.00",
  			"tender_amount_max": 0.00,
  			"repay_type": "3",
  			"hidden_status": "1",
  			"is_company": -1,
  			"additional_apr": 0.00,
  			"tenderNum": "0",
  			"status": "3"
  		},
  		"member_approve": {
  			"is_email": "no",
  			"is_phone": "yes",
  			"is_realname": "yes",
  			"is_lock": "yes",
  			"username": "15831017062"
  		},
  		"company_info": {},
  		"member_info": {
  			"member_id": 213,
  			"birthday": "1998-10-29",
  			"industry_name": "未填",
  			"gender": "男",
  			"company_scale_name": "未填",
  			"member_name": "15831017062",
  			"marry_name": "未填",
  			"card_id": "130426199810290835",
  			"realname": "爱***",
  			"edu_name": "未填",
  			"graduated": "未填",
  			"imgPath": "http://112.126.69.227:8085",
  			"monthly_income_name": "未填",
  			"id": 208,
  			"company_office_name": "未填"
  		},
  		"member_loan_info": {
  			"late_amount": 0,
  			"late_repay": 0,
  			"late_repay_max": 0,
  			"loan_success_amount": 0,
  			"interestTotal": 5104.17,
  			"loan_count": 1,
  			"repay_success_count": 0,
  			"loan_success_count": 0,
  			"wait_repay_total": 0
  		},
  		"comList": [],
  		"iscompany": "-1",
  		"attaList": [],
  		"companyPic": "",
  		"member": {
  			"lastlogin_time": 1578815862,
  			"role": 1,
  			"group_status": 2,
  			"is_id5": -1,
  			"register_time": 1572834559,
  			"id": 238,
  			"register_ip": 611319874,
  			"is_login": 1,
  			"group": 1,
  			"is_email": -1,
  			"credit_point": 0,
  			"amount": 0.00,
  			"is_phone": 1,
  			"is_vip": -1,
  			"can_tender_new": 1,
  			"count": 9,
  			"lastlogin_date": "Jan 12, 2020",
  			"is_realname": 1,
  			"register_date": "Nov 4, 2019",
  			"is_auto": "-1",
  			"lock_time": 1578816087,
  			"register_type": 1,
  			"is_video": -1,
  			"self_loan": -1,
  			"phone": 13264228482,
  			"balance_amount": 50676.90,
  			"name": "13264228482",
  			"lastlogin_ip": 611319876,
  			"status": 1
  		},
  		"repay_type": {
  			"contents": "到期还本还息",
  			"name": "到期还本还息",
  			"remark": "",
  			"id": 3
  		},
  		"loan_roam": {
  			"portion_total": 1,
  			"assets": "1",
  			"portion_wait": 1,
  			"portion_yes": 0,
  			"interest_every": 104.170000,
  			"assets_use": "1",
  			"risk": "1",
  			"vouch_style": "admin17",
  			"tend_roam_min": 5000.00
  		},
  		"bondingCompany": {
  			"id": 1,
  			"name": "厦门帝网信息科技有限公司",
  			"capital": 30000.00,
  			"riskMoney": 10000.00,
  			"loginDate": "Oct 1, 2019 12:00:00 AM",
  			"type": -1,
  			"companyLogo": "http://112.126.69.227:8085/member/company/20191009/82500934-5d1d-4317-a112-2fb12b2d6144.png",
  			"provinceId": 1310,
  			"cityId": 1326,
  			"companyAddress": "思明区软件园二期望海路71号楼",
  			"companyTel": "0592-5866543",
  			"legal": "张健",
  			"legalTel": "15985837305",
  			"contactTel": "15985837305",
  			"companyIntro": "/member/company/20191009/7c08cec7-e6b1-4473-b169-c2e77b3edc3e.jpg",
  			"companySerialno": "DY201910200002",
  			"status": 1,
  			"companyMaterials": "a:4:{i:0;a:3:{s:5:\"title\";s:0:\"\";s:6:\"imgurl\"}}",
  			"contents": "厦门帝网信息科技有限公司,2010年06月07日成立，经营范围包括信息系统集成服务；计算机、软件及辅助设备批发；计算机、软件及辅助设备零售；通信设备零售；其他电子产品零售；互联网接入及相关服务（不含网吧）；其他互联网服务（不含需经许可审批的项目）其他未列明电信业务；固定电信服务；移动电信服务；承接所属电信业企业在其经营范围内委托的业务。"
  		}
  	},
  	"description": "OK"
  }
  ```

#### 投资

##### 基本信息

- `Path： /trust/trust/tender `
- `Method:POST`
- 接口描述:

##### 请求参数

**headers**

| 参数名称     | 参数值                            | 是否必填 | 示例 | 备注 |
| ------------ | --------------------------------- | -------- | ---- | ---- |
| Content-Type | application/x-www-form-urlencoded |          |      |      |
| Cookie       | JSESSIONID=99679F2B755D2C         |          |      |      |

**body**

| 参数名称           | 类型 | 是否必填 | 默认值 | 备注   |
| ------------------ | ---- | -------- | ------ | ------ |
| id                 | int  | 是       |        | 产品id |
| depositCertificate | int  | 是       | -1     |        |
| amount             | int  | 是       |        | 金额   |



##### 返回数据

- 响应状态码：200

- 状态码描述：

  - 200：
  - 100:
    - 投资金额不能为空
    - 投资密码不能为空

  ```python
  {
  	"status": 200,
  	"description": {
  		"form": "<form name='easypaysubmit' id='easypaysubmit' target='_blank' method='post' action='http://mertest.chinapnr.com/muser/publicRequests'><input name='Version' type='hidden' value='20'/><input name='CmdId' type='hidden' value='InitiativeTender'/><input name='MerCustId' type='hidden' value='6000060007313892'/><input name='OrdId' type='hidden' value='20011310425477231138'/><input name='OrdDate' type='hidden' value='20200113'/><input name='TransAmt' type='hidden' value='500.00'/><input name='UsrCustId' type='hidden' value='6000060011480141'/><input name='MaxTenderRate' type='hidden' value='0.20'/><input name='BorrowerDetails' type='hidden' value='[{\"BorrowerCustId\":\"6000060011478653\",\"BorrowerAmt\":\"500.00\",\"BorrowerRate\":\"0.90\",\"ProId\":\"\"}]'/><input name='IsFreeze' type='hidden' value='Y'/><input name='FreezeOrdId' type='hidden' value='20011310425477231138'/><input name='RetUrl' type='hidden' value='http://dev-www.zcbk.deayou.com/trust/chinapnr/tender/return/20011310425477231138'/><input name='BgRetUrl' type='hidden' value='https://www.baidu.com/'/><input name='MerPriv' type='hidden' value=''/><input name='ReqExt' type='hidden' value=''/><input name='ChkValue' type='hidden' value='7B516A12B6FB6FC997FDEC3A42AE15C53BFD8223440BF7CCD7505E06B11FA18661F823271FE087E2565E21365825D1EB84FE2C7F4D8E9B5383A895B42620C28AA089F816FD2CAE8CD188D70C5538E57AC7AA7DB9510F2285BB7BB9C57FB106DEA4328549391BF3C7910EDD3EEED35BD745693DB327F624AF35E86808D66E217C'/><input name='CharSet' type='hidden' value='UTF-8'/></form><script>document.forms['easypaysubmit'].submit();</script>"
  	}
  }
  ```



#### 我的投资列表

##### 基本信息

- `Path： /loan/tender/mytenderlist `
- `Method:POST`
- 接口描述:

##### 请求参数

**headers**

| 参数名称     | 参数值                            | 是否必填 | 示例 | 备注 |
| ------------ | --------------------------------- | -------- | ---- | ---- |
| Content-Type | application/x-www-form-urlencoded |          |      |      |
| Cookie       | JSESSIONID=99679F2B755D2C         |          |      |      |

**body**

| 参数名称 | 类型 | 是否必填 | 默认值 | 取值范围                                                     | 备注 |
| -------- | ---- | -------- | ------ | ------------------------------------------------------------ | ---- |
| page     | int  | 否       | 1      |                                                              | 页码 |
| status   | enum | 否       |        | recover：回款中；tender：投标中；recover_yes：已结清；over：已流标 | 状态 |



##### 返回数据

- 响应状态码：200

- 返回响应体

  ```json
  {
  	"isCert": "2",
  	"recover_amount_yes_total": 0,
  	"recover_amount_wait_total": 0,
  	"total_items": 2,
  	"page": 1,
  	"items": [{
  		"award_amount": "0.00",
  		"auto_status": "-1",
  		"recover_count": "0",
  		"transfer_status": "-1",
  		"cancel_count": "0",
  		"recover_interest": "0.00",
  		"recover_interest_yes": 0,
  		"deposit_certificate": "-1",
  		"recover_prepayment_fee": "0.00",
  		"recover_count_yes": "0",
  		"loan_member_name": "15810553242",
  		"id": "115",
  		"amount": "1000.00",
  		"status_name": "投标中",
  		"ind": "20011311303536360743",
  		"recover_status": "-1",
  		"repay_type": "4",
  		"transfer_member_name": "",
  		"serialno": "202001130001",
  		"tenderId": "115",
  		"recover_principal": "0.00",
  		"voucher_amt": "0.00",
  		"status": "-2",
  		"transfer_member_id": "0",
  		"trust_status": "-2",
  		"loan_name": "借款A",
  		"member_id": "243",
  		"add_ip": "2130706433",
  		"recover_overdue_fee": "0.00",
  		"loan_member_id": "148",
  		"award_interest": 0.0,
  		"recover_amount": 0,
  		"recover_amount_yes": "0.00",
  		"add_time": "1578886264",
  		"member_name": "13210001000",
  		"loanId": "84",
  		"recover_principal_yes": "0.00",
  		"loan_id": "84"
  	}, {
  		"award_amount": "0.00",
  		"auto_status": "-1",
  		"recover_count": "0",
  		"transfer_status": "-1",
  		"cancel_count": "0",
  		"recover_interest": "0.00",
  		"recover_interest_yes": 0,
  		"deposit_certificate": "-1",
  		"recover_prepayment_fee": "0.00",
  		"recover_count_yes": "0",
  		"loan_member_name": "15810553242",
  		"id": "114",
  		"amount": "500.00",
  		"status_name": "投标中",
  		"ind": "20011311270692883343",
  		"recover_status": "-1",
  		"repay_type": "4",
  		"transfer_member_name": "",
  		"serialno": "202001130001",
  		"tenderId": "114",
  		"recover_principal": "0.00",
  		"voucher_amt": "0.00",
  		"status": "-2",
  		"transfer_member_id": "0",
  		"trust_status": "-2",
  		"loan_name": "借款A",
  		"member_id": "243",
  		"add_ip": "2130706433",
  		"recover_overdue_fee": "0.00",
  		"loan_member_id": "148",
  		"award_interest": 0.0,
  		"recover_amount": 0,
  		"recover_amount_yes": "0.00",
  		"add_time": "1578886036",
  		"member_name": "13210001000",
  		"loanId": "84",
  		"recover_principal_yes": "0.00",
  		"loan_id": "84"
  	}],
  	"isStartTime": "yes",
  	"total_pages": 1,
  	"epage": 6,
  	"tender_amount_total": 1500.00,
  	"recover_amount_total": 0
  }
  ```

