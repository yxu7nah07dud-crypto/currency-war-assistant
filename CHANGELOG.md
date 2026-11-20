# Changelog / 更新记录 / 更新履歴

## v2.0.0 — 2026-11-20

- 中文：支持 4.7「入画奇航」标准博弈。按赛季隔离攻略和识别数据，加入职级、奇遇、主角光环和新版词缀分析。运营采用新商店权重与已确认的阵容、投资和装备。
- English: Added 4.7 Season 2 Standard Gambit rules, rank, Escapade and Plot Armor, season-specific recognition and guide caches, and updated shop and lineup advice.
- 日本語：4.7 シーズン2標準モードの職級・奇遇・主役補正、更新した敵特性とショップ比率、シーズン別の攻略・認識記録に対応。

## v1.0.7 — 2026-10-15

- 攻略同时匹配真实持有、已选环境、作者环境推荐与概念股的羁绊收益；修复未知持有时 10 分封顶抹平环境差异，信息不足只显示“候选参考”，不自动指挥买人。
- 官方配置头像按需缓存在本机，新增备战格子识别并用于前后台图像匹配；商店卡与持有严格区分，同头像多形态保留待确认，公开包不含游戏图标。攻略页显示实际匹配依据。
- Guide ranking now preserves environment relevance with unknown owned roles, labels weak evidence as references, and uses locally cached official portraits to recognize ownership. No game icons are bundled.
- 所持と環境の照合を修正し、情報不足は参考表示。公式画像を本機に保存して所持を認識し、ゲーム画像は配布に含めません。
- 新增“难度 / 投资”：手动 A8 难度跨重启保留，恢复自动或新对局清除；补上继续进度“财富造物主50”识别。主界面显示已选环境与当前效果。
- 准备阶段的已选环境详情不再误判为三选一，可读取“夜之半神概念股”等当前环境。观察到游戏内点卡、确认和离页后也自动记录实际投资；刷新/取消/超时不猜测选择。
- Added persistent manual A8 difficulty, resume-screen recognition, selected-environment tooltip OCR and read-only card/Confirm tracking. Owned tooltips no longer appear as three-choice screens; version remains v1.0.7.
- 手動 A8 難易度の再起動保持、再開画面認識、選択済み環境詳細の OCR とカード・確認操作の観察を追加。詳細画面を3択と誤判定せず、版はv1.0.7のまま。
- 修复投资推荐被上一页滚动位置遮住的问题：进入投资页或刷新候选后自动显示“现在怎么做”的推荐开头；同组选项保留手动滚动和标签页，短暂漏识别不会反复跳转。
- Investment advice now opens at the top when entering a choice page or refreshing its options. Repeated frames preserve the reader's scroll and tab, including temporarily missing OCR rows.
- 投資画面への移動・候補更新時は提案の先頭を表示。同じ候補ではスクロールとタブを保持し、一時的な認識漏れで表示を移動しません。
- 修复 A8 难度显示固定为 30 的问题：从游戏左上角难度横幅读取 50 等实际数值。
- 未识别到难度横幅时显示“待确认”，避免把默认值误当成当前难度。
- 新增敌人情报页面识别，读取敌人难度和同一行 DEBUFF，排除 UID、助手文字和下一步按钮；条件跨回合保留，新对局清除。
- 依据 V4.6 公开游戏规则的 55 项词缀数值和 0–300 敌人难度表自动分析，区分侵蚀变体和位面范围；提供组合风险、未激活羁绊估算和闲置装备影响。无需手填效果。
- 增加中/英/日规则摘要、对策与“识别纠正 → 敌人 / DEBUFF”入口，数值与名称可纠正，效果自动映射；版本号保持 v1.0.7。
- Added automatic opponent-screen OCR, 55 rule-based affix analyses, per-plane enemy scaling, combination warnings and three-language explanations. Conditions persist until New game; version remains v1.0.7.
- 敵情報の自動認識、55項目のルール分析、ステージ別難易度倍率、組合せリスクと三言語説明を追加。新しい対局まで保持し、版はv1.0.7のまま。

## v1.0.6 — 2026-10-12

### 中文

