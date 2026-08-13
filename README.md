# Weight Health · 减脂记录与 AI 分析助手

## 项目结构

```
├── backend/          ← 共享：FastAPI 后端
├── frontend/         ← 共享：Vue3 前端
├── docs/             ← 产品文档 & 数据字典
│
├── web/              ← 🌐 网站版
│   ├── start.sh      → 一键启动 (后端 :8011 + 前端 :5173)
│   └── Makefile      → make dev / make build
│
├── desktop/          ← 🖥️ 桌面安装版
│   ├── build-mac.sh         → macOS .app + .dmg 构建
│   ├── build-windows.bat    → Windows .exe 构建（你的版本，含历史数据）
│   ├── build-clean-windows.bat → Windows 纯净版（朋友版，无历史数据）
│   ├── desktop_launcher.py  → 原生窗口启动器
│   └── icons/               → App 图标
│
└── releases/         ← 构建产物（DMG/EXE）
```

## 两种运行方式

### 🌐 网站版（开发/部署用）
```bash
cd web && bash start.sh
# 或
make dev
```
浏览器打开 http://localhost:5173

### 🖥️ 桌面版（独立应用）

**macOS：**
```bash
bash desktop/build-mac.sh
```
输出：`releases/Weight-Health-macOS-arm64.dmg`

**Windows：**
```bat
desktop\build-windows.bat
```
输出：`backend/dist/WeightHealth/WeightHealth.exe`

**Windows 纯净版（送朋友）：**
```bat
desktop\build-clean-windows.bat
```
无历史数据，从零开始。
