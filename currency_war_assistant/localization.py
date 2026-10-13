"""Shared interface and local advice translations; source game text is unchanged."""
LANGUAGE_OPTIONS=(("中文","zh"),("English","en"),("日本語","ja"))
I18N={
    "zh": {
        "language":"语言", "settings":"设置", "theme":"主题", "dark_theme":"深色", "light_theme":"浅色", "save_on_close":"设置会在关闭助手时自动保存。", "topmost_label":"始终置顶", "title":"货币战争 · 实时助手", "fold":"折叠", "expand":"展开",
        "brief":"普通 A8·30 · 等待选择游戏窗口", "status_idle":"本地识别，游戏操作由你完成。",
        "find_window":"找窗口", "start":"开始观察", "pause":"暂停", "analyze":"立即分析", "new_game":"新对局",
        "advice_tab":"现在怎么做", "guides_tab":"攻略与备选", "state_tab":"已识别", "name":"名称", "zone":"位置", "star":"星级", "source":"依据",
        "correct":"识别纠正 / 补充隐藏信息", "preview":"查看画面 / 校准区域 / 学习图标", "warning":"装备详情未打开、星级不清楚时，需要你确认。",
        "refresh":"更新攻略", "export":"导出诊断", "cache_loading":"攻略缓存载入中…", "stage":"阶段", "gold":"金币", "level":"等级", "hp":"生命", "locked":"本局攻略", "opacity":"透明度", "pending":"待确认", "unlocked":"未锁定",
        "guide_code":"本局攻略码", "read_clipboard":"读取剪贴板", "apply_lock":"应用并锁定", "clear_lock":"解除锁定",
        "initial_advice":"选择游戏窗口，点击“开始观察”。\n\n首次准备阶段：\n1. 打开商店。\n2. 在“已识别”中查看识别结果。\n3. 校准位置区域，纠正未确定的角色或装备。\n\n助手只观察游戏，推荐分数表示适配程度。",
        "waiting_guides":"等待角色和装备信息。\n已缓存的公开攻略将在观察后匹配。", "locked_label":"已锁定", "main_pick":"主推荐", "alternative":"备选 {index}", "blocked":"前提未满足", "fit":"适配 {score:.0f}/100", "author_unknown":"作者未知", "guide_code_prefix":"攻略码：", "missing":"缺少核心 / 前提：", "target_cost":"未持有目标角色 {count}名 · 单份购入至少 {cost}金币（不含刷新、升级与追星）", "copy":"复制码", "original":"原文", "unlock":"解锁", "lock":"锁定", "details":"详情",
        "guide_code_missing":"这篇攻略的攻略码未取得，请打开原文复制。", "guide_code_copied":"已复制真实攻略码。可在游戏“攻略大全 → 输入攻略码”中粘贴。", "clipboard_read":"已读取剪贴板内容，请点击“应用并锁定”。", "clipboard_empty":"剪贴板没有可读取的文字。", "paste_first":"请先粘贴攻略码。", "topmost_on":"已开启始终置顶。", "topmost_off":"已关闭始终置顶，助手会按普通窗口层级显示。",
        "detail_title":"攻略详情", "author":"作者：", "operation":"运营说明（作者原文）：\n", "early":"前期", "middle":"中期", "final":"后期", "front":"前台：", "back":"后台：", "preferred":"优选策略", "secondary":"次选策略", "environment":"推荐环境", "origin":"来源：",
        "correction_title":"识别纠正 · 只修改助手记录", "correction_note":"补充隐藏信息；出售、升星、合成后可在这里修改或移除。", "team_level":"团队等级", "round":"阶段（如1-6）", "save_numbers":"保存数值", "copies":"份数", "equipped_to":"已装备给", "add_update":"添加 / 更新", "remove_selected":"移除选中", "clear_shop":"清除手动商店", "done":"完成", "role":"角色", "equipment":"装备", "strategy":"策略", "environment_kind":"环境", "front_zone":"前台", "back_zone":"后台", "bench":"备战", "shop":"商店", "inventory":"库存", "equipped":"已装备", "selected":"已选", "unselected":"待选", "confirm":"请核对", "invalid_name":"请输入名称并从下拉列表选择具体形态。", "manual_economy":"经济数值为手动纠正；再次读取到可靠数值或进入新阶段后会更新。",
        "preview_title":"画面校准 · 框选区域或图标", "preview_note":"在画面中拖出矩形，只改变助手校准，不向游戏发送操作。商店区域仅框五个角色卡片，备战区域不要与商店重叠。", "save_region":"保存位置区域", "learn_icon":"学习图标", "close":"关闭", "preview_ready":"框选后保存区域，或学习一个已确认图标。", "save_region_status":"区域已保存。逐一校准备战、前台、后台和库存后关闭。", "learn_status":"图标已学习。后续相同画面会本地匹配。", "select_item":"请选择已确认的名称和具体形态。",
        "window_missing":"先启动游戏，再点击“找窗口”。", "choose_window":"请选择正在运行的游戏窗口。", "capture_failed":"窗口捕获未启动：{error}。可尝试无边框窗口。", "start_observe":"开始观察后才能查看画面。", "invalid_box":"请先框选有效区域。", "recognizer_loading":"识别引擎还在初始化，请稍后。", "export_done":"诊断已保存到助手数据文件夹。", "network":"规则 V{version} · 攻略 {count}篇 · {connection}\n缓存更新 {updated} · 分数不是通关概率", "online":"已联网", "offline":"使用缓存", "unknown":"未知", "new_game_done":"已清空上一局记录；区域校准和图标学习保留。", "hidden_record":"隐藏角色沿用最近观察记录；出售或升星后，请核对“已识别”。\n", "warning_pending":"待确认 {count} 项。星级、隐藏装备与已选投资不明时请补充。"
    },
    "en": {
        "language":"Language", "settings":"Settings", "theme":"Theme", "dark_theme":"Dark", "light_theme":"Light", "save_on_close":"Settings are saved automatically when the assistant closes.", "topmost_label":"Always on top", "title":"Currency War · Live Assistant", "fold":"Collapse", "expand":"Expand",
        "brief":"Normal A8·30 · Choose a game window", "status_idle":"Local recognition; you control the game.",
        "find_window":"Find window", "start":"Start observing", "pause":"Pause", "analyze":"Analyze now", "new_game":"New game",
        "advice_tab":"What to do now", "guides_tab":"Guides & alternatives", "state_tab":"Recognized", "name":"Name", "zone":"Position", "star":"Stars", "source":"Source",
        "correct":"Correct recognition / add hidden info", "preview":"View frame / calibrate / learn icon", "warning":"Confirm equipment and stars when details are not visible.",
        "refresh":"Update guides", "export":"Export diagnostics", "cache_loading":"Loading guide cache…", "stage":"Stage", "gold":"Gold", "level":"Level", "hp":"HP", "locked":"Locked guide", "opacity":"Opacity", "pending":"Pending", "unlocked":"Not locked",
        "guide_code":"Guide code for this game", "read_clipboard":"Read clipboard", "apply_lock":"Apply & lock", "clear_lock":"Unlock",
        "initial_advice":"Choose a game window and click “Start observing”.\n\nPreparation checklist:\n1. Open the shop.\n2. Review recognition in “Recognized”.\n3. Calibrate zones and correct unknown roles or equipment.\n\nThe assistant only observes; fit scores are not win probabilities.",
        "waiting_guides":"Waiting for role and equipment information.\nCached public guides will be matched after observation.", "locked_label":"LOCKED", "main_pick":"TOP PICK", "alternative":"ALT {index}", "blocked":" · prerequisite missing", "fit":"Fit {score:.0f}/100", "author_unknown":"Unknown author", "guide_code_prefix":"Guide code: ", "missing":"Missing core / prerequisite: ", "target_cost":"{count} target roles not owned · at least {cost} gold for one copy (before refresh, leveling or stars)", "copy":"Copy code", "original":"Original", "unlock":"Unlock", "lock":"Lock", "details":"Details",
        "guide_code_missing":"This guide has no code yet; open the original guide and copy it.", "guide_code_copied":"Real guide code copied. Paste it in the game's Guidebook → Enter code.", "clipboard_read":"Clipboard read. Click “Apply & lock”.", "clipboard_empty":"No readable text in the clipboard.", "paste_first":"Paste a guide code first.", "topmost_on":"Always-on-top enabled.", "topmost_off":"Always-on-top disabled; the assistant uses normal window stacking.",
        "detail_title":"Guide details", "author":"Author: ", "operation":"Operation notes (author text):\n", "early":"Early", "middle":"Mid", "final":"Final", "front":"Front: ", "back":"Back: ", "preferred":"Preferred strategies", "secondary":"Secondary strategies", "environment":"Recommended environment", "origin":"Source: ",
        "correction_title":"Recognition correction · assistant record only", "correction_note":"Add hidden information; update or remove entries after selling, starring or combining.", "team_level":"Team level", "round":"Stage (e.g. 1-6)", "save_numbers":"Save values", "copies":"Copies", "equipped_to":"Equipped to", "add_update":"Add / update", "remove_selected":"Remove selected", "clear_shop":"Clear manual shop", "done":"Done", "role":"Role", "equipment":"Equipment", "strategy":"Strategy", "environment_kind":"Environment", "front_zone":"Front", "back_zone":"Back", "bench":"Bench", "shop":"Shop", "inventory":"Inventory", "equipped":"Equipped", "selected":"Selected", "unselected":"Unselected", "confirm":"Check input", "invalid_name":"Enter a name and choose a specific form from the list.", "manual_economy":"Economy values were corrected manually; reliable recognition or a new stage will update them.",
        "preview_title":"Frame calibration · select a zone or icon", "preview_note":"Drag a rectangle over the frame. This only changes assistant calibration and never sends game input. Select five shop cards; do not overlap the bench zone.", "save_region":"Save zone", "learn_icon":"Learn icon", "close":"Close", "preview_ready":"Select a box to save a zone or learn a confirmed icon.", "save_region_status":"Zone saved. Calibrate bench, front, back and inventory before closing.", "learn_status":"Icon learned. The same image can be matched locally later.", "select_item":"Select a confirmed name and specific form.",
        "window_missing":"Start the game, then click “Find window”.", "choose_window":"Choose a running game window.", "capture_failed":"Could not start capture: {error}. Try borderless mode.", "start_observe":"Start observing before viewing a frame.", "invalid_box":"Select a valid rectangle first.", "recognizer_loading":"Recognition is still initializing; try again shortly.", "export_done":"Diagnostics saved in the assistant data folder.", "network":"Rules V{version} · {count} guides · {connection}\nCache updated {updated} · fit is not win probability", "online":"online", "offline":"cached", "unknown":"unknown", "new_game_done":"Previous game cleared; calibration and learned icons were kept.", "hidden_record":"Hidden roles use the last observation; check “Recognized” after selling or starring.\n", "warning_pending":"{count} item(s) need confirmation. Add stars, hidden equipment or selected investments when unclear."
    },
    "ja": {
        "language":"言語", "settings":"設定", "theme":"テーマ", "dark_theme":"ダーク", "light_theme":"ライト", "save_on_close":"設定は助手を閉じると自動的に保存されます。", "topmost_label":"常に最前面", "title":"通貨戦争 · リアルタイム助手", "fold":"折りたたむ", "expand":"展開",
        "brief":"通常 A8·30 · ゲーム画面を選択", "status_idle":"ローカル認識。ゲーム操作はあなたが行います。",
        "find_window":"画面を探す", "start":"観察開始", "pause":"一時停止", "analyze":"今すぐ分析", "new_game":"新しいゲーム",
        "advice_tab":"今すること", "guides_tab":"攻略と候補", "state_tab":"認識結果", "name":"名前", "zone":"位置", "star":"星", "source":"根拠",
        "correct":"認識を修正 / 非表示情報を追加", "preview":"画面表示 / 範囲調整 / アイコン学習", "warning":"装備詳細や星が見えない場合は確認してください。",
        "refresh":"攻略を更新", "export":"診断を出力", "cache_loading":"攻略キャッシュを読み込み中…", "stage":"段階", "gold":"コイン", "level":"レベル", "hp":"HP", "locked":"固定攻略", "opacity":"透明度", "pending":"要確認", "unlocked":"未固定",
        "guide_code":"このゲームの攻略コード", "read_clipboard":"クリップボード読込", "apply_lock":"適用して固定", "clear_lock":"固定解除",
        "initial_advice":"ゲーム画面を選び「観察開始」を押してください。\n\n準備段階:\n1. ショップを開く。\n2. 「認識結果」で確認する。\n3. 範囲を調整し、不明なキャラや装備を修正する。\n\n助手は観察のみ行い、適性スコアは勝率ではありません。",
        "waiting_guides":"キャラと装備の情報を待っています。\n観察後にキャッシュ済み攻略を照合します。", "locked_label":"固定中", "main_pick":"おすすめ", "alternative":"候補 {index}", "blocked":" · 前提未達", "fit":"適性 {score:.0f}/100", "author_unknown":"作者不明", "guide_code_prefix":"攻略コード：", "missing":"不足する核心 / 前提：", "target_cost":"未所持の目標キャラ {count}体 · 1体に最低 {cost}コイン（更新・育成・星上げを除く）", "copy":"コードをコピー", "original":"原文", "unlock":"解除", "lock":"固定", "details":"詳細",
        "guide_code_missing":"この攻略にはコードがありません。原文を開いてコピーしてください。", "guide_code_copied":"攻略コードをコピーしました。ゲーム内の攻略大全 → コード入力で貼り付けてください。", "clipboard_read":"クリップボードを読み込みました。「適用して固定」を押してください。", "clipboard_empty":"クリップボードに読み取れる文字がありません。", "paste_first":"攻略コードを貼り付けてください。", "topmost_on":"常に最前面を有効にしました。", "topmost_off":"常に最前面を無効にしました。通常のウィンドウ順で表示します。",
        "detail_title":"攻略詳細", "author":"作者：", "operation":"運用メモ（作者原文）：\n", "early":"序盤", "middle":"中盤", "final":"終盤", "front":"前衛：", "back":"後衛：", "preferred":"優先戦略", "secondary":"次点戦略", "environment":"おすすめ環境", "origin":"出典：",
        "correction_title":"認識修正 · 助手の記録のみ", "correction_note":"非表示情報を追加します。売却・星上げ・合成後は更新または削除してください。", "team_level":"チームレベル", "round":"段階（例 1-6）", "save_numbers":"数値を保存", "copies":"個数", "equipped_to":"装備先", "add_update":"追加 / 更新", "remove_selected":"選択を削除", "clear_shop":"手動ショップを消去", "done":"完了", "role":"キャラ", "equipment":"装備", "strategy":"戦略", "environment_kind":"環境", "front_zone":"前衛", "back_zone":"後衛", "bench":"待機", "shop":"ショップ", "inventory":"所持品", "equipped":"装備中", "selected":"選択済み", "unselected":"未選択", "confirm":"入力を確認", "invalid_name":"名前を入力し、一覧から形態を選択してください。", "manual_economy":"経済数値を手動修正しました。確実な認識または新しい段階で更新されます。",
        "preview_title":"画面調整 · 範囲またはアイコンを選択", "preview_note":"画面上で矩形をドラッグします。助手の調整だけを変更し、ゲーム操作は行いません。ショップは5枚のカードだけを囲み、待機範囲と重ねないでください。", "save_region":"範囲を保存", "learn_icon":"アイコンを学習", "close":"閉じる", "preview_ready":"範囲を選択して保存するか、確認済みアイコンを学習してください。", "save_region_status":"範囲を保存しました。待機・前衛・後衛・所持品を調整してから閉じてください。", "learn_status":"アイコンを学習しました。同じ画面を後でローカル照合できます。", "select_item":"確認済みの名前と形態を選択してください。",
        "window_missing":"ゲームを起動してから「画面を探す」を押してください。", "choose_window":"実行中のゲーム画面を選択してください。", "capture_failed":"画面取得を開始できません：{error}。ボーダーレス表示を試してください。", "start_observe":"観察開始後に画面を表示できます。", "invalid_box":"有効な範囲を選択してください。", "recognizer_loading":"認識エンジンを初期化中です。少し待ってください。", "export_done":"診断を助手データフォルダに保存しました。", "network":"ルール V{version} · 攻略 {count}件 · {connection}\nキャッシュ更新 {updated} · 適性は勝率ではありません", "online":"接続中", "offline":"キャッシュ使用", "unknown":"不明", "new_game_done":"前のゲームを消去しました。調整と学習済みアイコンは保持しています。", "hidden_record":"非表示キャラは最後の認識を使用します。売却や星上げ後は「認識結果」を確認してください。\n", "warning_pending":"{count}件が要確認です。星、非表示装備、選択済み投資を補足してください。"
    },
}

