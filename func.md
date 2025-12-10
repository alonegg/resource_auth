实验教学资源授权平台 (ETRAP) 设计方案

1. 项目概述

目标：构建一个统一的实验教学资源门户，集成商业软件授权、高性能计算资源、API服务及数据资源。
核心价值：实现“根据资源属性的差异化授权”——让标准软件零等待获取，让稀缺资源（算力/Token）可控分配，同时兼顾安全溯源与通知触达。

2. 核心功能模块设计

2.1 用户前台 (Student/Faculty Portal)

A. 资源大厅 (Resource Hub)

用户登录后（目前暂时不对接校内SSO，使用本地登陆。对接校内统一身份认证 SSO），根据资源类型展示四大板块：

商业软件 (Commercial Software): SAS, MATLAB, Stata, SPSS等。

计算资源 (Computing Power): DSLAB GPU, MATLAB Cluster.

API服务 (API Services): LLM Token (GPT/Claude/Local Models), GitHub Enterprise.

数据资源 (Data Service): Wind数据转发, 实验数据集 (建设中).

扩展板块: AI加速辅助工具.

功能点：

未申请状态：显示软件功能介绍、适用学科、官方文档链接、安装包下载地址（仅安装包，无License）。

已授权状态：显示License Key、License文件下载、API Endpoint、连接端口号、有效期倒计时。

资源链接：底部友情链接至学校信息中心（Office/OS下载），实现流量互导。

B. 智能申请向导 (Smart Application Wizard)

身份预填充：自动拉取姓名、学号/工号、学院、手机、邮箱。

场景区分：

教学用途：必填课程名称/代码。

科研用途：必填研究方向/项目编号。

动态表单：

选择SAS -> 弹出用途多选框。

选择DSLAB -> 弹出预约时间段选择 & DSLAB旧平台跳转指引。

选择LLM -> 弹出预计Token量申请 & 用途说明。

C. 个人中心 (My Dashboard)

我的授权：查看所有历史申请及当前有效的授权。

通知中心：系统站内信（与邮件/短信同步）。

2.2 管理后台 (Admin Dashboard)

A. 待办审批工作台 (Approval Queue)

高优先级：Github Enterprise, DSLAB算力, MATLAB集群, 大额LLM Token申请。

操作：一键批准/拒绝（支持填写拒绝理由）。

自动化辅助：系统自动检测用户是否已在 resource.swufe.edu.cn 完成前置预约（如果API打通），或人工核对。

B. 资源配置中心 (Resource Config)

配额管理：设置LLM Token的默认限额（如非教学用途默认10W），设置重置周期。

文件水印配置：配置哪些软件（如SAS）需要开启“动态压缩包水印”功能。

API Key池管理：导入OpenAI/Midjourney等上游Key，系统负责分发下游Key。

C. 审计与报表 (Audit & Analytics)

申请记录全视图：支持按时间、用户ID、资源类型（软件/算力/数据）、授权状态筛选。

数据看板：

热门资源Top10（用于决定明年采购预算）。

计算资源负载热力图。

学院使用分布图。

泄露溯源：输入泄露的文件特征（如从SAS包里提取的加密txt），反查申请人。

2.3 核心业务流程与逻辑 (Backend Logic)

逻辑一：自动化授权与安全水印 (Auto-Auth & Watermarking)

适用对象：SAS, Stata等本地运行软件。

流程：

用户提交申请 -> 系统验证基本信息完整。

关键步骤：系统后台调用脚本，生成一个名为 license_info.txt 的文件（包含申请人、时间、IP、加密哈希），通过命令行工具（如zip/7z）将其追加到标准的SAS License压缩包中。

系统生成该用户专属的下载链接。

状态即时变更为“已授权”。

逻辑二：人工审核与双通道通知 (Manual Review & Notification)

适用对象：GitHub Enterprise, MATLAB Cluster.

流程：

用户提交 -> 状态变为“审核中”。

通知管理员：

调用 Aliyun短信网关 -> 发送短信给值班管理员：“收到新的GHE申请，申请人：张三”。

调用 Mailgun -> 发送详情邮件给管理员。

管理员后台点击“批准” -> 触发后续动作（如调用GitHub API邀请用户进Org，或人工操作后点击确认）。

通知用户：

系统调用 Mailgun 发送包含激活链接的邮件。

（可选）发送Aliyun短信提醒用户查收。

逻辑三：API配额管理 (API Token Proxy)

适用对象：LLM API (GPT/Claude等)。

机制：不直接透传OpenAI Key，而是搭建一个 API Gateway（中转层）。

用户申请 -> 系统分配一个内部 Key (如 sk-swufe-student-123)。

