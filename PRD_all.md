# 实验教学资源授权平台 (E-TRAP) - 产品需求文档 (PRD v2.1)

## 1. 文档概述
*   **项目名称**：实验教学资源授权平台 (E-TRAP)
*   **版本**：v2.1 (Alignment with Functional Specs)
*   **核心目标**：构建一个统一的实验教学资源门户，集成商业软件授权、高性能计算资源、API服务及数据资源。
*   **技术栈**：Python 3.11+, FastAPI, SQLite (核心存储), Jinja2 (MVP Frontend).

## 2. 核心功能模块 (Aligned with func.md)

### 2.1 用户前台 (Student/Faculty Portal)

#### A. 资源大厅 (Resource Hub)
根据资源类型展示四大板块：
1.  **商业软件 (Commercial Software)**: SAS, MATLAB, Stata, Github Enterprise等。
2.  **计算资源 (Computing Power)**: DSLAB Giant GPU, MATLAB Cluster.
3.  **API服务 (API Services)**: LLM Token (GPT/Claude), GitHub Enterprise.
4.  **数据资源 (Data Service)**: Wind数据转发等 (后期建设).

#### B. 智能申请向导 (Smart Application Wizard)
*   **动态表单**:
    *   *通用*: 姓名、学号 (SSO预填).
    *   *软件类 (SAS)*: 用途 (教学/科研), 课程名称/项目编号.
    *   *算力类 (DSLAB)*: 预约时间段.
    *   *API类 (LLM)*: 预计Token量, 用途说明.

#### C. 个人中心 (My Dashboard)
*   **我的授权**: 查看历史申请、License Key、API Endpoint、有效期倒计时。
*   **通知中心**: 站内信 (集成短信/邮件通知状态).

### 2.2 管理后台 (Admin Dashboard)
*   **审批工作台**: 重点处理人工审核类资源 (GHE, DSLAB).
*   **资源配置**: 
    *   配额管理 (LLM Token Limit).
    *   水印配置 (Type A Zip Injection).

## 3. 业务流程逻辑

### Logic 1: 自动化授权与安全水印 (Type A)
*   **适用**: SAS, Stata.
*   **流程**: 用户申请 -> 自动验证 -> 后台注入加密水印 (`setup.dat` containing User/Time/Hash) -> 生成下载链接 -> 状态"已授权".

### Logic 2: 人工审核与双通道通知 (Type B)
*   **适用**: GitHub Enterprise, MATLAB Cluster.
*   **流程**: 用户申请 -> 状态"审核中" -> 通知管理员(SMS/Email) -> 管理员批准 -> 通知用户(Email/SMS).

### Logic 3: API 配额管理 (Type D)
*   **适用**: LLM Token.
*   **流程**: 用户申请 -> 系统分配内部Key (e.g. `sk-swufe-student-123`) -> 设定额度 (100k) -> 网关拦截计费.

## 4. 数据库模型调整 (SQLModel)

```python
class Resource(SQLModel, table=True):
    # ... basic fields ...
    category: str # "Software", "Compute", "API", "Data"
    
    # UI Prompt Configuration for Dynamic Forms
    # e.g. {"fields": [{"name": "course_name", "label": "Course Name", "type": "text"}]}
    form_schema: Dict[str, Any] = Field(default={}, sa_type=JSON)

class Application(SQLModel, table=True):
    # ... basic fields ...
    # Store dynamic field responses here
    user_input: Dict[str, Any] = Field(default={}, sa_type=JSON)
```

## 5. 开发路线图 (MVP Update)
1.  **Model Update**: Add `category` and `form_schema` to Resource model.
2.  **Seed Data**: Populate DB with examples of all 4 categories.
3.  **Frontend Update**: 
    *   Refactor `resources.html` to use Tabs/Sections.
    *   Make Application Modal dynamic based on `form_schema`.
4.  **Backend Logic**: Update `apply_resource` to validate `form_schema`.