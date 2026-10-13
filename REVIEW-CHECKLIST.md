# v1.0.6 修复与验证 / Review / 修正確認

2026-10-12。本文件对应用户提供的 A–E 审查清单。所有测试使用合成条目或用户明确提供的本机资料，不分发游戏素材、攻略缓存或作者全文。提交保存在本地，未自动推送 GitHub。

## 逐项状态

| 项目 | 状态 | 改法与验证依据 |
| --- | --- | --- |
| A1 | 已修复并有测试 | 完整同步后的 24 小时内，热门只重读前三页，最新遇整页已缓存时停止；持有变化只重算及补详情。合成列表首次 12 次、再次 4 次请求，覆盖记录不变；真实观察循环测试确认不爬列表。缓存缺码仍完整查找，不能被增量早停截断。 |
| A2 | 已修复并有测试 | 非空失效 token 将对应流重置为首页并只重试一次；恢复完成、再次失败不循环、重置状态持久化均有回归测试。 |
| A3 | 已修复并有测试 | 相同角色副本分别保留，按 45×65 像素阈值内最近框匹配；两张→两张→卖一张、隐藏星级匹配、手动记录保留测试通过。 |
| B1 | 已修复并有测试 | 内容未变时不重建表格；按类别、ID、位置恢复选中和滚动。Windows Tk 实测不变帧和重排选择，以及三语言默认高度下纠正按钮可见性。 |
| B2 | 已修复并有测试 | 数值、添加、移除、清除手动商店均改用加锁的 Controller 方法；快照与导出也加锁。并发纠正/快照、独立状态副本及无效数值原子校验测试通过。 |
| B3 | 已修复并有测试 | 核查当时本机 1811 篇：均有阶段阵容，524 篇描述为空，故实施补详情。当前候选缺详情按攻略 ID 去重、间隔 60 秒，仅请求 detail。忙时重复请求和无列表调用测试通过。 |
| B4 | 已修复并有测试 | 无码且匹配有效的卡片按 ID 离线锁定；有码保持官方核对流程。离线、失效拒绝、有码分支测试通过。 |
| B5 | 已修复并有测试 | 前提文本先清理 HTML，规范化后少于两字的角色名跳过。带标签的流萤前提与单字“刃”测试通过。 |
| B6 | 已修复并有测试 | 角色、装备、材料明确按类别查名；无类别冲突记 warning。同 ID 角色/装备的名称及装备建议测试通过。 |
| B7 | 已修复并有测试 | 记录 last_seen；两次完整同步缺席才清理，锁定项保护；旧缓存视为新近见过。增量、中断、旧字段迁移、双次缺席与攻略码查找中的锁保护测试通过。 |
| B8 | 已修复并有测试 | 无适用模板时跳过 SIFT 与区域扫描；无库存装备模板时立即返回。本机学习的 custom matchTemplate 保留。空模板禁止 SIFT、学习图标匹配和区域跳过测试通过。 |
| B9 | 已修复并有测试 | 游戏识别仅支持简体中文的提示在界面常驻，英文/繁体窗口标题另外提示。生成建议、投资比较及位置/来源标签统一三语言，内部中文枚举保持。三语言分数一致、参数一致、枚举双向选择及布局测试通过；官方名称、效果与作者原文仍为来源中文。 |
| B10 | 已修复并有测试 | 按用户确认集约 50 金币、10 金币/1 利息且上限 5、刷新 2、费用到等级 5/6/7/9/9；生成文本明确标为通用估算。数值、利息和标识测试通过。 |
| C | 已修复并有测试 | 三语言 README/QUICKSTART 明确公开版无图标模板，商店标题 OCR 之外需手动补充或本机学习。历史头像/星级验证使用私有/学习模板由用户确认；空模板回归与公开包内容核对覆盖当前公开能力，不将历史验证当作公开版保证。 |
| D1 | 已修复并有测试 | 从 dist-info、包目录或固定版本官方来源收集许可和第三方声明；缺漏即报错。保留本地捕获补丁说明，manifest 禁止空许可项。包目录、官方回退、失败阻断及补丁说明测试通过。 |
| D2 | 已修复并有测试 | 用户允许后生成 windows-capture 2.0.1+cwa.headless1，仅修改依赖与版本元数据，保留原代码、原生字节与许可。统一 opencv-python-headless，pip check 通过；wheel 字节/RECORD 测试与冻结程序捕获、离线 OCR 回放通过。源码附可复现脚本。 |
| D3 | 已修复并有测试 | PyInstaller 移入开发依赖，开发步骤同步；运行包不含 .gitignore。检查文件与冻结模块后只排除未打包的 pip；当前包含 setuptools 代码/资源，真实保留其许可，PyInstaller 许可也保留。包含/排除条件与发布内容检查通过。 |
| D4 | 已修复并有测试 | User-Agent 使用 CurrencyWarAssistant/当前版本。版本回归测试通过。 |
| E1 | 已修复并有测试 | 报告定时器失败后继续调度；空结果和未变内容不重复写入；CLI 缺参数明确提示用法。错误写入重调度、变化写入次数和缺参数测试通过，既有参数保持。 |
| E2 | 已修复并有测试 | 搜索引用后移除无使用路径、捕获排除函数、热键残留、旧 SIFT 属性和旧透明度控件引用；阶段函数保留可达默认分支并简化冗余。默认阶段和移除符号测试通过。 |

