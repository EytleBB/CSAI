# CSAI Frontend — CS2 军事简报风 UI 重设计

Date: 2026-03-31
File: `server/templates/index.html`

---

## 设计目标

将现有浅色商务风前端改为 CS2 T-side 作战室风格，使界面感觉像"专门为T方备赛的情报简报系统"。

---

## 视觉风格

- **底色**: `#0a0a0a` (近纯黑)，辅以 `#080808` 区分层级
- **主色调**: `#e8a020` (琥珀橙，T-side 色)
- **边框/分隔线**: `#1a1a1a` / `#1e1e1e`
- **文字层级**:
  - 主要内容: `#cccccc`
  - 次要标签: `#888888`
  - 暗标签 (letter-spacing uppercase): `#444444`
- **字体**: `'Segoe UI'` 正文 + `monospace` 数字/代码
- **排版风格**: UPPERCASE 标签 + letter-spacing 营造军事感

---

## Logo

- 文件: `Icon-t-patch-small.webp`（军事臂章，五角星+交叉匕首）
- 位置 B: header 左侧，36×36px，圆形裁切
- 位置 C: 热力图结果卡片右下角水印，44×44px，`opacity: 0.07`
- 路径: Flask 通过 `/static/logo.webp` 提供（需复制文件到 `server/static/`）

---

## 布局

### 桌面端 (≥ 768px)
```
┌─────────────────────────────────────────────────────┐
│  [logo] CSAI  T-SIDE TACTICAL PREP · MIRAGE  //...  │  ← header
├──────────────┬──────────────────────────────────────┤
│ TARGET       │  [tab: player1] [tab: player2] ...   │
│ DESIGNATIONS │  ─────────────────────────────────── │
│              │  PLAYERNAME         10/10 · 47 rounds │
│ [input×5]    │  ┌──────────────────────────────────┐ │
│              │  │                                  │ │
│ DEMO DEPTH   │  │      热力图 (大图，max-width:    │ │
│ [slider]     │  │       100%，正方形自适应)        │ │
│              │  │                          [水印]  │ │
│ [EXECUTE]    │  └──────────────────────────────────┘ │
│              │  ZONE DISTRIBUTION                    │
│ [状态显示]   │  [FULL BUY] zone rows...              │
│              │  [FORCE BUY] zone rows...             │
│              │  [ECO] zone rows...                   │
│              │  [PISTOL] zone rows...                │
└──────────────┴──────────────────────────────────────┘
```
- 左侧面板宽度: `240px`，固定
- 右侧: 热力图 `max-width: 600px`，居中显示，下方接区域统计

### 手机端 (< 768px)
单列堆叠：header → 输入区 → 按钮 → 状态 → 结果（热力图全宽 → 区域统计）

---

## 组件规格

### Header
- 高度: `~56px`
- 左: logo (36px) + 文字 "CSAI" (13px, #e8a020, letter-spacing:3px) + 副标题 "T-SIDE TACTICAL PREP · MIRAGE" (9px, #444)
- 右: `// OPPONENT INTELLIGENCE SYSTEM` (#2a2a2a, 9px) — 桌面端显示，手机端隐藏
- 下边框: `1px solid #e8a02033`

### 左侧输入面板（桌面）/ 顶部输入区（手机）
- 标签: `TARGET DESIGNATIONS` (#444, 9px, letter-spacing:2px)
- 输入框: `#0f0f0f` 背景，`#1e1e1e` 边框，`#888` 文字，左侧序号标签
- Focus 状态: 边框变 `#e8a02066`
- Slider: 轨道 `#1a1a1a`，填充+thumb `#e8a020`
- 按钮: `▶ EXECUTE SCAN`，全宽，`#e8a020` 背景，`#000` 文字，700 weight，letter-spacing:3px
- Disabled 状态: `#3a3a3a` 背景，`#666` 文字

### 状态显示
- running: 绿色闪烁点 + "SCANNING..." 字样，`#0f1a0a` 背景，`#2a4a1a` 边框
- done: 绿色点 + "ANALYSIS COMPLETE"
- error: 红色 `#1a0a0a` 背景，`#aa3030` 文字

### 进度信息（running时）
- 使用现有 `statusBar` + `statusText`，文字样式改为橙色军事感
- 旋转动画 spinner 颜色改为 `#e8a020`
- **不改动 JS 逻辑**，仅改 CSS 样式

### 玩家 Tabs
- 未选中: `#0f0f0f` 背景，`#444` 文字，`#1e1e1e` 边框
- 选中: `#e8a02022` 背景，`#e8a020` 文字，`#e8a020` 边框
- Hover: 边框变 `#e8a02066`

### 结果卡片
- 卡片头: `#0d0d0d` 背景，玩家名 `#e8a020` 14px，右侧元信息 `#444` 9px
- 热力图: 全宽显示（`width:100%; max-width:600px; margin:0 auto`），`border: 1px solid #1a1a1a`
- 水印: logo 绝对定位在热力图右下角，`opacity:0.07`

### 区域统计（热力图下方）
- 标题: `ZONE DISTRIBUTION` (#444, 8px, letter-spacing:2px)
- Round type 徽章保持现有4种颜色但改为深色版:
  - Full Buy: `#3a0a0a` 背景，`#cc4040` 文字
  - Force Buy: `#2a1500` 背景，`#cc7030` 文字
  - Eco: `#1a1a00` 背景，`#aaaa40` 文字
  - Pistol: `#001525` 背景，`#4090cc` 文字
- 进度条: `#1a1a1a` 底，`#e8a020` 填充，高度 3px

### 数据足够度 (Adequacy)
- 改为左侧面板底部的紧凑列表，每行: 玩家名 + 进度条 + 百分比
- 颜色规则保持，但改暗色版

### 未能分析玩家（Failed）
- `#1a0a0a` 背景，`#aa3030` 标题，`#6a2020` 分隔线

---

## 文件变更

1. `server/templates/index.html` — 完整重写 CSS + HTML 结构（JS 逻辑保持不变）
2. 新建 `server/static/` 目录
3. 复制 `D:/CSAI/Icon-t-patch-small.webp` → `server/static/logo.webp`
4. `server/web_server.py` — 添加 `app.static_folder` 指向 `server/static/`（如未配置）

---

## 不变的部分

- 所有 JS 逻辑（`startAnalysis`, `pollStatus`, `renderResults`, `renderFailed`, `renderAdequacy`, `switchPlayer`）
- API 调用逻辑
- HTML 结构中的 id 属性（`statusBar`, `resultsContainer`, `adequacyBar`, `failedSection` 等）
