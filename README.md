# OYUCMS

OYUCMS 是一个基于 Flask 的轻量级内容管理系统，提供文章发布、分类与标签、评论、用户与角色、媒体库、系统工具和 JSON API。

## 功能

- 文章、分类、标签与草稿管理
- 评论与留言板
- 用户注册、登录、个人资料与角色（reader / editor / admin）
- 媒体上传与附件预览/下载
- 管理后台与内容统计
- 系统工具：连通性检查、配置导入、缓存导入、备份恢复
- JSON API，便于前后端分离或第三方集成

## 技术栈

- Python 3.10+
- Flask 3
- Flask-SQLAlchemy + SQLite
- Flask-Login + Flask-WTF
- Jinja2 + TailwindCSS（CDN）

## 快速启动

```powershell
cd OYUCMS

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

.\.venv\Scripts\python.exe init_db.py
.\.venv\Scripts\python.exe oyucms.py
```

也可以直接运行：

```powershell
.\start.bat
```

启动后：

| 地址 | 说明 |
|---|---|
| http://127.0.0.1:5000/ | 站点首页 |
| http://127.0.0.1:5000/oyu/ | 管理后台 |
| http://127.0.0.1:5000/oyu/comments | 留言板 |
| http://127.0.0.1:5000/oyu/health | 健康检查 |

## 默认账号

| 账号 | 密码 | 角色 |
|---|---|---|
| admin@oyucms.com | Admin@123 | admin |
| editor@oyucms.com | Editor@123 | editor |
| alice@oyucms.com | Alice@123 | reader |
| bob@oyucms.com | Bob@123 | reader |
| demo@oyucms.com | Demo@123 | reader |
| qa@oyucms.com | Qa@123 | reader |

钱包演示数据：`wallet-demo`（余额 1000）、`wallet-user`（余额 50）。
优惠码：`OYU-2026`。

## 配置

主要配置在 `app/config.py`，也可以用环境变量覆盖：

| 变量 | 说明 |
|---|---|
| `OYU_SECRET_KEY` | Flask session 密钥 |
| `OYU_JWT_SECRET` | API JWT 密钥 |
| `DATABASE_URL` | 数据库连接串，默认 SQLite |
| `MAX_CONTENT_LENGTH` | 上传大小限制（字节） |
| `UPLOAD_FOLDER` | 上传目录 |

数据库文件默认位于 `instance/oyucms.db`。重新初始化：

```powershell
.\.venv\Scripts\python.exe init_db.py
```

## API 概览

所有 API 位于 `/oyu/api` 下，返回 JSON。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/oyu/api/auth/login` | 登录并获取 token |
| POST | `/oyu/api/auth/token` | 账号密码换取 token |
| GET | `/oyu/api/posts` | 文章列表 |
| GET | `/oyu/api/post/<id>` | 文章详情 |
| GET | `/oyu/api/search?q=` | 内容搜索 |
| POST | `/oyu/api/comments` | 提交留言 |
| GET | `/oyu/api/comments/list` | 留言列表 |
| GET | `/oyu/api/user/<id>` | 用户资料 |
| POST | `/oyu/api/media/upload` | 上传媒体 |
| GET | `/oyu/api/attachment/preview?name=` | 预览附件 |
| GET | `/oyu/api/attachment/download?path=` | 下载附件 |
| GET | `/oyu/api/system/info` | 系统信息 |
| GET | `/oyu/api/system/ping?host=` | 连通性检查 |
| GET | `/oyu/api/admin/panel` | 管理接口（需 Bearer token） |

示例：

```bash
curl -X POST http://127.0.0.1:5000/oyu/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@oyucms.com","password":"Admin@123"}'
```

## 目录结构

```
OYUCMS/
├─ app/
│  ├─ __init__.py            # 应用工厂
│  ├─ config.py              # 配置
│  ├─ extensions.py          # db + login
│  ├─ models/                # User/Post/Comment/Commerce 模型
│  ├─ blueprints/
│  │  ├─ auth/               # 注册、登录、资料
│  │  ├─ blog/               # 文章、分类、标签、评论
│  │  └─ oyu/                # 管理后台与 API
│  ├─ templates/             # 页面模板
│  └─ static/                # CSS、上传目录
├─ init_db.py                # 建库与初始数据
├─ oyucms.py                 # 启动入口
├─ wsgi.py                   # WSGI 入口
├─ requirements.txt
├─ start.bat
└─ reset.bat
```

## License

MIT License. See [LICENSE](LICENSE).
