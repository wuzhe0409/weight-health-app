# Weight Health — Windows 安装包构建

> **数据安全保证**：所有打包脚本只读取 `frontend/dist/`、`backend/seed/`（可选）、`schema.sql`。**绝不触碰** `backend/data/app.db`、用户的 `~/` 或 `%USERPROFILE%/.weight-health/`。朋友的数据库是空的，正符合本项目要分享给多人使用的设计。

---

## 三种构建方式

### 方式 A — GitHub Actions（最简单，点一下等 5 分钟）

1. 把这个项目推到 GitHub：
   ```bash
   git push origin feature/multi-date-backfill
   ```

2. 打开 GitHub → 仓库页面 → **Actions** → 左侧选 `build-windows` → 右上 **Run workflow** → 选分支 → 点击绿色按钮

3. 等 3-5 分钟，下载产物：
   - `WeightHealth-Windows-x64.zip`（绿色版单文件夹，解压即可用）
   - `WeightHealth-Setup-1.0.0.exe`（正式安装器，桌面图标 + 开始菜单）

4. 把 `.exe` 发给朋友

如果想要以后每次发布自动产生安装包，打 tag 即可：
```bash
git tag v1.0.0 && git push origin v1.0.0
# → 自动跑 Action，自动创建 GitHub Release 草稿
```

---

### 方式 B — 在朋友 / 任意 Windows PC 上直接构建

前置：Windows 10/11、Python 3.11+、Node.js 22+、Inno Setup 6（可选）

```cmd
cd path\to\weight-health-app
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r desktop\requirements-win.txt

cd frontend
npm ci
npm run build
cd ..

REM 干净版（不含 seed，给朋友用）：
set BUILD_DIST=1
call desktop\build-windows.bat

REM 含 seed 版（你本机调试用）：
call desktop\build-windows.bat
```

产物：
- `backend\dist\WeightHealth\` — 单文件夹版本
- `desktop\installer_output\WeightHealth-Setup-1.0.0.exe` — 安装器

---

### 方式 C — 我在你电脑上 Wine 模拟（不推荐）

在 arm64 M1 Mac 上能写但很慢。我没采用这条路。

---

## 数据流向验证

```
你的代码仓库 ──PyInstaller 读取──> backend\dist\WeightHealth\
                                       (含 static/, schema.sql, code)
                                       (写 BUILD_DIST=1 时不含 seed/)
                                                │
                                                ▼
朋友首次运行 ──app.db 写入──> %USERPROFILE%\.weight-health\app.db
                                                 (空数据库)
                                                 (与你的数据完全隔离)
```

如果朋友想重新开始 → 删 `%USERPROFILE%\.weight-health\` 整个目录即可。

---

## 自动化打包（开发用，你不需要）

修改 `frontend/` 或 `backend/` 后想让产物同步，CI 会自动跑；如果你在本机想再生成一份 Windows 包但没有 Win 电脑，按方式 A 在 GitHub Actions 上点一下即可。