- 攻略更新改为增量，保留完整覆盖记录与中断续传；失效分页 token 重试一次。持有角色变化只补当前候选详情，按攻略去重并限频。
- 保留同角色多张副本；识别表格选中与滚动状态保留；手动纠正、快照与报告写入加锁，无码卡片可离线锁定。
- 前提检测清理 HTML、忽略单字角色名；角色/装备编号按类别查询；两次完整同步缺席的旧攻略清理并保护锁定项。空模板跳过无效 SIFT 扫描。
- 经济常量维持用户确认的数值，明确标为通用估算。公开版无模板能力与历史私有模板验证如实注明。
- 统一 headless OpenCV，附捕获 wheel 元数据补丁脚本；补齐上游许可并阻止缺漏打包，分离开发依赖、清理未包含的开发工具许可。
- 修复报告定时器和缺参数提示，清理无引用代码；生成建议和位置/来源标签支持三语言，明确游戏识别仅支持简体客户端。官方名称与原文不自动翻译。

### English

- Incremental public-guide refresh preserves complete coverage and resume progress; invalid cursors restart once. Owned-role changes fetch missing candidate details only, with deduplication and cooldown.
- Keep duplicate role cards and tree selection/scroll. Serialize corrections, snapshots and exports; lock valid code-less cards offline.
- Clean prerequisite HTML and skip one-character names. Query role/equipment IDs by kind, retire guides absent from two full scans while protecting locks, and skip empty-template feature scans.
- Centralize user-confirmed economy estimates; document public recognition limits and historical private-template checks.
- Use one headless OpenCV with a reproducible capture-wheel metadata patch. Retain upstream notices, fail packaging on missing licenses, separate build requirements and omit unused dev notices.
- Keep report scheduling after errors, validate missing CLI parameters, remove dead code, and translate generated advice and position/source labels. Recognition supports only the Simplified Chinese client; official source text remains unchanged.

### 日本語

- 攻略の増分更新で完全取得記録と再開位置を保持し、失効カーソルは一度だけ再試行。所持変更では候補詳細のみを重複排除・待機時間付きで補完。
- 同一キャラの複数カード、一覧の選択とスクロールを保持。修正・スナップショット・出力を排他制御し、コードなしの有効攻略もオフライン固定。
- 前提の HTML を除去し、一文字名の誤検出を防止。ID を種類別に検索し、2 回の完全取得に現れない未固定攻略を整理。空テンプレートの特徴抽出を省略。
- ユーザー確認済みの経済概算を集約。公開版の認識範囲と私有テンプレートでの過去検証を明記。
- headless OpenCV に統一し、捕獲 wheel の依存情報パッチを再現可能に。元の許諾文を保持し、不足時の配布を停止。開発依存を分離し未同梱ツールの許諾文を除外。
- 出力失敗後も定期保存を継続し、CLI 引数不足を案内。未使用コードを削除し、生成提案・位置・根拠を三言語化。ゲーム認識は簡体字のみ対応し、公式原文は保持。

## v1.0.5 — 2026-10-12

### 中文

- 在主操作栏“新对局”右侧增加“识别纠正”按钮，所有页面都能直接进入。
- “已识别”页的纠正与校准按钮移至表格上方，列表随空间缩放并支持滚动；修复默认高度及长攻略标题下按钮被挤掉的问题。

### English

- Add **Correct recognition** beside **New game** in the main toolbar, accessible from every tab.
- Place correction and calibration tools above the recognized list. Let the list shrink and scroll, keeping tools visible at the default height with wrapped guide titles.

### 日本語

- 主操作欄の **新しい対局** の隣に **認識修正** を追加し、どのタブからも開けるようにしました。
- 認識一覧の上に修正・校正ボタンを配置。一覧の高さを可変にしてスクロールを追加し、標準の高さや長い攻略名でもボタンを表示。

## v1.0.4 — 2026-10-12

### 中文

- 修复投资环境页面没有推荐的问题，同时记录三张待选卡，按攻略作者优选/次选、阵容关联、资源效果和触发条件给出比较。
- 未锁定攻略时仍可比较投资环境和策略；识别不足三张时明确标记临时建议，不把未识别或待选项当成已选择。
- 投资刷新和离开页面后清除旧待选项，保留手动确认的已选投资；修复环境与角色编号相同导致的名称串读。
- 投资页标题优先于效果中的“伤害”“刷新”等关键词，避免误判成战斗或商店。支持在“已识别”中纠正待选项及确认已选项。