## 本次完成的验证

- `python -m unittest discover -s tests -v`：90 项通过，包含原有测试和本次回归；Windows 窗口测试未跳过。
- `pip check`：通过，仅一个 OpenCV 分发包（headless）。
- Windows PyInstaller 构建成功；`tools/verify_release.py` 运行冻结版 v1.0.6，通过原生捕获导入、边框切换和自建测试窗口真实图像捕获。
- 使用用户此前提供的投资截图离线回放：冻结版识别“投资选择”、两个可见候选并生成建议，约 3 秒。截图中有遮挡，不声称识别了完整三项。
- 三语言深色界面和中文浅色界面用自建窗口检查；设置、纠正按钮和简体客户端提示可见。
- 公开包检查：压缩包完整、英文路径、无用户数据/游戏模板/研究资料；依赖许可清单无空项、单个 OpenCV，保留实际包含的 setuptools 和 PyInstaller 许可。

## 未验证的范围

本次额外尝试实时游戏捕获时未找到单一运行中的游戏窗口，因此该项没有完成；必需的自建窗口发布自检已通过。没有验证完整 A8·30 通关、独占全屏覆盖或所有分辨率。没有英文/繁体客户端场景识别实现，也不以界面语言切换声称支持这些客户端。无需用户补充信息即可交付本次 A–E 修复；如要验证这些扩展范围，需要另行提供对应运行场景。

## English

All A–E items above are fixed with regression tests or documented package checks. The full suite passes 90 tests; the frozen v1.0.6 executable passes native capture, window-mode checks and offline investment OCR. A second synthetic manual refresh uses 4 requests instead of 12. The runtime contains one headless OpenCV; the reproducible capture metadata patch retains original source/native bytes and notices. Setuptools is actually bundled, so its notices are retained. Recognition supports only the Simplified Chinese game client. Official source names, effects and prose remain Chinese. No live-game capture was completed during this run because no single running game window was available; a full A8·30 completion is not claimed.

## 日本語

A–E の全項目を修正し、回帰テストまたは配布内容確認を実施。90 件のテスト、凍結版 v1.0.6 の実ウィンドウ取得・枠切替・投資画像のオフライン OCR が通過。合成データでは再更新の要求が 12 回から 4 回に減少。OpenCV は headless 一種類で、捕獲 wheel の再現可能な依存情報パッチは元のソース・ネイティブバイナリ・許諾文を保持。実際に同梱された setuptools の許諾文も保持。ゲーム認識は簡体字クライアントのみ対応し、公式名・効果・作者原文は中国語のまま。今回は単一の実行中ゲーム画面が見つからず、ライブゲーム取得と A8·30 全体クリアを検証済みとはしていません。