系统设置该 Key 的总额度为 100,000 Token。

用户调用 https://api.swufe.edu.cn/v1/...。

网关拦截请求，扣除额度，转发至上游大模型服务。

额度耗尽，自动返回 HTTP 402/403 错误，并提示申请扩容。

逻辑四：混合预约流程 (Hybrid Booking)

适用对象：DSLAB 超大GPU算力。

流程：

平台提示用户先去 resource.swufe.edu.cn 锁定机时。

用户回到本平台提交申请，填写预约凭证（或时间段）。

管理员核对双边信息后批准。

平台发放具体的SSH登录端口和密码/Key。

3. 用户场景 (User Stories)

场景一：本科生小李申请 SAS 做作业

类型：自动化授权 + 安全水印 + 即时反馈

背景：统计学大三学生小李需要做期末作业，老师要求使用SAS。

操作：

登录平台，点击“商业软件” -> “SAS”。

填写用途：勾选“教学使用”，输入课程名“多元统计分析”。

点击“立即获取”。

后台处理：

系统自动验证通过。

触发打包脚本，将小李的学号加密写入 user_trace.dat 并放入SAS License Zip包中。

结果：页面直接刷新显示“下载License”按钮。小李下载并完成作业。

异常分支：如果该License文件后续在公网被发现，管理员提取包内文件即可定位到是小李泄露的。

场景二：王教授申请 GitHub Enterprise 版权

类型：人工审核 + 短信通知 + 第三方集成

背景：计算机学院王教授的团队需要私有仓库协作。

操作：

登录平台，点击“Github Enterprise”。

填写个人的Github账号（邮箱）。

提交申请。

后台处理：

系统通过 Aliyun短信 告知管理员：“王教授申请GHE，请处理。”

管理员收到短信，手机登录后台查看，确认为本校教师，点击“批准”。

结果：

系统自动发送邮件（Via Mailgun）给王教授：“您的申请已通过，请点击以下GitHub邀请链接加入组织。”

同时平台状态更新为“已授权”。

场景三：博士生张同学申请 LLM API 跑实验

类型：配额管理 + 政策限制 + 使用监控

背景：金融科技博士生需要调用GPT-4分析大量文本，非课程教学，属于科研。

操作：

点击“API服务” -> “LLM Token”。

填写用途：“论文文本情感分析”，勾选“非教学/科研”。

系统提示：“非教学用途默认限额 10W Token，如需更多请联系导师申请扩容。”

提交申请。

结果：

自动化规则判断（如未超过全校每日总限额）自动批准，或进入人工审核。

批准后，页面显示：

API Base URL: https://api.swufe.edu.cn/llm

API Key: sk-swufe-zhang-xyz

余额: 100,000 / 100,000

使用手册: Python调用示例代码。

后续：张同学跑了一半Token不够了，在平台点击“申请扩容”，管理员收到邮件通知进行评估。

场景四：管理员陈老师的日常运维

早晨：登录后台，查看“待办事项”。发现有3个DSLAB的GPU申请。

核对：打开另一个窗口 resource.swufe.edu.cn，确认这3个时间段确实已被预约。

处理：在ETRAP平台点击“全部通过”。系统自动通过Mailgun发送入群二维码或SSH Key给学生。

统计：月底，陈老师导出“月度资源使用报告”，查看Matlab集群的利用率，决定下学期是否需要购买更多节点。

配置：发现期末临近，SAS申请量激增，检查Aliyun短信包余额是否充足（虽然SAS主要靠邮件，但GHE等需要短信），确保通知服务不中断。

4. 技术架构简述

前端：React/Vue (响应式设计，适配手机查看申请状态)。

后端：Python (Django/FastAPI) 或 Node.js。

Python优势：方便处理Zip文件操作（SAS水印）、对接LLM API、处理数据转发逻辑。

数据库：MySQL (存储用户、申请记录) + Redis (LLM Token 计数器/缓存)。

集成服务：

身份认证：LDAP / CAS / OAuth2 (对接学校信息中心)。

消息通知：

Aliyun SMS SDK (高优先级通知)。

Mailgun API (常规通知、大段文字通知、License文件发送)。

文件处理：Python zipfile 库 (用于动态注入水印)。

5. 未来扩展 (Roadmap)

数据转发 (Data Proxy): 针对Wind/CSMAR等数据库，建立内网穿透或API转发鉴权，让师生在校外也能通过本平台鉴权后访问特定数据接口。

AI加速辅助: 集成学校自建的Coding Assistant或Paper Reading Assistant，作为SaaS服务在平台直接提供网页版入口。