I18N["zh"].update({
    "borderless":"无边框窗口", "minimize":"最小化", "exit":"关闭助手",
    "borderless_on":"已开启助手无边框窗口：拖动标题移动，拖动右下角缩放；Esc 恢复边框。",
    "borderless_off":"已恢复助手窗口边框。",
    "borderless_failed":"助手窗口模式切换失败：{error}",
    "capture_dependency_missing":"窗口捕获组件缺失或无法加载。请完整解压最新版本，并保留 _internal 文件夹；切换窗口模式不能修复组件缺失。详细原因：{error}",
    "capture_failed":"窗口捕获未启动：{error}。游戏黑屏时可尝试将游戏切换为无边框显示。",
})
I18N["en"].update({
    "borderless":"Borderless window", "minimize":"Minimize", "exit":"Close assistant",
    "borderless_on":"Assistant borderless mode enabled. Drag the header to move; drag the bottom-right corner to resize. Esc restores the frame.",
    "borderless_off":"Assistant window frame restored.",
    "borderless_failed":"Could not change the assistant window mode: {error}",
    "capture_dependency_missing":"Capture component is missing or cannot load. Extract the complete latest release and keep _internal. Window mode cannot fix a missing component. Details: {error}",
    "capture_failed":"Could not start capture: {error}. If the game image is black, try the game's borderless display mode.",
})
I18N["ja"].update({
    "borderless":"枠なしウィンドウ", "minimize":"最小化", "exit":"助手を閉じる",
    "borderless_on":"助手の枠なし表示を有効にしました。見出しで移動、右下でサイズ変更。Esc で枠を戻せます。",
    "borderless_off":"助手のウィンドウ枠を戻しました。",
    "borderless_failed":"助手のウィンドウ表示を切り替えられません：{error}",
    "capture_dependency_missing":"画面取得コンポーネントがないか読み込めません。最新版を全て展開し、_internal を残してください。表示モードの変更では解決できません。詳細：{error}",
    "capture_failed":"画面取得を開始できません：{error}。ゲーム画面が黒い場合はゲームのボーダーレス表示を試してください。",
})