### English

- Fix missing investment-environment advice. Keep all three choices and compare guide preferences, lineup relevance, resource effects and trigger conditions.
- Compare environments and strategies without a locked guide. Mark incomplete recognition as provisional and never treat an offered card as selected.
- Clear old choices on refresh or page exit while preserving manually confirmed selections. Resolve environment/role ID name collisions.
- Detect the investment page heading before damage/refresh words in descriptions; allow choice corrections and selected-status confirmation.

### 日本語

- 投資環境で助言が出ない問題を修正。3枚の候補を保持し、攻略の優先・次点候補、編成との関係、資源効果と発動条件を比較。
- 攻略未固定でも環境・戦略を比較。認識不足は暫定と表示し、提示されたカードを選択済みとして扱わない。
- 更新・画面移動で古い候補を消去し、手動確認した選択は保持。環境とキャラの ID が重なる場合の名称誤表示を修正。
- 効果文の「ダメージ」「更新」より投資画面の見出しを優先。「認識済み」から候補修正・選択状態確認が可能。

## v1.0.3 — 2026-10-10

### 中文

- 修复只读取热门和最新各前3页、约60篇攻略的遗漏。按官方分页读取到末尾并去重，显示真实攻略码数量、同步范围和完整状态，支持中断续传。
- 粘贴攻略码后自动联网查找、核对官方详情并锁定。完整分享标题可用于羁绊筛选，找到后无需等待全量同步。
- 单独显示查找进度、失效和版本差异提示；新局或解除锁定会取消旧查找，避免迟到的结果再次锁定。

### English

- Replace the first-three-pages limit with pagination to both public list ends, deduplication, code counts, coverage status and resumable sync.
- Look up pasted codes online, verify official details and lock immediately. Full share titles can accelerate trait-filtered lookup.
- Keep lookup status visible; show expiry/version context and cancel pending lookups on unlock or new game.

### 日本語

- 各順3ページまでの制限を修正し、公開一覧の最後まで取得、重複除去、コード件数・取得範囲・完了状態を表示。中断後は再開可能。
- 貼り付けたコードをオンライン検索し、公式詳細と照合して即座に固定。共有タイトルによる特性検索にも対応。
- 検索状態を独立表示し、期限・バージョン情報を案内。解除や新しい対局で古い検索を取消。

## v1.0.2 — 2026-10-10

### 中文

- 显式打包 Windows 窗口捕获的原生模块；发布前用打包后的程序验证实际图像捕获。
- 左上角设置新增“无边框窗口”开关，关闭助手时自动保存，下次启动恢复。
- 助手标题支持拖动，右下角支持缩放，新增最小化和关闭按钮；Esc 可恢复窗口边框。
- 切换语言、最小化恢复及折叠展开时保留无边框模式；修复调整尺寸时出现的边距偏移。
- 设置栏改为两行，保留中文、英语、日语；窗口显示版本号，缺少捕获组件时给出对应修复提示。
- 支持从游戏复制的 `##代码##->使用说明` 分享文字，提取代码后匹配已缓存攻略。

### English

- Explicitly bundle the native Windows capture module and verify real frame capture using the packaged executable.
- Add an assistant **Borderless window** setting, saved on close and restored on launch.
- Drag the header to move, use the bottom-right grip to resize, and use the minimize/close buttons. Esc restores the window frame.
- Preserve borderless mode across language changes, minimize/restore and fold/expand; correct resize margins.
- Arrange settings in two rows, retain three interface languages, display the version and explain missing capture components.
- Extract codes from the game's `##code##->instructions` share text when matching cached guides.

### 日本語

- Windows キャプチャのネイティブモジュールを明示的に同梱し、配布版で実際の画像取得を検証。
- 助手に **枠なしウィンドウ** 設定を追加。終了時に保存し、次回起動時に復元。
- 見出しのドラッグによる移動、右下のサイズ変更、最小化・終了ボタンを追加。Esc で枠を復元。
- 言語変更、最小化からの復帰、折りたたみ時も枠なし設定を維持。サイズ変更時の余白ずれを修正。
- 設定欄を二行に整理し、三言語に対応。バージョン表示とキャプチャモジュール不足時の説明を追加。
- ゲームの `##コード##->説明文` からコードを抽出し、キャッシュ済み攻略と照合。
