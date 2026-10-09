from __future__ import annotations

from pathlib import Path
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser

from PIL import Image,ImageTk

from .api import guide_url
from .capture import find_game_windows
from .controller import Controller,normalize_share_code
from .models import Seen,normalize
from .paths import data_dir,read_json,write_json
from .strategy import clean,target_level,stage_roles
from .vision import DEFAULT_REGIONS

BG="#17133a"; PANEL="#211c4f"; INK="#f5f1ff"; MUTED="#b9b4dc"; ACCENT="#61e4ff"; GOLD="#ffd36e"; BUTTON="#302766"; BORDER="#594b9d"; SELECTED="#493d86"; METRIC="#1d1944"
THEMES={
    "dark":{"BG":"#17133a","PANEL":"#211c4f","INK":"#f5f1ff","MUTED":"#b9b4dc","ACCENT":"#61e4ff","GOLD":"#ffd36e","BUTTON":"#302766","BORDER":"#594b9d","SELECTED":"#493d86","METRIC":"#1d1944"},
    "light":{"BG":"#e9e6ff","PANEL":"#faf8ff","INK":"#241d4f","MUTED":"#5e5a85","ACCENT":"#326fc2","GOLD":"#a66a00","BUTTON":"#d6d1f4","BORDER":"#a69bdf","SELECTED":"#bfc9f5","METRIC":"#ddd9f8"},
}
THEME_OPTIONS=(("深色","dark"),("浅色","light"))

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