I18N["zh"].update({
    "lookup_searching":"正在联网查找这条攻略码 · 已检查 {pages} 页；找到后自动锁定，无需等待全部同步。",
    "lookup_locked":"已锁定：{title} · 作者版本 V{version} / 当前 V{current}；后续按此攻略推荐。",
    "lookup_not_found":"本次公开推荐列表中没有找到该攻略码。可粘贴含标题的完整分享文字重试；未公开或已删除攻略无法保证取得。",
    "lookup_invalid":"已找到 {title}，但官方标记失效或当前角色配置不兼容，未锁定。",
    "lookup_error":"攻略查找中断：{error}。保留原锁定；请检查网络后重试。",
    "coverage_running":"正在同步公开推荐列表 · {pages} 页（可边同步边使用）",
    "coverage_complete":"公开推荐列表本次已读完 · {pages} 页（热门＋最新，去重）",
    "coverage_partial":"缓存不完整 · {pages} 页；点击“更新攻略”继续同步",
    "coverage_interrupted":"同步中断 · {pages} 页；点击“更新攻略”续传",
    "network":"规则 V{version} · 缓存 {count}篇 / 有攻略码 {codes}篇 · {connection}\n{coverage}\n缓存更新 {updated} · 不保证包含未公开攻略 · 分数不是通关概率",
})
I18N["en"].update({
    "lookup_searching":"Looking up this code online · {pages} pages checked. It locks as soon as found; full sync can continue.",
    "lookup_locked":"Locked: {title} · guide V{version} / current V{current}. Advice follows this guide.",
    "lookup_not_found":"Code not found in this public recommendation snapshot. Try the full share text with its title. Private or deleted guides may be unavailable.",
    "lookup_invalid":"Found {title}, but it is expired or incompatible with the current catalog. It was not locked.",
    "lookup_error":"Lookup interrupted: {error}. Previous lock kept. Check the connection and retry.",
    "coverage_running":"Syncing public recommendations · {pages} pages (usable during sync)",
    "coverage_complete":"Public recommendation snapshot read to the end · {pages} pages (Hot + Latest, deduplicated)",
    "coverage_partial":"Incomplete cache · {pages} pages. Update guides to continue.",
    "coverage_interrupted":"Sync interrupted · {pages} pages. Update guides to resume.",
    "network":"Rules V{version} · {count} cached / {codes} with codes · {connection}\n{coverage}\nUpdated {updated} · private guides may be unavailable · fit is not win probability",
})
I18N["ja"].update({
    "lookup_searching":"コードをオンライン検索中 · {pages}ページ確認済み。見つかり次第固定します。全件同期は継続できます。",
    "lookup_locked":"固定中：{title} · 攻略 V{version} / 現行 V{current}。この攻略に沿って提案します。",
    "lookup_not_found":"今回の公開おすすめ一覧にコードがありません。タイトル付き共有文でも再試行できます。非公開・削除済み攻略の取得は保証できません。",
    "lookup_invalid":"{title} が見つかりましたが、期限切れまたは現行設定と互換性がないため固定しません。",
    "lookup_error":"検索中断：{error}。以前の固定を保持します。接続を確認して再試行してください。",
    "coverage_running":"公開おすすめを同期中 · {pages}ページ（同期中も利用可能）",
    "coverage_complete":"今回の公開おすすめ一覧を最後まで取得 · {pages}ページ（人気＋新着、重複除去）",
    "coverage_partial":"キャッシュは未完了 · {pages}ページ。「攻略更新」で続きを取得",
    "coverage_interrupted":"同期中断 · {pages}ページ。「攻略更新」で再開",
    "network":"ルール V{version} · キャッシュ {count}件 / コードあり {codes}件 · {connection}\n{coverage}\n更新 {updated} · 非公開攻略の網羅は保証できません · 適性は勝率ではありません",
})


