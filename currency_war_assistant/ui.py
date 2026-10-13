from __future__ import annotations

from pathlib import Path
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser

from PIL import Image,ImageTk

from .api import guide_url
from . import __version__
from .capture import find_game_windows, CaptureDependencyUnavailable,unsupported_client_title
from .controller import Controller,normalize_share_code
from .models import Seen,normalize
from .paths import data_dir,read_json,write_json
from .strategy import clean,target_level,stage_roles
from .vision import DEFAULT_REGIONS
from .window import WindowChrome

BG="#17133a"; PANEL="#211c4f"; INK="#f5f1ff"; MUTED="#b9b4dc"; ACCENT="#61e4ff"; GOLD="#ffd36e"; BUTTON="#302766"; BORDER="#594b9d"; SELECTED="#493d86"; METRIC="#1d1944"
THEMES={
    "dark":{"BG":"#17133a","PANEL":"#211c4f","INK":"#f5f1ff","MUTED":"#b9b4dc","ACCENT":"#61e4ff","GOLD":"#ffd36e","BUTTON":"#302766","BORDER":"#594b9d","SELECTED":"#493d86","METRIC":"#1d1944"},
    "light":{"BG":"#e9e6ff","PANEL":"#faf8ff","INK":"#241d4f","MUTED":"#5e5a85","ACCENT":"#326fc2","GOLD":"#a66a00","BUTTON":"#d6d1f4","BORDER":"#a69bdf","SELECTED":"#bfc9f5","METRIC":"#ddd9f8"},
}
THEME_OPTIONS=(("深色","dark"),("浅色","light"))