class Assistant:
    def __init__(self,root,data=None):
        self.root=root
        self.data=data or data_dir()
        self.settings=read_json(self.data / "settings.json",{}) or {}
        legacy_language=read_json(self.data / "language.json",{}) or {}
        self.language=self.settings.get("language",legacy_language.get("language","zh"))
        if self.language not in I18N:self.language="zh"
        self.theme=self.settings.get("theme","dark") if self.settings.get("theme","dark") in THEMES else "dark"
        self.language_var=tk.StringVar(value=next(label for label,code in LANGUAGE_OPTIONS if code==self.language))
        self.theme_var=tk.StringVar(value=self.theme_label(self.theme))
        self.opacity=tk.DoubleVar(value=max(.55,min(1.0,float(self.settings.get("opacity",.96)))))
        self.topmost=tk.BooleanVar(value=bool(self.settings.get("topmost",True)))
        self._apply_theme(self.theme)
        self.controller=Controller(self.data)
        self.root.title(self.t("title"))
        sw,sh=self.root.winfo_screenwidth(),self.root.winfo_screenheight()
        width,height=min(980,sw-40),min(650,sh-90)
        self.root.geometry(f"{width}x{height}+{max(0,sw-width-60)}+{max(0,min(140,sh-height-50))}")
        self.root.minsize(760,480)
        self.root.configure(bg=BG)
        self.root.attributes("-topmost",bool(self.topmost.get()))
        self.root.attributes("-alpha",float(self.opacity.get()))
        self.root.protocol("WM_DELETE_WINDOW",self.close)
        self.root.option_add("*Font",("Microsoft YaHei UI",10))
        self.collapsed=False
        self._geometry=""
        self._render_signature=None
        self._preview_windows=[]
        self.settings_open=False
        self._hotkey_stop=False
        self.guide_code=tk.StringVar()
        self.locked_summary=tk.StringVar(value=self.t("unlocked"))
        self.metric_vars={}
        self._build_style()
        self._build()
        # The assistant is intentionally capturable by Windows screenshots and recordings.
        self.root.after(150,self.poll)
        self.root.after(300,self.controller.initialize)
        self.root.after(400,self.refresh_windows)

    def _apply_theme(self,theme):
        global BG,PANEL,INK,MUTED,ACCENT,GOLD,BUTTON,BORDER,SELECTED,METRIC
        palette=THEMES.get(theme,THEMES["dark"])
        BG,PANEL,INK,MUTED,ACCENT,GOLD,BUTTON,BORDER,SELECTED,METRIC=(palette[k] for k in ("BG","PANEL","INK","MUTED","ACCENT","GOLD","BUTTON","BORDER","SELECTED","METRIC"))

    def save_settings(self):
        write_json(self.data / "settings.json",{"language":self.language,"theme":self.theme,"opacity":round(float(self.opacity.get()),2),"topmost":bool(self.topmost.get())})

    def theme_label(self,code):
        return self.t("dark_theme" if code=="dark" else "light_theme")

    def set_theme(self,event=None):
        label=self.theme_var.get()
        self.theme="dark" if label==self.theme_label("dark") else "light"
        self._apply_theme(self.theme)
        self._rebuild_ui()

    def t(self,key,**values):
        text=I18N.get(self.language,I18N["zh"]).get(key,I18N["zh"].get(key,key))
        return text.format(**values) if values else text

    def set_language(self,event=None):
        label=self.language_var.get()
        self.language=next((code for name,code in LANGUAGE_OPTIONS if name==label),"zh")
        self._rebuild_ui()

    def _rebuild_ui(self):
        for child in list(self.root.winfo_children()):
            child.destroy()
        self._render_signature=None
        self._preview_windows=[]
        self.metric_vars={}
        self.settings_open=False
        self.language_var.set(next(label for label,code in LANGUAGE_OPTIONS if code==self.language))
        self.theme_var.set(self.theme_label(self.theme))
        self.root.title(self.t("title"))
        self._build_style()
        self._build()
        self.refresh_windows()
        self.controller.recalculate()

    def open_settings(self):
        if not hasattr(self,"settings_panel"):return
        if self.settings_open:
            self.settings_panel.pack_forget()
            self.settings_open=False
            self.settings_button.configure(text=self.t("settings"))
        else:
            self.settings_panel.pack(fill="x",before=self.header,padx=16,pady=(8,0))
            self.settings_open=True
            self.settings_button.configure(text=self.t("close"))

    def _build_style(self):
        style=ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame",background=BG)
        style.configure("TLabel",background=BG,foreground=INK)
        style.configure("TButton",background=BUTTON,foreground=INK,borderwidth=0,padding=(9,6))
        style.map("TButton",background=[("active",SELECTED)])
        style.configure("TNotebook",background=BG,borderwidth=0)
        style.configure("TNotebook.Tab",background=PANEL,foreground=MUTED,padding=(14,8))
        style.map("TNotebook.Tab",background=[("selected",SELECTED)],foreground=[("selected",INK)])
        style.configure("Treeview",background=PANEL,fieldbackground=PANEL,foreground=INK,rowheight=26)
        style.configure("Treeview.Heading",background=BUTTON,foreground=INK)
        style.map("Treeview",background=[("selected",SELECTED)])
        style.configure("TEntry",fieldbackground=PANEL,foreground=INK,insertcolor=INK)
        style.configure("TCombobox",fieldbackground=PANEL,foreground=INK,arrowcolor=INK)

    def _build_settings_panel(self):
        self.settings_panel=tk.Frame(self.root,bg=METRIC,highlightthickness=1,highlightbackground=BORDER)
        tk.Label(self.settings_panel,text=self.t("settings"),bg=METRIC,fg=ACCENT,font=("Microsoft YaHei UI",11,"bold")).pack(side="left",padx=(10,12),pady=8)
        tk.Checkbutton(self.settings_panel,text=self.t("topmost_label"),variable=self.topmost,command=self.set_topmost,bg=METRIC,fg=INK,activebackground=METRIC,activeforeground=INK,selectcolor=BUTTON,highlightthickness=0).pack(side="left",padx=(0,12))
        tk.Label(self.settings_panel,text=self.t("opacity"),bg=METRIC,fg=MUTED).pack(side="left")
        self.settings_opacity_label=tk.Label(self.settings_panel,text=f"{int(self.opacity.get()*100)}%",bg=METRIC,fg=INK,width=5)
        def update_opacity(value):
            self.set_opacity(value);self.settings_opacity_label.configure(text=f"{int(self.opacity.get()*100)}%")
        tk.Scale(self.settings_panel,from_=0.55,to=1.0,variable=self.opacity,orient="horizontal",length=135,showvalue=False,resolution=.01,bg=METRIC,fg=INK,highlightthickness=0,troughcolor=BUTTON,command=update_opacity).pack(side="left",padx=(5,10))
        tk.Label(self.settings_panel,text=self.t("language"),bg=METRIC,fg=MUTED).pack(side="left")
        language_box=ttk.Combobox(self.settings_panel,textvariable=self.language_var,values=[name for name,code in LANGUAGE_OPTIONS],state="readonly",width=9)
        language_box.pack(side="left",padx=(4,10));language_box.bind("<<ComboboxSelected>>",self.set_language)
        tk.Label(self.settings_panel,text=self.t("theme"),bg=METRIC,fg=MUTED).pack(side="left")
        theme_box=ttk.Combobox(self.settings_panel,textvariable=self.theme_var,values=[self.theme_label("dark"),self.theme_label("light")],state="readonly",width=8)
        theme_box.pack(side="left",padx=(4,10));theme_box.bind("<<ComboboxSelected>>",self.set_theme)
        tk.Label(self.settings_panel,text=self.t("save_on_close"),bg=METRIC,fg=MUTED,font=("Microsoft YaHei UI",8)).pack(side="left",padx=(0,8))

    def _build(self):
        self._build_settings_panel()
        self.header=tk.Frame(self.root,bg=BG)
        self.header.pack(fill="x",padx=16,pady=(12,5))
        tk.Label(self.header,text=self.t("title"),bg=BG,fg=ACCENT,font=("Microsoft YaHei UI",13,"bold")).pack(side="left")
        self.settings_button=ttk.Button(self.header,text=self.t("settings"),command=self.open_settings,width=8)
        self.settings_button.pack(side="left",padx=(12,0))
        self.fold_button=ttk.Button(self.header,text=self.t("fold"),command=self.toggle,width=7)
        self.fold_button.pack(side="right")
        self.brief=tk.StringVar(value=self.t("brief"))
        tk.Label(self.root,textvariable=self.brief,bg=BG,fg=INK,anchor="w",wraplength=900,font=("Microsoft YaHei UI",11,"bold")).pack(fill="x",padx=16)
        self.status=tk.StringVar(value=self.t("status_idle"))
        tk.Label(self.root,textvariable=self.status,bg=BG,fg=MUTED,anchor="w",wraplength=900).pack(fill="x",padx=16,pady=(3,7))
        self._build_metrics()
        self.body=ttk.Frame(self.root)
        self.body.pack(fill="both",expand=True,padx=8)
        target=ttk.Frame(self.body);target.pack(fill="x",padx=8)
        self.window_var=tk.StringVar()
        self.window_box=ttk.Combobox(target,textvariable=self.window_var,state="readonly",width=50)
        self.window_box.pack(side="left",fill="x",expand=True)
        ttk.Button(target,text=self.t("find_window"),command=self.refresh_windows).pack(side="right",padx=(6,0))
        controls=ttk.Frame(self.body);controls.pack(fill="x",padx=8,pady=7)
        for label,command in [(self.t("start"),self.start),(self.t("pause"),self.controller.pause),(self.t("analyze"),self.controller.immediate),(self.t("new_game"),self.new_game)]:
            ttk.Button(controls,text=label,command=command).pack(side="left",padx=(0,5))
        self._build_guide_code_bar()
        self.notebook=ttk.Notebook(self.body)
        self.notebook.pack(fill="both",expand=True,padx=5)
        self.advice_tab=ttk.Frame(self.notebook);self.guide_tab=ttk.Frame(self.notebook);self.state_tab=ttk.Frame(self.notebook)
        self.notebook.add(self.advice_tab,text=self.t("advice_tab"))
        self.notebook.add(self.guide_tab,text=self.t("guides_tab"))
        self.notebook.add(self.state_tab,text=self.t("state_tab"))
        self.advice_text=self.text_panel(self.advice_tab)
        self.guide_canvas=tk.Canvas(self.guide_tab,bg=BG,highlightthickness=0,height=1,width=1)
        self.guide_scroll=ttk.Scrollbar(self.guide_tab,orient="vertical",command=self.guide_canvas.yview)
        self.guide_canvas.configure(yscrollcommand=self.guide_scroll.set)
        self.guide_scroll.pack(side="right",fill="y");self.guide_canvas.pack(side="left",fill="both",expand=True)
        self.cards=tk.Frame(self.guide_canvas,bg=BG)
        self.cards_id=self.guide_canvas.create_window((0,0),window=self.cards,anchor="nw")
        self.cards.bind("<Configure>",lambda e:self.guide_canvas.configure(scrollregion=self.guide_canvas.bbox("all")))
        self.guide_canvas.bind("<Configure>",lambda e:self.guide_canvas.itemconfigure(self.cards_id,width=e.width))
        self.guide_canvas.bind("<MouseWheel>",lambda e:self.guide_canvas.yview_scroll(-int(e.delta/120),"units"))
        self.tree=ttk.Treeview(self.state_tab,columns=("zone","star","source"),height=10)
        self.tree.heading("#0",text=self.t("name"));self.tree.heading("zone",text=self.t("zone"));self.tree.heading("star",text=self.t("star"));self.tree.heading("source",text=self.t("source"))
        self.tree.column("#0",width=130,minwidth=90);self.tree.column("zone",width=62);self.tree.column("star",width=48);self.tree.column("source",width=78)
        self.tree.pack(fill="both",expand=True,padx=3,pady=5)
        self.tree.bind("<Double-1>",lambda e:self.correct())
        ttk.Button(self.state_tab,text=self.t("correct"),command=self.correct).pack(fill="x",padx=4,pady=3)
        ttk.Button(self.state_tab,text=self.t("preview"),command=self.preview).pack(fill="x",padx=4,pady=3)
        self.warning=tk.StringVar(value=self.t("warning"))
        tk.Label(self.state_tab,textvariable=self.warning,bg=BG,fg=GOLD,wraplength=365,justify="left").pack(fill="x",padx=5,pady=5)
        footer=ttk.Frame(self.body);footer.pack(fill="x",padx=8,pady=7)
        ttk.Button(footer,text=self.t("refresh"),command=lambda:self.controller.refresh_guides(True)).pack(side="left")
        ttk.Button(footer,text=self.t("export"),command=self.export).pack(side="right")
        self.network=tk.StringVar(value=self.t("cache_loading"))
        tk.Label(self.body,textvariable=self.network,bg=BG,fg=MUTED,anchor="w",font=("Microsoft YaHei UI",9),wraplength=900).pack(fill="x",padx=8,pady=(0,7))
        self.set_text(self.advice_text,self.t("initial_advice"))
        self.render_guides([])
        self.update_network()

    def _build_metrics(self):
        panel=tk.Frame(self.root,bg=METRIC,highlightthickness=1,highlightbackground=BORDER)
        panel.pack(fill="x",padx=16,pady=(2,7))
        for key,label in (("stage",self.t("stage")),("gold",self.t("gold")),("level",self.t("level")),("hp",self.t("hp")),("locked",self.t("locked")),("opacity",self.t("opacity"))):
            cell=tk.Frame(panel,bg=METRIC);cell.pack(side="left",fill="both",expand=True,padx=8,pady=6)
            tk.Label(cell,text=label,bg=METRIC,fg=MUTED,font=("Microsoft YaHei UI",9)).pack(anchor="w")
            value=tk.StringVar(value=self.t("pending") if key!="locked" else self.t("unlocked"))
            self.metric_vars[key]=value
            tk.Label(cell,textvariable=value,bg=METRIC,fg=ACCENT if key!="locked" else GOLD,anchor="w",font=("Microsoft YaHei UI",10,"bold"),wraplength=160).pack(anchor="w")

    def _build_guide_code_bar(self):
        frame=tk.Frame(self.body,bg=METRIC,highlightthickness=1,highlightbackground=BORDER)
        frame.pack(fill="x",padx=8,pady=(0,7))
        tk.Label(frame,text=self.t("guide_code"),bg=METRIC,fg=ACCENT,font=("Microsoft YaHei UI",10,"bold")).pack(side="left",padx=(9,5),pady=6)
        entry=ttk.Entry(frame,textvariable=self.guide_code)
        entry.pack(side="left",fill="x",expand=True,padx=4,pady=5)
        ttk.Button(frame,text=self.t("read_clipboard"),command=self.read_clipboard_code).pack(side="left",padx=3)
        ttk.Button(frame,text=self.t("apply_lock"),command=self.apply_guide_code).pack(side="left",padx=(3,8))
        ttk.Button(frame,text=self.t("clear_lock"),command=self.clear_guide_lock).pack(side="left",padx=(0,8))

    def text_panel(self,parent):
        frame=tk.Frame(parent,bg=BG);frame.pack(fill="both",expand=True,padx=6,pady=6)
        scroll=ttk.Scrollbar(frame);scroll.pack(side="right",fill="y")
        text=tk.Text(frame,bg=PANEL,fg=INK,wrap="word",borderwidth=0,padx=13,pady=13,spacing3=10,height=1,width=1,yscrollcommand=scroll.set,font=("Microsoft YaHei UI",10))
        text.pack(fill="both",expand=True);scroll.configure(command=text.yview)
        text.tag_configure("heading",foreground=ACCENT,font=("Microsoft YaHei UI",11,"bold"))
        text.configure(state="disabled")
        return text

    def set_text(self,widget,value):
        position=widget.yview()[0]
        widget.configure(state="normal");widget.delete("1.0","end");widget.insert("end",value);widget.configure(state="disabled");widget.yview_moveto(position)

    def refresh_windows(self):
        try:
            self.windows=find_game_windows()
            values=[f"{w.title} · {w.width}×{w.height} · {w.hwnd}" for w in self.windows]
            self.window_box["values"]=values
            if len(values)==1:
                self.window_box.current(0)
            elif not values:
                self.window_var.set(self.t("window_missing"))
                self.status.set(self.t("window_missing"))
        except Exception as error:
            self.status.set(f"{self.t('find_window')}: {error}")

    def start(self):
        index=self.window_box.current()
        if index<0 or index>=len(getattr(self,"windows",[])):
            self.refresh_windows();self.status.set(self.t("choose_window"))
            return
        try:
            self.controller.start(self.windows[index])
        except Exception as error:
            self.status.set(self.t("capture_failed",error=error))

    def poll(self):
        try:
            for _ in range(100):
                kind,value=self.controller.events.get_nowait()
                if kind=="status":self.status.set(value)
                elif kind=="result":self.render(value)
                elif kind=="network":self.update_network()
                elif kind=="preview":
                    for window in list(self._preview_windows):
                        if not window.winfo_exists():self._preview_windows.remove(window)
        except Exception as error:
            import queue
            if not isinstance(error,queue.Empty):
                import logging
                logging.exception("UI update failed")
        self.root.after(150,self.poll)

    def render(self,result):
        state=result["state"]
        show=lambda v:self.t("pending") if v is None else str(v)
        self.brief.set(f"{state.difficulty} · {state.round or self.t('stage')+self.t('pending')}\n{self.t('gold')} {show(state.gold)} · {self.t('level')} {show(state.level)} · {self.t('hp')} {show(state.hp)}")
        self.metric_vars["stage"].set({"Early":self.t("early"),"Middle":self.t("middle"),"Final":self.t("final")}.get(state.stage(),self.t("pending")))
        self.metric_vars["gold"].set(show(state.gold));self.metric_vars["level"].set(show(state.level));self.metric_vars["hp"].set(show(state.hp))
        self.metric_vars["locked"].set(self.controller.locked_title or self.t("unlocked"))
        self.metric_vars["opacity"].set(f"{int(self.opacity.get()*100)}%")
        self.locked_summary.set(self.controller.locked_title or self.t("unlocked"))
        text=self.advice_text;position=text.yview()[0];text.configure(state="normal");text.delete("1.0","end")
        for title,body in result["advice"]:
            text.insert("end",title+"\n","heading");text.insert("end",body+"\n\n")
        if any(r.source!="手动" and time.time()-r.at>15 for r in state.roles):
            text.insert("end",self.t("hidden_record"))
        text.configure(state="disabled");text.yview_moveto(position)
        signature=tuple((m.guide["id"],round(m.score,1),tuple(m.reasons),tuple(m.cautions),self.controller.locked) for m in result["matches"])
        if signature!=self._render_signature:
            self.render_guides(result["matches"]);self._render_signature=signature
        self.tree.delete(*self.tree.get_children())
        self.entries=[]
        for item in state.roles+state.shop+state.equipment+state.strategies+([state.environment] if state.environment else []):
            self.entries.append(item)
            self.tree.insert("", "end",iid=str(len(self.entries)-1),text=item.name,values=(item.zone, str(item.star)+"星" if item.star else self.t("pending") if item.kind=="角色" else "—",item.source))
        for pending in state.unresolved:
            identifier=(pending.get("ids") or [""])[0]
            name=" / ".join(self.controller.catalog.name(i) for i in pending.get("ids",[]))
            item=Seen(identifier,name,pending["kind"],self.t("pending"),confidence=pending.get("confidence",0),box=pending.get("box",()))
            self.entries.append(item)
            self.tree.insert("","end",iid=str(len(self.entries)-1),text=name,values=(self.t("pending"),self.t("pending"),pending.get("source",self.t("source"))))
        self.warning.set(state.warning or self.t("warning_pending",count=len(state.unresolved)))
        self.update_network()

    def render_guides(self,matches):
        for widget in self.cards.winfo_children():widget.destroy()
        if not matches:
            tk.Label(self.cards,text=self.t("waiting_guides"),bg=BG,fg=MUTED,wraplength=350,pady=20).pack(fill="x")
        for index,match in enumerate(matches):
            guide=match.guide;detail=guide.get("tourn_detail",{})
            card=tk.Frame(self.cards,bg=PANEL,padx=12,pady=10);card.pack(fill="x",padx=3,pady=5)
            locked=guide["id"]==self.controller.locked
            label=self.t("locked_label") if locked else self.t("main_pick") if index==0 else self.t("alternative",index=index)
            if match.blocked:label+=self.t("blocked")
            tk.Label(card,text=f"{label}  ·  {self.t('fit',score=match.score)}",bg=PANEL,fg=GOLD if match.blocked else ACCENT,anchor="w",font=("Microsoft YaHei UI",11,"bold")).pack(fill="x")
            tk.Label(card,text=guide.get("title","无标题"),bg=PANEL,fg=INK,wraplength=340,justify="left",anchor="w",font=("Microsoft YaHei UI",11,"bold")).pack(fill="x",pady=5)
            tk.Label(card,text=f"{guide.get('nickname',self.t('author_unknown'))} · V{detail.get('rpg_game_big_version',self.t('unknown'))}",bg=PANEL,fg=MUTED,anchor="w",font=("Microsoft YaHei UI",9)).pack(fill="x")
            code=guide.get("tourn_detail",{}).get("share_code","")
            if code:tk.Label(card,text=self.t("guide_code_prefix")+code,bg=PANEL,fg=GOLD if locked else MUTED,wraplength=760,justify="left",anchor="w",font=("Microsoft YaHei UI",9)).pack(fill="x",pady=(3,0))
            for line in match.reasons:
                tk.Label(card,text=line,bg=PANEL,fg=INK,wraplength=340,justify="left",anchor="w").pack(fill="x",pady=(4,0))
            if match.missing:
                tk.Label(card,text=self.t("missing")+"、".join(match.missing),bg=PANEL,fg=GOLD,wraplength=340,justify="left",anchor="w").pack(fill="x",pady=(4,0))
            missing=set(str(r["id"]) for r in stage_roles(guide))-self.controller.tracker.state.owned_ids()
            cost=sum(self.controller.catalog.cost(r) for r in missing)
            tk.Label(card,text=self.t("target_cost",count=len(missing),cost=cost),bg=PANEL,fg=MUTED,wraplength=340,justify="left",anchor="w").pack(fill="x",pady=(4,0))
            for line in match.cautions:
                tk.Label(card,text=line,bg=PANEL,fg=GOLD,wraplength=340,justify="left",anchor="w",font=("Microsoft YaHei UI",9)).pack(fill="x",pady=(4,0))
            buttons=tk.Frame(card,bg=PANEL);buttons.pack(fill="x",pady=(8,0))
            ttk.Button(buttons,text=self.t("copy"),command=lambda g=guide:self.copy_code(g)).pack(side="left")
            ttk.Button(buttons,text=self.t("original"),command=lambda g=guide:webbrowser.open(guide_url(g["id"]))).pack(side="left",padx=5)
            ttk.Button(buttons,text=self.t("unlock") if locked else self.t("lock"),command=lambda g=guide:self.lock(g)).pack(side="left")
            ttk.Button(buttons,text=self.t("details"),command=lambda g=guide:self.details(g)).pack(side="right")

    def copy_code(self,guide):
        code=guide.get("tourn_detail",{}).get("share_code","")
        if not code:
            self.status.set(self.t("guide_code_missing"))
            return
        self.root.clipboard_clear();self.root.clipboard_append(code);self.root.update_idletasks()
        self.status.set(self.t("guide_code_copied"))

    def lock(self,guide):
        if self.controller.locked==guide["id"]:
            self.controller.clear_guide_lock()
        else:
            self.controller.apply_guide_code(guide.get("tourn_detail",{}).get("share_code", ""))
        self.controller.recalculate()

    def read_clipboard_code(self):
        try:
            self.guide_code.set(normalize_share_code(self.root.clipboard_get()))
            self.status.set(self.t("clipboard_read"))
        except tk.TclError:
            self.status.set(self.t("clipboard_empty"))

    def apply_guide_code(self):
        code=self.guide_code.get().strip()
        if not code:
            self.status.set(self.t("paste_first"))
            return
        self.controller.apply_guide_code(code)

    def clear_guide_lock(self):
        self.controller.clear_guide_lock()
        self.guide_code.set("")

    def set_opacity(self,value):
        opacity=max(.55,min(1.0,float(value)))
        self.opacity.set(opacity)
        self.root.attributes("-alpha",opacity)
        if hasattr(self,"opacity_label"):self.opacity_label.configure(text=f"{int(opacity*100)}%")
        if hasattr(self,"settings_opacity_label"):self.settings_opacity_label.configure(text=f"{int(opacity*100)}%")

    def set_topmost(self):
        self.root.attributes("-topmost", bool(self.topmost.get()))
        self.status.set(self.t("topmost_on") if self.topmost.get() else self.t("topmost_off"))

    def details(self,guide):
        window=self.dialog(self.t("detail_title"), "650x680")
        text=self.text_panel(window)
        parts=[guide.get("title",""),self.t("author")+guide.get("nickname",""),self.t("operation")+clean(guide.get("description","尚未取得正文，请打开原文"))]
        for stage in guide.get("tourn_detail",{}).get("role_stages",[]):
            names={"Early":self.t("early"),"Middle":self.t("middle"),"Final":self.t("final")}
            parts.append(names.get(stage.get("stage"),self.t("guides_tab"))+"\n"+self.t("front")+"、".join(r.get("name","") for r in stage.get("front_roles",[]))+"\n"+self.t("back")+"、".join(r.get("name","") for r in stage.get("back_roles",[])))
            for role in stage.get("front_roles",[])+stage.get("back_roles",[]):
                equipment=role.get("first_equipments",[])
                if equipment:parts.append(role.get("name","")+" 装备："+"、".join(e.get("name","") for e in equipment))
        detail=guide.get("tourn_detail",{})
        for title,key in [(self.t("preferred"),"first_fight_augments"),(self.t("secondary"),"second_fight_augments"),(self.t("environment"),"portals")]:
            values=detail.get(key,[])
            parts.append(title+"："+"、".join(v.get("name","") if isinstance(v,dict) else self.controller.catalog.name(str(v)) for v in values))
        parts.append(self.t("origin")+guide_url(guide["id"]))
        self.set_text(text,"\n\n".join(parts))

    def dialog(self,title,size="500x650"):
        window=tk.Toplevel(self.root);window.title(title);window.geometry(size);window.configure(bg=BG);window.attributes("-topmost", bool(self.topmost.get()))
        return window

    def correct(self):
        state=self.controller.tracker.state
        window=self.dialog(self.t("correction_title"), "580x700")
        note=tk.Label(window,text=self.t("correction_note"),bg=BG,fg=MUTED,wraplength=550);note.pack(fill="x",padx=12,pady=10)
        frame=tk.Frame(window,bg=BG);frame.pack(fill="x",padx=12)
        fields={}
        for row,(label,key) in enumerate([(self.t("gold"),"gold"),(self.t("team_level"),"level"),(self.t("hp"),"hp"),(self.t("round"),"round")]):
            tk.Label(frame,text=label,bg=BG,fg=INK).grid(row=row,column=0,sticky="w",pady=3)
            variable=tk.StringVar(value="" if getattr(state,key) is None else str(getattr(state,key)))
            ttk.Entry(frame,textvariable=variable,width=18).grid(row=row,column=1,padx=8)
            fields[key]=variable
        def save_numbers():
            try:
                for key,var in fields.items():
                    value=var.get().strip()
                    if key=="round" and value:
                        import re
                        if not re.fullmatch(r"[1-5]-\d{1,2}",value):raise ValueError("阶段格式应为1-6")
                    if key!="round" and value:
                        number=int(value)
                        maximum=10 if key=="level" else 999
                        if number<0 or number>maximum or key=="level" and number<1:raise ValueError("数值超出范围")
                    setattr(state,key,(value or None) if key=="round" else int(value) if value else None)
                    state.manual_fields.add(key)
                state.warning="经济数值为手动纠正；再次读取到可靠数值或进入新阶段后会更新。"
                self.controller.recalculate()
            except ValueError as error:messagebox.showerror("请核对",str(error),parent=window)
        ttk.Button(frame,text=self.t("save_numbers"),command=save_numbers).grid(row=0,column=2,rowspan=4,padx=8)
        selection=tk.Frame(window,bg=BG);selection.pack(fill="x",padx=12,pady=12)
        kind=tk.StringVar(value="角色");name=tk.StringVar();zone=tk.StringVar(value="备战");star=tk.StringVar(value="待确认");copies=tk.StringVar(value="1")
        ttk.Combobox(selection,textvariable=kind,values=["角色","装备","策略","环境"],state="readonly",width=6).grid(row=0,column=0,padx=(0,6))
        name_box=ttk.Combobox(selection,textvariable=name,width=24);name_box.grid(row=0,column=1,columnspan=3,sticky="ew")
        zone_box=ttk.Combobox(selection,textvariable=zone,state="readonly",width=9);zone_box.grid(row=1,column=0,pady=6)
        ttk.Combobox(selection,textvariable=star,values=["待确认","1","2","3","4"],state="readonly",width=7).grid(row=1,column=1,padx=6)
        tk.Label(selection,text=self.t("copies"),bg=BG,fg=INK).grid(row=1,column=2)
        ttk.Spinbox(selection,from_=1,to=9,textvariable=copies,width=4).grid(row=1,column=3)
        options={}
        owner=tk.StringVar(value="待确认")
        owner_options={r.name:r.id for r in state.roles}
        tk.Label(selection,text=self.t("equipped_to"),bg=BG,fg=INK).grid(row=2,column=0,sticky="w")
        ttk.Combobox(selection,textvariable=owner,values=["待确认"]+list(owner_options),state="readonly",width=24).grid(row=2,column=1,columnspan=3,sticky="ew")
        def update_options(*_):
            nonlocal options
            options={f"{r['name']} · {self.controller.catalog.cost(i)}费 · {i}" if kind.get()=="角色" else f"{r.get('name',i)} · {i}":i for i,r in self.controller.catalog.pool(kind.get()).items()}
            name_box["values"]=list(options)
            zones={"角色":["前台","后台","备战","商店"],"装备":["库存","已装备"],"策略":["已选","待选"],"环境":["已选","待选"]}[kind.get()]
            zone_box["values"]=zones;zone.set(zones[0]);name.set("")
        kind.trace_add("write",update_options);update_options()
        selected=self.tree.selection()
        original=None
        if selected and int(selected[0])<len(getattr(self,"entries",[])):
            original=self.entries[int(selected[0])]
            kind.set(original.kind)
            update_options()
            label=next((label for label,i in options.items() if i==original.id),"")
            name.set(label)
            if original.zone!="待确认":zone.set(original.zone)
            star.set(str(original.star) if original.star else "待确认")
            copies.set(str(original.copies))
            owner.set(self.controller.catalog.name(original.equipped_to) if original.equipped_to else "待确认")
        listing=tk.Listbox(window,bg=PANEL,fg=INK,selectbackground=SELECTED,borderwidth=0,height=10,exportselection=False)
        listing.pack(fill="both",expand=True,padx=12)
        listing_items=[]
        def refresh_list():
            nonlocal listing_items
            listing.delete(0,"end")
            listing_items=state.roles+state.shop+state.equipment+state.strategies+([state.environment] if state.environment else [])
            for item in listing_items:listing.insert("end",f"{item.name} | {item.zone} | {str(item.star)+'星' if item.star else '星级待确认' if item.kind=='角色' else '—'} | ×{item.copies}"+(" → "+self.controller.catalog.name(item.equipped_to) if item.equipped_to else ""))
        def add():
            identifier=options.get(name.get())
            if not identifier:
                exact=[i for label,i in options.items() if normalize(self.controller.catalog.name(i))==normalize(name.get())]
                if len(exact)!=1:messagebox.showinfo("选择名称","请输入名称并从下拉列表选择具体形态。",parent=window);return
                identifier=exact[0]
            try:count=int(copies.get());assert 1<=count<=9
            except (ValueError,AssertionError):return
            item=Seen(identifier,self.controller.catalog.name(identifier),kind.get(),zone.get(),star=int(star.get()) if star.get().isdigit() and kind.get()=="角色" else None,confidence=1,source="手动",copies=count)
            if item.kind=="装备" and item.zone=="已装备":item.equipped_to=owner_options.get(owner.get(),"")
            self.controller.tracker.ignored.discard((item.kind,item.id,item.zone))
            if original and original.id!=item.id and original.kind==item.kind:
                self.controller.tracker.ignored.add((original.kind,original.id,original.zone))
                for previous_pool in (state.roles,state.shop,state.equipment,state.strategies):
                    previous_pool[:]=[r for r in previous_pool if not(r.id==original.id and r.zone==original.zone)]
            pool=state.roles if item.kind=="角色" and item.zone!="商店" else state.shop if item.kind=="角色" else state.equipment if item.kind=="装备" else state.strategies if item.kind=="策略" else None
            if pool is not None:
                pool[:]=[r for r in pool if not(r.id==item.id and r.zone==item.zone)]
                pool.append(item)
            else:state.environment=item
            if item.zone=="商店":self.controller.tracker.manual_shop=list(state.shop)
            self.controller.recalculate();refresh_list()
        def remove():
            if not listing.curselection():return
            item=listing_items[listing.curselection()[0]]
            self.controller.tracker.ignored.add((item.kind,item.id,item.zone))
            for pool in (state.roles,state.shop,state.equipment,state.strategies):
                if item in pool:pool.remove(item)
            if state.environment is item:state.environment=None
            if item.zone=="商店":self.controller.tracker.manual_shop=list(state.shop)
            self.controller.recalculate();refresh_list()
        buttons=tk.Frame(window,bg=BG);buttons.pack(fill="x",padx=12,pady=10)
        ttk.Button(buttons,text=self.t("add_update"),command=add).pack(side="left")
        ttk.Button(buttons,text=self.t("remove_selected"),command=remove).pack(side="left",padx=7)
        def clear_shop():
            self.controller.tracker.manual_shop=None;state.shop=[];refresh_list();self.controller.recalculate()
        ttk.Button(buttons,text=self.t("clear_shop"),command=clear_shop).pack(side="left")
        ttk.Button(buttons,text=self.t("done"),command=window.destroy).pack(side="right")
        refresh_list()

    def preview(self):
        controller=self.controller
        if controller.image is None:
            self.status.set(self.t("start_observe"))
            return
        window=self.dialog(self.t("preview_title"), "1040x730")
        self._preview_windows.append(window)
        picture=controller.image.copy()
        h,w=picture.shape[:2];scale=min(980/w,570/h)
        display=Image.fromarray(picture[:,:,::-1]).resize((int(w*scale),int(h*scale)))
        photo=ImageTk.PhotoImage(display)
        canvas=tk.Canvas(window,width=display.width,height=display.height,bg=BG,highlightthickness=0);canvas.pack(pady=6);canvas.create_image(0,0,image=photo,anchor="nw");canvas.photo=photo
        start=[0,0];box=[0,0,0,0];rectangle=[None]
        def down(event):
            start[:]=[event.x,event.y]
            if rectangle[0]:canvas.delete(rectangle[0])
            rectangle[0]=canvas.create_rectangle(event.x,event.y,event.x,event.y,outline=ACCENT,width=2)
        def move(event):
            if rectangle[0]:canvas.coords(rectangle[0],start[0],start[1],event.x,event.y)
        def up(event):
            box[:]=[int(min(start[0],event.x)/scale),int(min(start[1],event.y)/scale),int(max(start[0],event.x)/scale),int(max(start[1],event.y)/scale)]
        canvas.bind("<Button-1>",down);canvas.bind("<B1-Motion>",move);canvas.bind("<ButtonRelease-1>",up)
        tk.Label(window,text=self.t("preview_note"),bg=BG,fg=MUTED,wraplength=980).pack(fill="x",padx=15)
        row=tk.Frame(window,bg=BG);row.pack(fill="x",padx=15,pady=8)
        zone=tk.StringVar(value="商店")
        ttk.Combobox(row,textvariable=zone,values=list(DEFAULT_REGIONS),state="readonly",width=8).pack(side="left")
        status=tk.StringVar(value=self.t("preview_ready"))
        def save_region():
            if box[2]-box[0]<20 or box[3]-box[1]<15:status.set(self.t("invalid_box"));return
            recognizer=controller.recognizer
            if not recognizer:status.set(self.t("recognizer_loading"));return
            recognizer.regions[zone.get()]=[box[0]/w,box[1]/h,box[2]/w,box[3]/h]
            recognizer.calibrated.add(zone.get())
            recognizer.regions_calibrated=True
            write_json(self.data / "regions.json",{"regions":recognizer.regions,"calibrated":sorted(recognizer.calibrated)})
            status.set(zone.get()+"区域已保存。逐一校准备战、前台、后台和库存后关闭。")
        ttk.Button(row,text=self.t("save_region"),command=save_region).pack(side="left",padx=6)
        kind=tk.StringVar(value="角色");name=tk.StringVar()
        ttk.Combobox(row,textvariable=kind,values=["角色","装备"],state="readonly",width=6).pack(side="left",padx=6)
        item_box=ttk.Combobox(row,textvariable=name,width=23);item_box.pack(side="left")
        choices={}
        def items(*_):
            nonlocal choices
            choices={f"{v['name']} · {i}":i for i,v in controller.catalog.pool(kind.get()).items()}
            item_box["values"]=list(choices);name.set("")
        kind.trace_add("write",items);items()
        def learn():
            identifier=choices.get(name.get())
            if not identifier:status.set(self.t("select_item"));return
            try:
                controller.recognizer.save_crop(picture,box,kind.get(),identifier)
                status.set("图标已学习。后续相同画面会本地匹配。")
            except Exception as error:status.set(str(error))
        ttk.Button(row,text=self.t("learn_icon"),command=learn).pack(side="left",padx=6)
        ttk.Button(row,text=self.t("close"),command=window.destroy).pack(side="right")
        tk.Label(window,textvariable=status,bg=BG,fg=ACCENT,wraplength=980,anchor="w").pack(fill="x",padx=15)

    def update_network(self):
        c=self.controller.client
        at=time.strftime("%m-%d %H:%M",time.localtime(c.updated_at)) if c.updated_at else "未知"
        self.network.set(self.t("network",version=self.controller.catalog.version,count=len(self.controller.guides),connection=self.t("online") if c.online else self.t("offline"),updated=at))

    def new_game(self):
        self.controller.tracker.reset();self.controller.clear_guide_lock();self.guide_code.set("");self.controller._signature=None
        self.controller.recalculate();self.status.set(self.t("new_game_done"))

    def export(self):
        target=self.data / ("诊断-"+time.strftime("%Y%m%d-%H%M%S")+".json")
        self.controller.export_report(target)
        self.status.set(self.t("export_done"))

    def toggle(self):
        if self.collapsed:
            self.root.minsize(760,480);self.body.pack(fill="both",expand=True);self.root.geometry(self._geometry);self.collapsed=False;self.fold_button.configure(text=self.t("fold"))
        else:
            self._geometry=self.root.geometry();self.body.pack_forget();self.root.minsize(760,120);self.root.geometry("900x145");self.collapsed=True;self.fold_button.configure(text=self.t("expand"))

    def close(self):
        self.save_settings()
        self.controller.close();self.root.destroy()