def translate(language,key,**values):
    template=I18N.get(language,I18N['zh']).get(key,I18N['zh'].get(key,key))
    return template.format(**values) if values else template

ENUM_KEYS={'角色':'role','装备':'equipment','策略':'strategy','环境':'environment_kind',
           '前台':'front_zone','后台':'back_zone','备战':'bench','商店':'shop','库存':'inventory',
           '已装备':'equipped','已选':'selected','待选':'unselected','待确认':'pending',
           '手动':'manual_source','画面':'frame_source','文字':'ocr_source','官方图标':'official_icon_source',
           '已确认图标':'learned_icon_source','库存图标':'inventory_icon_source',
           '搜牌':'search_operation','升级':'level_operation'}


def enum_label(language,value):
    return translate(language,ENUM_KEYS[value]) if value in ENUM_KEYS else value


# Official names, skills, equipment effects and authors' prose stay in source
# Chinese. Only assistant-authored labels and explanations are translated.
ADVICE={
 'manual_source':('手动','Manual','手動'),
 'frame_source':('画面','Frame','画面'),
 'ocr_source':('文字','OCR text','OCR 文字'),
 'official_icon_source':('官方图标','Official icon','公式アイコン'),
 'learned_icon_source':('已确认图标','Learned icon','学習済みアイコン'),
 'inventory_icon_source':('库存图标','Inventory icon','所持品アイコン'),
 'search_operation':('搜牌','search for copies','カードを探す'),
 'level_operation':('升级','level up','レベルを上げる'),
 'client_only':('当前仅支持简体中文游戏客户端；界面语言可独立切换。','Only the Simplified Chinese game client is currently recognized; interface language is independent.','現在、認識は簡体字中国語のゲームクライアントのみ対応。助手の表示言語は別に選べます。'),
 'client_title_warning':('检测到英文或繁体中文游戏标题。当前识别只支持简体中文客户端，请切换游戏语言后观察。','An English or Traditional Chinese game title was detected. Recognition supports only the Simplified Chinese client; switch the game language before observing.','英語または繁体字のゲームタイトルを検出しました。認識は簡体字クライアントのみ対応するため、ゲーム言語を切り替えてください。'),
 'current_heading':('当前','Current','現在'),
 'confirm_heading':('先确认','Confirm first','先に確認'),
 'prerequisite_heading':('阵容前提','Lineup prerequisites','編成の前提'),
 'buy_heading':('买人','Buy','購入'),
 'combine_heading':('合成','Combine','合成'),
 'economy_heading':('经济','Economy','経済'),
 'next_heading':('下一步','Next','次の手順'),
 'locked_invalid_heading':('锁定失效','Locked guide invalid','固定攻略が無効'),
 'locked_invalid_body':('原攻略已失效或角色不兼容，当前显示有效备选。请重新锁定。','The locked guide is expired or has incompatible roles. Valid alternatives are shown; choose a new guide.','固定攻略が失効したか、キャラが非対応です。有効な候補から再度固定してください。'),
 'battle_advice':('战斗进行中，保留阵容记录；准备阶段再更新买人和经济建议。','Battle is underway. Keep the lineup record; buying and economy advice updates during preparation.','戦闘中は編成記録を保持します。購入と経済の提案は準備段階で更新します。'),
 'open_shop_advice':('请停留在货币战争准备界面并打开商店；投资页面中的选项需确认是否已选。','Stay on the Currency War preparation screen and open the shop. Confirm whether investment options have been selected.','通貨戦争の準備画面でショップを開いてください。投資候補は選択済みか確認が必要です。'),
 'confirm_owned_advice':('确认已持有角色与库存装备后生成建议。可以在“识别纠正”中补充未显示的角色。','Confirm owned roles and inventory equipment to generate advice. Add hidden roles using Correct recognition.','所持キャラと装備を確認すると提案を生成します。見えないキャラは「認識修正」で追加してください。'),
 'missing_context':('{name}（{kind}需确认已选）','{name} ({kind}: confirm selected)','{name}（{kind}：選択済みを確認）'),
 'prerequisites_missing':('必需前提未满足：{conditions}','Required prerequisites missing: {conditions}','必須前提が未達：{conditions}'),
 'owned_unknown':('已持有角色还未确认，当前仅供候选参考','Owned roles are unconfirmed; this is a candidate only','所持キャラが未確認のため、候補としてのみ参照してください'),
 'transition_high':('现有角色与目标阵容没有直接衔接，转型成本高','Current roles do not connect directly to this lineup; transition cost is high','所持キャラと目標編成のつながりが薄く、移行コストが高いです'),
 'stage_owned':('本阶段已有 {names}','Already owned for this stage: {names}','この段階の所持キャラ：{names}'),
 'gear_compatible':('已有装备或材料可衔接 {count:g} 项目标装备','Owned equipment/materials connect to {count:g} target equipment items','所持装備・素材で目標装備 {count:g} 件に対応できます'),
 'shop_strengthening':('当前商店有补强角色：{names}','The shop has lineup improvements: {names}','ショップの補強候補：{names}'),
 'gear_unknown':('装备库存尚未确认，装备适配分暂不计入','Equipment inventory is unconfirmed; equipment fit is not counted','装備在庫が未確認のため、装備適性は加算しません'),
 'old_version':('作者版本 {version}；已核对角色可用性，正文中的旧倍率需按现行规则确认','Author version {version}. Role availability was checked; old multipliers in the guide need current-rule verification','作者版 {version}。キャラの対応は確認済みですが、旧倍率は現行ルールで確認してください'),
 'candidate_confirm':('可用的攻略候选；确认角色、装备和经济后再决定','A valid guide candidate; confirm roles, equipment and economy before deciding','有効な攻略候補です。キャラ・装備・経済を確認して判断してください'),
 'blocked_advice':('{condition}；暂不为该攻略花钱搜核心，查看备选。','{condition}. Do not spend on this guide’s core yet; review alternatives.','{condition}。この攻略の核心探しへの支出を保留し、候補を確認してください。'),
 'buy_pair_reason':('可补齐升星份数','completes copies for starring','星上げに必要な枚数を補えます'),
 'buy_core_reason':('是攻略核心','is a guide core','攻略の核心です'),
 'buy_stage_reason':('能补本阶段阵容','improves this stage’s lineup','この段階の編成を補強します'),
 'buy_unknown_gold':('优先关注 {name}（{price}费），{reason}；金币待确认，先核对是否买得起。','Prioritize {name} (cost {price}); {reason}. Gold is unconfirmed; check affordability first.','{name}（{price}コスト）を優先：{reason}。コイン未確認のため、購入可能か確認してください。'),
 'buy_affordable':('优先买 {name}（{price}金币），{reason}。买后余 {remaining}；其他目标按现有格位购买。','Buy {name} first ({price} gold); {reason}. {remaining} gold remains; buy other targets as space permits.','{name}（{price}コイン）を優先購入：{reason}。残り {remaining}、他の候補は空き枠に合わせて購入します。'),
 'buy_unaffordable':('目标 {name} 需要 {price}金币，目前不足；可以手动锁店等待收入。','{name} costs {price} gold, more than currently available. You may lock the shop manually and wait for income.','{name} は {price} コイン必要ですが不足しています。手動でショップを固定して収入を待てます。'),
 'shop_no_targets':('当前确认的商店没有明显的阵容补强；不为无关角色消耗金币。','No clear lineup improvement in the confirmed shop; save gold on unrelated roles.','確認済みショップに明確な補強はありません。無関係なキャラへの支出を控えます。'),
 'shop_incomplete':('商店未读取完整，请打开商店或纠正五个商店格位。','Shop recognition is incomplete. Open the shop or correct its five slots.','ショップの認識が不完全です。開くか、5 枠を修正してください。'),
 'role_effect':('{zone}作用：{effect}','{zone} role — source effect: {effect}','{zone}の役割・原文効果：{effect}'),
 'gear_effect':(' 当前效果：{effect}',' Current source effect: {effect}',' 現在の原文効果：{effect}'),
 'equip_target':('可将 {gear} 给 {role}：这是作者的优选装备。核对该角色空余装备格。','Give {gear} to {role}: the author’s preferred equipment. Check free equipment slots.','{gear} を {role} に渡せます。作者の優先装備です。空き装備枠を確認してください。'),
 'combine_target':('{materials} → {gear}，优先考虑给 {role}。配方来自当前官方配置。','{materials} → {gear}; prioritize {role}. Recipe comes from current official configuration.','{materials} → {gear}。{role} を優先します。配合は現在の公式設定に基づきます。'),
 'gear_incomplete':('尚未确认可完成的目标装备；打开装备详情或补充库存，再判断给谁和是否合成。','No completed target equipment is confirmed. Open details or add inventory to assess recipients and recipes.','完成できる目標装備が未確認です。詳細や在庫を追加して、装備先と合成を判断します。'),
 'economy_blocked':('攻略必需前提缺失，保留金币；先选适配备选或补充确认信息，再决定升级和刷新。','Required prerequisites are missing. Save gold; choose a fitting alternative or confirm information before leveling or refreshing.','必須前提が不足しています。コインを保持し、候補や情報を確認してからレベル上げ・更新を判断します。'),
 'economy_unknown':('金币或等级待确认。该攻略运营方向：{target}级{operation}；暂不建议具体花费。','Gold or level is unconfirmed. Guide direction: level {target}, {operation}; no specific spending advice yet.','コインまたはレベルが未確認です。運用方向はレベル {target} で {operation}。具体的な支出は保留します。'),
 'economy_low_hp':('生命已低于25，先补当前阵容质量，优先购买可升星或立刻上场的角色；不要为了长期利息忽略眼前战斗。','HP is at most 25. Improve current strength with star completions or immediately usable roles; immediate battle matters more than long-term interest.','HP が 25 以下です。星上げや即戦力で編成を補強し、長期利息より目前の戦闘を優先します。'),
 'economy_level':('目标 {target}级{operation}。先存钱并升级；仅买阵容补强，避免低等级反复花{refresh}金币刷新搜高费核心。','Target level {target}, {operation}. Save and level; buy lineup improvements only. Avoid repeatedly spending {refresh} gold on refreshes at low levels for expensive cores.','目標はレベル {target} で {operation}。貯金と育成を進め、補強のみ購入します。低レベルで高コスト核心を探す {refresh} コインの更新連打は避けます。'),
 'economy_search':('已到搜牌等级；正常经济下先保留{reserve}金币，以超出部分搜核心。当前保留{reserve}后可用 {budget}金币。投资有特殊利息规则时需按其效果调整。','Search level reached. Keep {reserve} gold under ordinary economy rules and search with the surplus: {budget} available. Adjust for investment-specific interest rules.','探索レベルに到達しました。通常は {reserve} コインを保持し、余剰の {budget} を核心探しに使用します。投資の特別な利息ルールで調整してください。'),
 'economy_reached':('已达到{target}级。先补核心和关键羁绊；正常经济下 {gold}金币约产生 {interest}利息，刷新每次花{refresh}金币。特殊投资规则会改变收益。','Level {target} reached. Add core roles and key traits. Under ordinary rules, {gold} gold gives about {interest} interest; each refresh costs {refresh}. Investments may change returns.','レベル {target} 到達。核心と重要な特性を補強します。通常、{gold} コインで利息約 {interest}、更新は {refresh} コインです。投資で収益が変わります。'),
 'general_estimate':('按通用规则估算：{body}','General-rule estimate: {body}','一般ルールによる概算：{body}'),
 'next_targets':('补强目标：{names}','Strengthening targets: {names}','補強目標：{names}'),
 'investment_environment':('投资环境','Investment environment','投資環境'),
 'investment_strategy':('投资策略','Investment strategy','投資戦略'),
 'investment_no_cards':('已进入投资选择，但卡片标题尚未可靠识别。保持三张卡可见；在“已识别”中补充或纠正“待选”环境/策略，再点击立即分析。无需返回商店。','Investment selection detected but card titles are not reliable. Keep all three visible; add or correct unselected options in Recognized, then Analyze now. No need to return to the shop.','投資選択中ですが、カード名を確実に認識できていません。3 枚を表示し、認識結果で未選択の候補を追加・修正して分析してください。ショップに戻る必要はありません。'),
 'investment_partial':('只确认了 {count}/3 个选项；以下为已识别项的临时比较，请补齐后再确认。\n','Only {count}/3 options confirmed; comparison is provisional. Add missing options before choosing.\n','{count}/3 件のみ確認済みです。比較は暫定です。不足する候補を補ってから選択してください。\n'),
 'investment_tentative':('暂优先','Provisional preference','暫定優先'),
 'investment_overview':('{header}：{name}。{reasons}。','{header}: {name}. {reasons}.','{header}：{name}。{reasons}。'),
 'investment_no_leader':('当前证据不足以选出唯一首选；按下方效果和条件比较。','Evidence does not identify one best choice; compare the effects and conditions below.','単独の第一候補を選ぶ根拠が不足しています。以下の効果と条件で比較してください。'),
 'investment_generic':(' 尚未锁定攻略、角色未确认，当前按通用资源与触发条件比较。',' No guide is locked and roles are unconfirmed; comparison uses general resources and trigger conditions.',' 攻略未固定・キャラ未確認のため、一般的な資源と発動条件で比較します。'),
 'investment_position':('第{slot}张（从左到右）','Card {slot} (left to right)','左から {slot} 枚目'),
 'investment_position_unknown':('位置待确认','Position unconfirmed','位置は要確認'),
 'investment_body':('{position}\n当前官方效果：{effect}\n适配：{reasons}。','{position}\nCurrent official effect (source text): {effect}\nFit: {reasons}.','{position}\n現在の公式効果（原文）：{effect}\n適性：{reasons}。'),
 'investment_limits':('\n条件与限制：{limits}。','\nConditions and limits: {limits}.','\n条件と制限：{limits}。'),
 'investment_check_effect':('需核对完整效果','Check the complete effect','効果全文の確認が必要'),
 'investment_after_heading':('选后确认','Confirm after selection','選択後に確認'),
 'investment_after':('三张卡都按待选记录。确认选择后，可在“已识别”中将实际选中的环境或策略改为“已选”；这会影响后续攻略、装备和经济建议。','All three cards remain unselected in the record. After choosing, mark the actual environment/strategy as Selected in Recognized; this affects later guide, equipment and economy advice.','3 枚とも未選択として記録します。選んだ環境・戦略を認識結果で選択済みに変更してください。その後の攻略・装備・経済の提案に反映します。'),
 'investment_author_preferred':('{guide}作者优选','{guide}: author’s preferred choice','{guide}：作者の優先候補'),
 'investment_author_secondary':('{guide}作者次选','{guide}: author’s secondary choice','{guide}：作者の次点候補'),
 'investment_locked':('锁定攻略','Locked guide','固定攻略'),
 'investment_candidate':('当前候选攻略','Current guide candidate','現在の攻略候補'),
 'investment_required':('可满足攻略明确要求的投资前提；选择后需确认已选','Can meet the guide’s explicit investment prerequisite; confirm selected after choosing','攻略の明示的な投資前提を満たせます。選択後に選択済みを確認してください'),
 'investment_roles':('效果直接涉及目标角色：{names}','Effect directly mentions target roles: {names}','効果が目標キャラに直接関連：{names}'),
 'investment_roles_limit':('涉及角色不代表直接赠送角色，触发条件以效果为准','Mentioning a role does not mean receiving it; use the actual trigger conditions','キャラへの言及は配布を意味しません。発動条件は効果に従います'),
 'investment_bonds':('效果涉及目标羁绊：{names}','Effect relates to target traits: {names}','目標特性に関連する効果：{names}'),
 'investment_money':('提供经济资源','Provides economy resources','経済資源を提供'),
 'investment_equipment':('提供可分配的装备资源','Provides assignable equipment resources','割り当て可能な装備資源を提供'),
 'investment_delayed':('奖励到对应位面才发放，不能解决当前回合的装备缺口','Reward arrives in its stated plane; it does not fill this round’s equipment gap','報酬は該当ステージで受け取るため、今の装備不足は解決しません'),
 'investment_extra':('增加投资选择机会；具体收益取决于后续选项','Adds investment choices; benefit depends on future options','投資選択の機会を増やします。利益は後の候補次第です'),
 'investment_emblem':('星徽需要与阵容羁绊衔接；当前没有确认它能补到目标羁绊','An emblem must connect to the lineup; no confirmed match to target traits','エンブレムは編成の特性との接続が必要です。目標特性を補えるか未確認です'),
 'investment_conditional':('有触发、次数或成本条件，不能把奖励当作已经获得','Has trigger, count or cost conditions; reward is not already owned','発動・回数・コスト条件があるため、報酬を取得済みとして扱えません'),
 'investment_encounter':('会改变战斗节点；需结合遭遇内容和阵容强度，当前不按资源收益优先','Changes battle nodes; assess encounter content and lineup strength, without treating it as a priority resource gain','戦闘ノードを変更します。遭遇内容と編成の強さで判断し、資源利益としては優先しません'),
 'investment_unmatched':('当前效果未能与已确认阵容或通用资源规则建立适配关系','No match found to confirmed lineup or general resource rules','確認済み編成・一般的な資源ルールとの適性を確認できません'),
 'investment_unknown':('官方效果缺失，暂不能可靠比较','Official effect missing; cannot compare reliably','公式効果が不足しているため、確実な比較ができません'),
 'investment_other_missing':('该攻略仍有未满足前提，选到此项不代表其它前提已经满足','Other guide prerequisites remain missing; choosing this does not satisfy them','攻略には未達の前提が残っています。この候補の選択で他の前提まで満たすわけではありません'),
 'stars_value':('{count}星','{count} stars','星 {count}'),
}
for key,values in ADVICE.items():
    for language,value in zip(('zh','en','ja'),values):I18N[language][key]=value

