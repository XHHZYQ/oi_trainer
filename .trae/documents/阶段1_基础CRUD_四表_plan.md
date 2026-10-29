# 阶段 1：基础 CRUD（account / course / class_group / knowledge_point）

## 1. 概述

按需求设计文档 §8 阶段 1，先落地 4 张表的基础 CRUD：`account`、`course`、`class_group`、`knowledge_point`。

覆盖任务清单中与本 4 表相关的部分：

| 任务 | 内容 | 落点 |
| --- | --- | --- |
| 1.1 | 用户创建/详情/更新/软删除（唯一冲突处理） | account |
| 1.2 | 用户列表：分页 + 动态过滤 + 排序 | account |
| 1.3 | 课程 CRUD + 状态流转（软删后 code 可复用） | course |
| 1.4 | 批量创建 / 批量软删除 | course |
| 1.5 | 存在性判断 / 计数 | account/course repository |
| 1.6 | 知识点树基础 CRUD（自引用、order_index） | knowledge_point |

class_group 在任务清单中无专属条目，本轮做基础 CRUD（乐观锁/并发报名留阶段 3，`enrolled_count`/`version` 不允许通过 CRUD 接口修改）。

**已确认的 3 个决策**：
1. 实现 `POST /api/v1/auth/login` 签发 JWT；查询类接口公开，写接口（增删改）用 `require_role` 保护。
2. 练习产物：`scripts/阶段1_基础_crud.py`（直连 DB、可重复执行，风格对齐 `seed_base.py`）。
3. 面试总结沉淀为 `docs/interview/阶段1.md`。

## 2. 现状分析（基于实际代码）