from .localization import I18N,LANGUAGE_OPTIONS,translate,enum_label


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
        self.borderless=tk.BooleanVar(value=bool(self.settings.get("borderless",False)))
        self.chrome=WindowChrome(root)
        self._apply_theme(self.theme)
        self.controller=Controller(self.data)
        self.controller.set_language(self.language,recalculate=False)
        self.root.title(f"{self.t('title')} · v{__version__}")
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
        self._tree_signature=None
        self._selected_key=None
        self._preview_windows=[]
        self.settings_open=False
        self.guide_code=tk.StringVar()
        self._clipboard_share=""
        self.locked_summary=tk.StringVar(value=self.t("unlocked"))
        self.metric_vars={}
        self._build_style()
        self._build()
        self.root.bind("<Escape>", self.restore_frame, add="+")
        self.root.after_idle(lambda: self.set_borderless(announce=False))
        # The assistant is intentionally capturable by Windows screenshots and recordings.
        self.root.after(150,self.poll)
        self.root.after(300,self.controller.initialize)
        self.root.after(400,self.refresh_windows)

    def _apply_theme(self,theme):
        global BG,PANEL,INK,MUTED,ACCENT,GOLD,BUTTON,BORDER,SELECTED,METRIC
        palette=THEMES.get(theme,THEMES["dark"])
        BG,PANEL,INK,MUTED,ACCENT,GOLD,BUTTON,BORDER,SELECTED,METRIC=(palette[k] for k in ("BG","PANEL","INK","MUTED","ACCENT","GOLD","BUTTON","BORDER","SELECTED","METRIC"))

    def save_settings(self):
        write_json(self.data / "settings.json",{"language":self.language,"theme":self.theme,"opacity":round(float(self.opacity.get()),2),"topmost":bool(self.topmost.get()),"borderless":bool(self.borderless.get())})

    def set_borderless(self,announce=True):
        try:
            self.chrome.set_borderless(self.borderless.get())
            if announce:
                self.status.set(self.t("borderless_on" if self.borderless.get() else "borderless_off"))
        except Exception as error:
            self.borderless.set(self.chrome.borderless)
            self.status.set(self.t("borderless_failed",error=error))

    def restore_frame(self,event=None):
        if self.borderless.get():
            self.borderless.set(False)
            self.set_borderless()

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
        settings_open=self.settings_open
        for child in list(self.root.winfo_children()):
            child.destroy()
        self._render_signature=None
        self._tree_signature=None
        self._preview_windows=[]
        self.metric_vars={}
        self.settings_open=False
        self.language_var.set(next(label for label,code in LANGUAGE_OPTIONS if code==self.language))
        self.theme_var.set(self.theme_label(self.theme))
        self.root.title(f"{self.t('title')} · v{__version__}")
        self._build_style()
        self._build()
        self.root.configure(bg=BG)
        if settings_open:self.open_settings()
        if self.collapsed:
            self.body.pack_forget()
            self.fold_button.configure(text=self.t("expand"))
            self._fit_folded_window()
        self.refresh_windows()
        self.controller.set_language(self.language)

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
        if self.collapsed:self._fit_folded_window()

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
        style.map("TCombobox",fieldbackground=[("readonly",PANEL)],foreground=[("readonly",INK)],background=[("readonly",BUTTON)])

    def _build_settings_panel(self):
        self.settings_panel=tk.Frame(self.root,bg=METRIC,highlightthickness=1,highlightbackground=BORDER)
        row=tk.Frame(self.settings_panel,bg=METRIC);row.pack(fill="x",padx=10,pady=(5,0))
        tk.Label(row,text=self.t("settings"),bg=METRIC,fg=ACCENT,font=("Microsoft YaHei UI",11,"bold")).pack(side="left",padx=(0,12))
        tk.Checkbutton(row,text=self.t("topmost_label"),variable=self.topmost,command=self.set_topmost,bg=METRIC,fg=INK,activebackground=METRIC,activeforeground=INK,selectcolor=BUTTON,highlightthickness=0).pack(side="left",padx=(0,12))
        self.borderless_check=tk.Checkbutton(row,text=self.t("borderless"),variable=self.borderless,command=self.set_borderless,bg=METRIC,fg=INK,activebackground=METRIC,activeforeground=INK,selectcolor=BUTTON,highlightthickness=0)
        self.borderless_check.pack(side="left",padx=(0,12))
        tk.Label(row,text=self.t("opacity"),bg=METRIC,fg=MUTED).pack(side="left")
        self.settings_opacity_label=tk.Label(row,text=f"{int(self.opacity.get()*100)}%",bg=METRIC,fg=INK,width=5)
        def update_opacity(value):
            self.set_opacity(value);self.settings_opacity_label.configure(text=f"{int(self.opacity.get()*100)}%")
        tk.Scale(row,from_=0.55,to=1.0,variable=self.opacity,orient="horizontal",length=135,showvalue=False,resolution=.01,bg=METRIC,fg=INK,highlightthickness=0,troughcolor=BUTTON,command=update_opacity).pack(side="left",padx=(5,0))
        self.settings_opacity_label.pack(side="left")
        row=tk.Frame(self.settings_panel,bg=METRIC);row.pack(fill="x",padx=10,pady=(0,5))
        tk.Label(row,text=self.t("language"),bg=METRIC,fg=MUTED).pack(side="left")
        language_box=ttk.Combobox(row,textvariable=self.language_var,values=[name for name,code in LANGUAGE_OPTIONS],state="readonly",width=9)
        language_box.pack(side="left",padx=(4,10));language_box.bind("<<ComboboxSelected>>",self.set_language)
        tk.Label(row,text=self.t("theme"),bg=METRIC,fg=MUTED).pack(side="left")
        theme_box=ttk.Combobox(row,textvariable=self.theme_var,values=[self.theme_label("dark"),self.theme_label("light")],state="readonly",width=8)
        theme_box.pack(side="left",padx=(4,10));theme_box.bind("<<ComboboxSelected>>",self.set_theme)
        tk.Label(row,text=self.t("save_on_close"),bg=METRIC,fg=MUTED,font=("Microsoft YaHei UI",8)).pack(side="left",padx=(0,8))

    def _build(self):
        self._enum_boxes=[]
        self._build_settings_panel()
        self.header=tk.Frame(self.root,bg=BG)
        self.header.pack(fill="x",padx=16,pady=(12,5))
        self.title_label=tk.Label(self.header,text=self.t("title"),bg=BG,fg=ACCENT,font=("Microsoft YaHei UI",13,"bold"))
        self.title_label.pack(side="left")
        self.chrome.bind_drag(self.header);self.chrome.bind_drag(self.title_label)
        tk.Label(self.header,text=f"v{__version__}",bg=BG,fg=MUTED,font=("Microsoft YaHei UI",9)).pack(side="left",padx=(6,0))
        self.settings_button=ttk.Button(self.header,text=self.t("settings"),command=self.open_settings,width=8)
        self.settings_button.pack(side="left",padx=(12,0))
        ttk.Button(self.header,text="×",command=self.close,width=3).pack(side="right",padx=(5,0))
        ttk.Button(self.header,text="−",command=self.root.iconify,width=3).pack(side="right",padx=(5,0))
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
        correction_label={"zh":"识别纠正","en":"Correct recognition","ja":"認識修正"}[self.language]
        self.correction_button=ttk.Button(controls,text=correction_label,command=self.correct)
        self.correction_button.pack(side="left",padx=(6,0))
        self._build_guide_code_bar()
        self.network=tk.StringVar(value=self.t("cache_loading"))
        tk.Label(self.body,textvariable=self.network,bg=BG,fg=MUTED,anchor="w",font=("Microsoft YaHei UI",9),wraplength=900).pack(side="bottom",fill="x",padx=8,pady=(0,7))
        self.footer=ttk.Frame(self.body);self.footer.pack(side="bottom",fill="x",padx=8,pady=7)
        ttk.Button(self.footer,text=self.t("refresh"),command=lambda:self.controller.refresh_guides(True)).pack(side="left")
        ttk.Button(self.footer,text=self.t("export"),command=self.export).pack(side="right")
        self.client_hint=tk.StringVar(value=self.t("client_only"))
        tk.Label(self.footer,textvariable=self.client_hint,bg=BG,fg=MUTED,wraplength=650,
                 font=("Microsoft YaHei UI",8),justify="left").pack(side="left",padx=12)
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
        # Reserve tools before the expanding list: pack otherwise clips later
        # buttons in the default 650px window, especially with long guide titles.
        self.state_actions=ttk.Frame(self.state_tab)
        self.state_actions.pack(fill="x",padx=4,pady=(4,0))
        self.state_correct_button=ttk.Button(self.state_actions,text=self.t("correct"),command=self.correct)
        self.state_correct_button.pack(side="left",padx=(0,6))
        self.state_preview_button=ttk.Button(self.state_actions,text=self.t("preview"),command=self.preview)
        self.state_preview_button.pack(side="left")
        self.warning=tk.StringVar(value=self.t("warning"))
        tk.Label(self.state_tab,textvariable=self.warning,bg=BG,fg=GOLD,wraplength=900,justify="left").pack(fill="x",padx=5,pady=4)
        state_list=ttk.Frame(self.state_tab)
        state_list.pack(fill="both",expand=True,padx=3,pady=(0,4))
        state_scroll=ttk.Scrollbar(state_list,orient="vertical")
        state_scroll.pack(side="right",fill="y")
        self.tree=ttk.Treeview(state_list,columns=("zone","star","source"),height=1,yscrollcommand=state_scroll.set)
        state_scroll.configure(command=self.tree.yview)
        self.tree.heading("#0",text=self.t("name"));self.tree.heading("zone",text=self.t("zone"));self.tree.heading("star",text=self.t("star"));self.tree.heading("source",text=self.t("source"))
        self.tree.column("#0",width=130,minwidth=90);self.tree.column("zone",width=62);self.tree.column("star",width=48);self.tree.column("source",width=78)
        self.tree.pack(fill="both",expand=True)
        self.tree.bind("<Double-1>",lambda e:self.correct())
        self.tree.bind("<<TreeviewSelect>>",self._remember_selection)
        self.set_text(self.advice_text,self.t("initial_advice"))
        self.render_guides([])
        self.update_network()
        self.resize_grip=tk.Label(self.root,text="◢",bg=BG,fg=MUTED,cursor="size_nw_se",font=("Microsoft YaHei UI",12))
        self.resize_grip.place(relx=1,rely=1,anchor="se",x=-2,y=-2,width=18,height=18)
        self.chrome.bind_resize(self.resize_grip)

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
        self.lookup_summary=tk.StringVar()
        tk.Label(self.body,textvariable=self.lookup_summary,bg=BG,fg=GOLD,anchor="w",justify="left",wraplength=900,font=("Microsoft YaHei UI",9)).pack(fill="x",padx=10,pady=(0,4))
        self.update_lookup()

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
            self.client_hint.set(self.t("client_title_warning") if unsupported_client_title(self.windows[index].title) else self.t("client_only"))
            self.controller.start(self.windows[index])
        except CaptureDependencyUnavailable as error:
            self.status.set(self.t("capture_dependency_missing",error=error))
        except Exception as error:
            self.status.set(self.t("capture_failed",error=error))

    def poll(self):
        try:
            for _ in range(100):
                kind,value=self.controller.events.get_nowait()
                if kind=="status":self.status.set(value)
                elif kind=="result":self.render(value)
                elif kind=="network":self.update_network()
                elif kind=="guide_lookup":self.update_lookup()
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
        self._render_entries(state)
        self.warning.set(state.warning or self.t("warning_pending",count=len(state.unresolved)))
        self.update_network()

    @staticmethod
    def entry_key(item):
        return (item.kind,item.id,item.zone)

    def _remember_selection(self,event=None):
        selected=self.tree.selection()
        if selected and int(selected[0])<len(getattr(self,"entries",[])):
            self._selected_key=self.entry_key(self.entries[int(selected[0])])

    def _render_entries(self,state):
        entries=state.roles+state.shop+state.equipment+state.strategies+state.investment_choices+([state.environment] if state.environment else [])
        for pending in state.unresolved:
            identifier=(pending.get("ids") or [""])[0]
            name=" / ".join(self.controller.catalog.name(i,pending["kind"]) for i in pending.get("ids",[]))
            item=Seen(identifier,name,pending["kind"],"待确认",confidence=pending.get("confidence",0),box=pending.get("box",()),source=pending.get("source","画面"))
            entries.append(item)
        signature=tuple((e.kind,e.id,e.zone,e.name,e.star,e.copies,e.source,e.slot,e.equipped_to) for e in entries)
        self._remember_selection()
        self.entries=entries
        if signature==self._tree_signature:
            return
        position=self.tree.yview()[0]
        self.tree.delete(*self.tree.get_children())
        for i,item in enumerate(entries):
            self.tree.insert("","end",iid=str(i),text=item.name,values=(enum_label(self.language,item.zone),self.t("stars_value",count=item.star) if item.star else self.t("pending") if item.kind=="角色" else "—",enum_label(self.language,item.source)))
        restored=next((str(i) for i,e in enumerate(entries) if self.entry_key(e)==self._selected_key),None)
        if restored is not None:self.tree.selection_set(restored)
        self.tree.yview_moveto(position)
        self._tree_signature=signature

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
            missing=set(str(r["id"]) for r in stage_roles(guide))-self.controller.get_state().owned_ids()
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
            self.controller.lock_guide(guide)

    def read_clipboard_code(self):
        try:
            self._clipboard_share=self.root.clipboard_get()
            self.guide_code.set(normalize_share_code(self._clipboard_share))
            self.status.set(self.t("clipboard_read"))
        except tk.TclError:
            self.status.set(self.t("clipboard_empty"))

    def apply_guide_code(self):
        code=self.guide_code.get().strip()
        if not code:
            self.status.set(self.t("paste_first"))
            return
        share=self._clipboard_share if normalize_share_code(self._clipboard_share)==normalize_share_code(code) else code
        self.controller.apply_guide_code(share)

    def clear_guide_lock(self):
        self.controller.clear_guide_lock()
        self.guide_code.set("")
        self._clipboard_share=""

    def set_opacity(self,value):
        opacity=max(.55,min(1.0,float(value)))
        self.opacity.set(opacity)
        self.root.attributes("-alpha",opacity)
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
                if equipment:parts.append(role.get("name","")+" · "+self.t("equipment")+": "+"、".join(e.get("name","") for e in equipment))
        detail=guide.get("tourn_detail",{})
        for title,key in [(self.t("preferred"),"first_fight_augments"),(self.t("secondary"),"second_fight_augments"),(self.t("environment"),"portals")]:
            values=detail.get(key,[])
            kind="环境" if key=="portals" else "策略"
            parts.append(title+"："+"、".join((v.get("name") or v.get("title") or self.controller.catalog.name(str(v.get("id","")),kind)) if isinstance(v,dict) else self.controller.catalog.name(str(v),kind) for v in values))
        parts.append(self.t("origin")+guide_url(guide["id"]))
        self.set_text(text,"\n\n".join(parts))

    def dialog(self,title,size="500x650"):
        window=tk.Toplevel(self.root);window.title(title);window.geometry(size);window.configure(bg=BG);window.attributes("-topmost", bool(self.topmost.get()))
        return window

    def enum_box(self,parent,variable,values,**options):
        """Translate display choices while retaining Chinese internal enums."""
        display=tk.StringVar(value=enum_label(self.language,variable.get()))
        box=ttk.Combobox(parent,textvariable=display,**options)
        reverse={}
        def set_values(values):
            reverse.clear();reverse.update({enum_label(self.language,v):v for v in values})
            box['values']=list(reverse)
        def selected(event=None):
            if display.get() in reverse:variable.set(reverse[display.get()])
        variable.trace_add('write',lambda *_:display.set(enum_label(self.language,variable.get())))
        box.bind('<<ComboboxSelected>>',selected)
        box.set_enum_values=set_values
        set_values(values)
        self._enum_boxes.append((variable,box))
        return box

    def correct(self):
        state=self.controller.get_state()
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
                self.controller.save_numbers({key:var.get() for key,var in fields.items()})
            except ValueError as error:messagebox.showerror(self.t("confirm"),str(error),parent=window)
        ttk.Button(frame,text=self.t("save_numbers"),command=save_numbers).grid(row=0,column=2,rowspan=4,padx=8)
        selection=tk.Frame(window,bg=BG);selection.pack(fill="x",padx=12,pady=12)
        kind=tk.StringVar(value="角色");name=tk.StringVar();zone=tk.StringVar(value="备战");star=tk.StringVar(value="待确认");copies=tk.StringVar(value="1")
        self.enum_box(selection,kind,["角色","装备","策略","环境"],state="readonly",width=10).grid(row=0,column=0,padx=(0,6))
        name_box=ttk.Combobox(selection,textvariable=name,width=24);name_box.grid(row=0,column=1,columnspan=3,sticky="ew")
        zone_box=self.enum_box(selection,zone,[],state="readonly",width=10);zone_box.grid(row=1,column=0,pady=6)
        self.enum_box(selection,star,["待确认","1","2","3","4"],state="readonly",width=7).grid(row=1,column=1,padx=6)
        tk.Label(selection,text=self.t("copies"),bg=BG,fg=INK).grid(row=1,column=2)
        ttk.Spinbox(selection,from_=1,to=9,textvariable=copies,width=4).grid(row=1,column=3)
        options={}
        owner=tk.StringVar(value="待确认")
        owner_options={r.name:r.id for r in state.roles}
        tk.Label(selection,text=self.t("equipped_to"),bg=BG,fg=INK).grid(row=2,column=0,sticky="w")
        self.enum_box(selection,owner,["待确认"]+list(owner_options),state="readonly",width=24).grid(row=2,column=1,columnspan=3,sticky="ew")
        def update_options(*_):
            nonlocal options
            options={f"{r['name']} · {self.controller.catalog.cost(i)} · {i}" if kind.get()=="角色" else f"{r.get('name',i)} · {i}":i for i,r in self.controller.catalog.pool(kind.get()).items()}
            name_box["values"]=list(options)
            zones={"角色":["前台","后台","备战","商店"],"装备":["库存","已装备"],"策略":["已选","待选"],"环境":["已选","待选"]}[kind.get()]
            zone_box.set_enum_values(zones);zone.set(zones[0]);name.set("")
        kind.trace_add("write",update_options);update_options()
        self._remember_selection()
        original=None
        original=next((e for e in getattr(self,"entries",[]) if self.entry_key(e)==self._selected_key),None)
        if original:
            kind.set(original.kind)
            update_options()
            label=next((label for label,i in options.items() if i==original.id),"")
            name.set(label)
            if original.zone!="待确认":zone.set(original.zone)
            star.set(str(original.star) if original.star else "待确认")
            copies.set(str(original.copies))
            owner.set(self.controller.catalog.name(original.equipped_to,"角色") if original.equipped_to else "待确认")
        listing=tk.Listbox(window,bg=PANEL,fg=INK,selectbackground=SELECTED,borderwidth=0,height=10,exportselection=False)
        listing.pack(fill="both",expand=True,padx=12)
        listing_items=[]
        def refresh_list():
            nonlocal listing_items,state
            state=self.controller.get_state()
            listing.delete(0,"end")
            listing_items=state.roles+state.shop+state.equipment+state.strategies+state.investment_choices+([state.environment] if state.environment else [])
            for item in listing_items:listing.insert("end",f"{item.name} | {enum_label(self.language,item.zone)} | {self.t("stars_value",count=item.star) if item.star else self.t("pending") if item.kind=="角色" else "—"} | ×{item.copies}"+(" → "+self.controller.catalog.name(item.equipped_to,"角色") if item.equipped_to else ""))
        def add():
            identifier=options.get(name.get())
            if not identifier:
                exact=[i for label,i in options.items() if normalize(self.controller.catalog.name(i,kind.get()))==normalize(name.get())]
                if len(exact)!=1:messagebox.showinfo(self.t("name"),self.t("invalid_name"),parent=window);return
                identifier=exact[0]
            try:count=int(copies.get());assert 1<=count<=9
            except (ValueError,AssertionError):return
            item=Seen(identifier,self.controller.catalog.name(identifier,kind.get()),kind.get(),zone.get(),star=int(star.get()) if star.get().isdigit() and kind.get()=="角色" else None,confidence=1,source="手动",copies=count)
            if original and original.kind==item.kind:
                item.slot=original.slot
            if item.kind=="装备" and item.zone=="已装备":item.equipped_to=owner_options.get(owner.get(),"")
            self.controller.correct_item(item,original);refresh_list()
        def remove():
            if not listing.curselection():return
            self.controller.remove_item(listing_items[listing.curselection()[0]])
            refresh_list()
        buttons=tk.Frame(window,bg=BG);buttons.pack(fill="x",padx=12,pady=10)
        ttk.Button(buttons,text=self.t("add_update"),command=add).pack(side="left")
        ttk.Button(buttons,text=self.t("remove_selected"),command=remove).pack(side="left",padx=7)
        def clear_shop():
            self.controller.clear_manual_shop();refresh_list()
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
        self.enum_box(row,zone,list(DEFAULT_REGIONS),state="readonly",width=10).pack(side="left")
        status=tk.StringVar(value=self.t("preview_ready"))
        def save_region():
            if box[2]-box[0]<20 or box[3]-box[1]<15:status.set(self.t("invalid_box"));return
            recognizer=controller.recognizer
            if not recognizer:status.set(self.t("recognizer_loading"));return
            recognizer.regions[zone.get()]=[box[0]/w,box[1]/h,box[2]/w,box[3]/h]
            recognizer.calibrated.add(zone.get())
            recognizer.regions_calibrated=True
            write_json(self.data / "regions.json",{"regions":recognizer.regions,"calibrated":sorted(recognizer.calibrated)})
            status.set(enum_label(self.language,zone.get())+" · "+self.t("save_region_status"))
        ttk.Button(row,text=self.t("save_region"),command=save_region).pack(side="left",padx=6)
        kind=tk.StringVar(value="角色");name=tk.StringVar()
        self.enum_box(row,kind,["角色","装备"],state="readonly",width=10).pack(side="left",padx=6)
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
                status.set(self.t("learn_status"))
            except Exception as error:status.set(str(error))
        ttk.Button(row,text=self.t("learn_icon"),command=learn).pack(side="left",padx=6)
        ttk.Button(row,text=self.t("close"),command=window.destroy).pack(side="right")
        tk.Label(window,textvariable=status,bg=BG,fg=ACCENT,wraplength=980,anchor="w").pack(fill="x",padx=15)

    def update_lookup(self):
        lookup=self.controller.lookup
        state=lookup.get("state","idle")
        self.lookup_summary.set("" if state=="idle" else self.t("lookup_"+state,**lookup))
        if state=="locked":
            self.guide_code.set(self.controller.locked_code)

    def update_network(self):
        c=self.controller.client
        at=time.strftime("%m-%d %H:%M",time.localtime(c.updated_at)) if c.updated_at else self.t("unknown")
        summary=c.summary()
        coverage=summary["coverage"]
        pages=sum(s.get("page",0) for s in coverage.get("orders",{}).values())
        coverage_text=self.t("coverage_"+coverage.get("state","partial"),pages=pages)
        self.network.set(self.t("network",version=self.controller.catalog.version,count=summary["count"],codes=summary["codes"],connection=self.t("online") if c.online else self.t("offline"),updated=at,coverage=coverage_text))

    def new_game(self):
        self.controller.tracker.reset();self.controller.clear_guide_lock();self.guide_code.set("");self.controller._signature=None
        self.controller.recalculate();self.status.set(self.t("new_game_done"))

    def export(self):
        target=self.data / ("diagnostic-"+time.strftime("%Y%m%d-%H%M%S")+".json")
        self.controller.export_report(target)
        self.status.set(self.t("export_done"))

    def toggle(self):
        if self.collapsed:
            self.root.minsize(760,480);self.body.pack(fill="both",expand=True);self.chrome.set_size(*self._expanded_size);self.collapsed=False;self.fold_button.configure(text=self.t("fold"))
        else:
            self._expanded_size=(self.root.winfo_width(),self.root.winfo_height());self.body.pack_forget();self.root.minsize(760,120);self.collapsed=True;self.fold_button.configure(text=self.t("expand"));self._fit_folded_window()

    def _fit_folded_window(self):
        self.root.update_idletasks()
        self.chrome.set_size(900,max(145,self.root.winfo_reqheight()))

    def close(self):
        self.save_settings()
        self.controller.close();self.root.destroy()