- 28 张表模型与迁移已全部建好（`app/models/org.py`、`app/models/problem.py`），`alembic upgrade head` 已执行，`/health` 正常。
- 已有基础设施：
  - [db.py](file:///Users/xuhonghui/Project/oi_trainer/app/core/db.py)：全异步 `AsyncSession`，`get_session`（Depends 用）/ `new_session`（脚本用）。
  - [deps.py](file:///Users/xuhonghui/Project/oi_trainer/app/core/deps.py)：`get_current_user` / `require_role` 已就绪，但 `tokenUrl="/api/v1/auth/login"` 指向的登录接口尚不存在。
  - [security.py](file:///Users/xuhonghui/Project/oi_trainer/app/core/security.py)：bcrypt 哈希 + JWT 签发/解码已就绪。
  - [response.py](file:///Users/xuhonghui/Project/oi_trainer/app/core/response.py)：`EnvelopeRoute` 自动包 `{code, data, msg}`，路由返回值直接给 data 即可。
  - [exceptions.py](file:///Users/xuhonghui/Project/oi_trainer/app/core/exceptions.py)：`BusinessException(msg, code)` 全局兜底。
- `app/schemas/`、`app/repositories/`、`app/services/` 目前为空目录，`app/api/` 只有 `health.py`。
- 种子数据已有 admin / teacher01 / teacher02 / student01~20（密码均 `123456`）、2 门课程各 1 个班、10 节点知识点树。
- 表字段事实（写 schema 时以此为准）：
  - `account` / `course` 有 `deleted_at`（软删除 + 部分唯一索引）；`class_group` / `knowledge_point` 无 `deleted_at`（物理删除）。
  - `class_group` 有 CHECK 约束（`capacity>0`、`start_date<=end_date`、`enrolled_count<=capacity`）与 `version` 乐观锁列。
  - `knowledge_point` 有 `uq_kp_code` 全局唯一、`parent_id` 自引用。
  - `course.code` 部分唯一（`WHERE deleted_at IS NULL`）——软删后 code 可复用，是脚本演示点。
- API 前缀约定：`/health` 无前缀；业务接口统一挂 `/api/v1`（与 `tokenUrl` 一致）。

## 3. 变更清单

### 3.1 新建 schemas 层

**`app/schemas/common.py`**
- `Page[T]`（SQLModel + Generic）：`items: list[T]`、`total: int`、`page: int`、`size: int`。
- `PageParams`：FastAPI 依赖，`page: int = 1`、`size: int = 20`（ge=1, le=100），暴露 `offset` 属性。
- `apply_sort(stmt, model, sort, allowed)`：排序解析工具，`sort="-created_at,id"` 形式，字段必须在 `allowed` 白名单内，非法字段抛 `BusinessException`。

**`app/schemas/auth.py`**
- `Token`：`access_token: str`、`token_type: str = "bearer"`。

**`app/schemas/account.py`**
- `AccountCreate`：username(64)、password(8~64)、role(AccountRole)、email/phone/real_name/avatar_url 可选。
- `AccountUpdate`：全部可选（real_name/email/phone/avatar_url/role/status/password）。
- `AccountRead`：id、username、email、phone、role、real_name、avatar_url、status、created_at、updated_at（不含 hashed_password/deleted_at）。

**`app/schemas/course.py`**
- `CourseCreate`：code、title、level，description/cover_url/total_hours/price_cents 可选。
- `CourseUpdate`：全可选 + `status`（用于状态流转）。
- `CourseRead`、 `CourseBatchDelete`（`ids: list[int]`）。

**`app/schemas/class_group.py`**
- `ClassGroupCreate`：course_id、name、teacher_id、campus、start_date、end_date、capacity(gt=0)。
- `ClassGroupUpdate`：name/campus/start_date/end_date/capacity/teacher_id/status 可选；**不含** enrolled_count/version/course_id。
- `ClassGroupRead`。

**`app/schemas/knowledge_point.py`**
- `KnowledgePointCreate`：code、name、parent_id 可选、level、description、order_index。
- `KnowledgePointUpdate`：name/parent_id/level/description/order_index 可选。
- `KnowledgePointRead`：含 children 嵌套可选字段（树接口用）。

### 3.2 新建 repositories 层（纯数据访问，练习 SQL 的落点）

每表一个文件，统一 async 函数、首参 `session: AsyncSession`。

**`app/repositories/account.py`**
- `create(session, *, hashed_password, **fields) -> Account`
- `get_by_id(session, account_id)`：带 `deleted_at IS NULL`。
- `exists_by_username(session, username) -> bool`：`SELECT EXISTS(...)`（任务 1.5）。
- `count(session, **filters)` / `list(session, filters, page, size, sort)`：动态 WHERE（role/status）+ `LIMIT/OFFSET` + 排序（任务 1.2）。
- `update(session, account_id, fields) -> Account | None`：ORM 方式 get→setattr→flush（演示 `onupdate=func.now()` 自动维护 `updated_at`），查询带 `deleted_at IS NULL`。
- `soft_delete(session, account_id) -> bool`：置 `deleted_at = now(utc)`。

**`app/repositories/course.py`**
- `create` / `get_by_id` / `count+list`（status/level 过滤）/ `update` / `soft_delete`：同 account 模式。
- `create_batch(session, items) -> list[Course]`：`session.add_all` 批量插入（任务 1.4）。
- `soft_delete_batch(session, ids) -> int`：Core 写法 `update(Course).where(Course.id.in_(ids), Course.deleted_at.is_(None)).values(deleted_at=...)`，返回 rowcount（`WHERE id = ANY(:ids)` 练习点）。

**`app/repositories/class_group.py`**
- `create` / `get_by_id` / `count+list`（course_id/status/teacher_id 过滤）/ `update` / `delete`（**物理删除**，FK 冲突由 service 转成业务异常）。

**`app/repositories/knowledge_point.py`**
- `create` / `get_by_id` / `update` / `delete`（物理删除）。
- `list_children(session, parent_id | None)`：`WHERE parent_id IS NULL / = :pid ORDER BY order_index`（任务 1.6 同层排序）。
- `list_all(session)`：树接口全量加载用。
- `has_children(session, kp_id) -> bool`。

### 3.3 新建 services 层（业务规则）

**`app/services/auth.py`**
- `login(session, username, password) -> Token`：按 username 查（带 `deleted_at IS NULL`）→ `verify_password` → `create_access_token(sub=user.id)`；失败抛 `BusinessException("用户名或密码错误")`。

**`app/services/account.py`**
- `create_account`：`exists_by_username` 预检（演示"先查后插"）→ 插库，捕获 `IntegrityError` 兜底转 `BusinessException("用户名/邮箱/手机号已存在")`（演示"唯一约束才是最终防线"，两者对比是面试点）；bcrypt 哈希密码。
- `update_account` / `soft_delete_account`：找不到（含已软删）抛 404 业务异常。

**`app/services/course.py`**
- 状态机校验：`draft→published→archived`、`archived→published`（恢复上架）；其余流转抛 `BusinessException("非法状态流转")`。
- `create_course`：code 冲突 IntegrityError → 业务异常（软删后可复用的演示留脚本）。
- `batch_delete_courses`：返回实际删除行数。

**`app/services/class_group.py`**
- 创建/更新前校验 `course_id`、`teacher_id` 存在；`start_date <= end_date` 应用层先校验（CHECK 兜底）。
- `delete_class_group`：捕获 FK `IntegrityError` → `BusinessException("该班级下存在选课/订单数据，不允许删除")`。

**`app/services/knowledge_point.py`**
- 创建/移动节点：校验 `parent_id` 存在。
- **防环**：改 `parent_id` 时沿新父节点向上循环查 parent 链，若链上出现自己则抛 `BusinessException("不能把节点挂到自己的子孙下")`（树小，循环查足够，文档明确"禁止环：应用层校验"）。
- 删除：`has_children` 为真则拒绝；FK（problem_knowledge_point）冲突捕获转业务异常。

### 3.4 新建 API 层

**`app/api/v1/__init__.py`**：`api_router = APIRouter(prefix="/api/v1")`，聚合以下 5 个子路由。

**`app/api/v1/auth.py`**（tags=["auth"]）
| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| POST | `/auth/login` | 公开 | `OAuth2PasswordRequestForm`（与 tokenUrl/Swagger Authorize 兼容）→ Token |
| GET | `/auth/me` | 登录 | 返回当前用户（演示 `get_current_user`） |

**`app/api/v1/accounts.py`**（tags=["account"]）
| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| POST | `/accounts` | admin | 创建用户（1.1） |
| GET | `/accounts` | teacher/admin | 列表：page/size + role/status 过滤 + sort（1.2） |
| GET | `/accounts/{id}` | teacher/admin | 详情（1.1） |
| PATCH | `/accounts/{id}` | admin | 更新（1.1） |
| DELETE | `/accounts/{id}` | admin | 软删除（1.1） |

**`app/api/v1/courses.py`**（tags=["course"]）
| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| POST | `/courses` | admin | 创建（1.3） |
| GET | `/courses` | 公开 | 列表：status/level 过滤 + 分页排序 |
| GET | `/courses/{id}` | 公开 | 详情 |
| PATCH | `/courses/{id}` | admin | 编辑 + 状态流转 |
| DELETE | `/courses/{id}` | admin | 软删除 |
| POST | `/courses/batch` | admin | 批量创建（1.4） |
| POST | `/courses/batch-delete` | admin | 批量软删除，返回 affected 行数（1.4） |

**`app/api/v1/classes.py`**（tags=["class_group"]）
| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| POST | `/classes` | teacher/admin | 创建班级 |
| GET | `/classes` | 公开 | 列表：course_id/status/teacher_id 过滤 + 分页排序 |
| GET | `/classes/{id}` | 公开 | 详情 |
| PATCH | `/classes/{id}` | teacher/admin | 更新（不含 enrolled_count/version） |
| DELETE | `/classes/{id}` | admin | 物理删除（FK 冲突转业务提示） |

**`app/api/v1/knowledge_points.py`**（tags=["knowledge_point"]）
| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| POST | `/knowledge-points` | admin | 创建（可挂父节点）（1.6） |
| GET | `/knowledge-points` | 公开 | `parent_id` 过滤查子节点（`parent_id=0` 约定查根），按 order_index 排序 |
| GET | `/knowledge-points/tree` | 公开 | 全量查 + 内存组装嵌套树 |
| GET | `/knowledge-points/{id}` | 公开 | 详情 |
| PATCH | `/knowledge-points/{id}` | admin | 更新（含移动节点，防环） |
| DELETE | `/knowledge-points/{id}` | admin | 删除（有子节点拒绝） |

所有 router 用 `route_class=EnvelopeRoute`（对齐 health.py）。

### 3.5 修改 [main.py](file:///Users/xuhonghui/Project/oi_trainer/app/main.py)

注册 `api_router`（一行 import + 一行 include），不动 lifespan 与 health。

### 3.6 练习脚本 `scripts/阶段1_基础_crud.py`

直连 DB（`new_session()`，调 service/repository 层），`python -m scripts.阶段1_基础_crud` 运行。每次运行生成 `run_id = uuid4().hex[:6]` 拼进 username/code，保证可重复执行。分节演示并打印：

1. **1.1 用户**：创建 → 详情 → 更新 → 重复 username 创建（演示唯一冲突兜底）→ 软删除 → 删除后同 email 可重建（**部分唯一索引验证**）。
2. **1.2 列表**：按 role=student 过滤 + size=5 翻两页 + `-created_at` 排序，打印每页用户名。
3. **1.3 课程**：创建（draft）→ 发布 → 归档 → 恢复发布；非法流转（archived→draft）演示报错；软删后同 code 重建成功。
4. **1.4 批量**：批量创建 3 门课 → 批量软删，打印 affected。
5. **1.5 存在性/计数**：`exists_by_username`、`count` 打印。
6. **1.6 知识点树**：创建父节点 + 两个子节点（不同 order_index）→ 查子节点验证排序 → 移动节点 → 防环演示（把父节点挂到自己子节点下，预期报错）→ 删有子节点的节点被拒 → 先删子后删父成功。

### 3.7 面试总结 `docs/interview/阶段1.md`

按「面试题 → 答案要点 → 本项目对应代码位置」组织，覆盖：

1. 软删除 vs 物理删除的设计权衡；为什么 `email`/`phone` 用部分唯一索引而 `username` 全局唯一。
2. "先查再插" vs "直接插 + 唯一约束兜底"（竞态窗口、IntegrityError 捕获）。
3. offset 分页原理与深分页问题（为 1.7 keyset 分页埋预告）。
4. 批量操作：`add_all` vs Core `insert`；`WHERE id = ANY(:ids)` 批量软删。
5. 枚举状态机：为什么状态流转要在应用层校验而非只靠 CHECK。
6. 自引用树形表设计：parent_id、同层排序 order_index、防环。
7. `updated_at` 自动维护（`server_default` + `onupdate`）；`expire_on_commit=False` 的作用。
8. `class_group.version` 乐观锁列的设计意图（预告阶段 3）。

## 4. 假设与决策

- 账号管理是管理员职责：写操作仅 admin，读操作 teacher/admin；课程/知识点写操作仅 admin；班级写操作 teacher/admin（主讲教练可管班）。
- 登录用 `OAuth2PasswordRequestForm`（表单 username/password），与 deps.py 的 `tokenUrl` 和 Swagger Authorize 按钮天然兼容。
- `class_group` / `knowledge_point` 物理删除（表上无 `deleted_at`，与文档一致）；FK 冲突统一捕获转业务异常。
- 排序参数统一 `sort="-created_at,id"` 形式 + 白名单校验，4 个列表接口复用 `apply_sort`。
- 列表默认过滤软删除行；不提供"查已删除"参数（管理端回收站不在本轮范围）。
- 递归 CTE 子树查询是阶段 2 任务 2.5，本轮树接口只做全量组装。

## 5. 验证

1. `uv run uvicorn app.main:app --reload` 启动后 `/docs` 可见 5 组接口；`POST /api/v1/auth/login` 用 admin/123456 拿到 token，Authorize 后写接口可调。
2. 未登录调写接口返回 401 信封；student 登录调写接口返回 403。
3. `python -m scripts.阶段1_基础_crud` 全部 6 节演示按预期输出（含预期报错的两处），重复运行不冲突。
4. `uv run pytest` 通过（不破坏 test_health）。
5. 手动 SQL 抽查：软删的 account `deleted_at` 非空且同 email 新行插入成功；批量软删后 `course` 行数与 affected 一致。
