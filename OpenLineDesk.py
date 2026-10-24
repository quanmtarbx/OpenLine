import hashlib, json, os, re, subprocess, sys, threading, tkinter as tk, urllib.request, webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

VERSION = "0.3.1"
DEFAULT_UPDATE_FEED = "https://github.com/quanmtarbx/OpenLine/releases/latest/download/update-manifest.json"
CFG = Path.home()/".openline-desk"/"settings.json"
PROGRAMS = ["Default service","(1) Weekday service","(2) Regular service","(4) Regular service","(5) Regular service","(6) Weekday service"]

def read_cfg():
    try: return json.loads(CFG.read_text(encoding="utf-8"))
    except (OSError, ValueError): return {}
def write_cfg(d):
    CFG.parent.mkdir(parents=True,exist_ok=True); CFG.write_text(json.dumps(d,indent=2),encoding="utf-8")
def files(root, suffixes):
    if not str(root).strip(): return []
    p=Path(root)
    return sorted((x for x in p.rglob("*") if x.is_file() and x.suffix.lower() in suffixes),key=lambda x:str(x).lower()) if p.is_dir() else []
def trains(root):
    if not str(root).strip(): return []
    p=Path(root)
    return sorted({x.parent for x in p.rglob("train.dat") if x.is_file()},key=lambda x:str(x).lower()) if p.is_dir() else []
def rel(p,root):
    try: return str(p.relative_to(root))
    except ValueError: return str(p)

def detect_multiplayer_files(exe):
    p=Path(exe) if exe else None
    return bool(p and p.is_file() and (p.parent/"Multiplayer.dll").is_file() and (p.parent/"Server"/"Server.exe").is_file())

def detect_multiplayer_exe():
    """Find the OBND multiplayer installation without mistaking vanilla OpenBVE for it."""
    candidates=[]
    try:
        import winreg
        uninstall_keys=(
            (winreg.HKEY_LOCAL_MACHINE,r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE,r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER,r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        )
        for hive,key_path in uninstall_keys:
            try:
                with winreg.OpenKey(hive,key_path) as root:
                    for i in range(winreg.QueryInfoKey(root)[0]):
                        try:
                            with winreg.OpenKey(root,winreg.EnumKey(root,i)) as item:
                                name=winreg.QueryValueEx(item,"DisplayName")[0]
                                if "openbve" not in name.lower() or "multiplayer" not in name.lower():continue
                                location=winreg.QueryValueEx(item,"InstallLocation")[0]
                                if location:candidates.append(Path(location)/"OpenBve.exe")
                        except (OSError,IndexError):pass
            except OSError:pass
    except ImportError:pass
    for root in (os.environ.get("ProgramFiles(x86)"),os.environ.get("ProgramFiles")):
        if root:candidates.append(Path(root)/"openBVE"/"OpenBve.exe")
    for candidate in candidates:
        if (candidate.is_file() and (candidate.parent/"Multiplayer.dll").is_file()
                and (candidate.parent/"Server"/"Server.exe").is_file()):
            return str(candidate)
    return ""

class Desk(tk.Tk):
 def __init__(self):
    super().__init__(); self.cfg=read_cfg(); self.title("OpenLine Desk · OpenBVE companion"); self.geometry("1240x820"); self.minsize(960,680); self.configure(bg="#10171e")
    s=ttk.Style(self); s.theme_use("clam"); s.configure("TFrame",background="#10171e"); s.configure("Card.TFrame",background="#1b252e")
    s.configure("TLabel",background="#10171e",foreground="#e8eef3",font=("Segoe UI",10)); s.configure("Muted.TLabel",background="#1b252e",foreground="#93a5b4",font=("Segoe UI",9))
    s.configure("Title.TLabel",background="#10171e",foreground="#edf4f7",font=("Segoe UI Semibold",23)); s.configure("Sub.TLabel",background="#10171e",foreground="#a3b3be",font=("Segoe UI",10))
    s.configure("TButton",font=("Segoe UI Semibold",10),padding=(11,8),background="#243544",foreground="#eaf1f5",borderwidth=0); s.map("TButton",background=[("active","#344d60")])
    s.configure("Accent.TButton",background="#e4a94a",foreground="#15202a"); s.map("Accent.TButton",background=[("active","#f3bd64")])
    s.configure("TCombobox",fieldbackground="#17222c",background="#17222c",foreground="#edf4f7",arrowcolor="#f0a64a",padding=7); s.map("TCombobox",fieldbackground=[("readonly","#17222c"),("disabled","#17222c"),("focus","#17222c")],foreground=[("readonly","#edf4f7"),("disabled","#82919b")]); s.configure("TEntry",fieldbackground="#17222c",foreground="#edf4f7",insertcolor="#edf4f7",padding=7)
    s.configure("Treeview",background="#0c141d",foreground="#e8eef3",fieldbackground="#0c141d",rowheight=26); s.configure("Treeview.Heading",background="#1c2a36",foreground="#b9c9d3")
    self.rr=tk.StringVar(value=self.cfg.get("route_root","")); self.tr=tk.StringVar(value=self.cfg.get("train_root","")); self.ex=tk.StringVar(value=self.cfg.get("exe",""))
    self.routes=[]; self.trainlist=[]; self.rm={}; self.tm={}; self.build(); self.after(300,self.refresh); self.after(700,self.checks)
 def section(self,p,title,sub):
    f=ttk.Frame(p); f.pack(fill="x",pady=(10,8)); ttk.Label(f,text=title,foreground="#f0a64a",font=("Segoe UI Semibold",9)).pack(anchor="w"); ttk.Label(f,text=sub,style="Sub.TLabel").pack(anchor="w",pady=(2,0))
 def card(self,p,manager="pack"):
    f=ttk.Frame(p,style="Card.TFrame")
    if manager=="pack": f.pack(fill="x")
    return f
 def build(self):
    self.r=tk.StringVar(); self.t=tk.StringVar(); self.update_feed=tk.StringVar(value=self.cfg.get("update_feed") or DEFAULT_UPDATE_FEED)
    self.prog=tk.StringVar(value=PROGRAMS[0]); self.day=tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
    self.tmval=tk.StringVar(value="08:00"); self.sched=tk.StringVar(value="OpenBVE route default"); self.cond=tk.BooleanVar()
    shell=ttk.Frame(self); shell.pack(fill="both",expand=True)
    nav=ttk.Frame(shell,style="Card.TFrame",width=190); nav.pack(side="left",fill="y"); nav.pack_propagate(False)
    ttk.Label(nav,text="OPENLINE",foreground="#f0a64a",background="#1b252e",font=("Segoe UI Semibold",14)).pack(anchor="w",padx=20,pady=(24,0))
    ttk.Label(nav,text="DESK  ·  OPENBVE",foreground="#a3b3be",background="#1b252e",font=("Segoe UI",8)).pack(anchor="w",padx=20,pady=(2,22))
    for label,page in (("▶   Drive","Drive"),("◎   Multiplayer","Multiplayer"),("▦   Content","Content"),("⚙   Settings","Settings"),("?   Help","Help")):
        ttk.Button(nav,text=label,command=lambda p=page:self.show_page(p)).pack(fill="x",padx=12,pady=4)
    ttk.Label(nav,text="OpenBVE companion\nVersion "+VERSION,foreground="#667987",background="#1b252e",font=("Segoe UI",8),justify="left").pack(side="bottom",anchor="w",padx=20,pady=18)
    self.page_host=ttk.Frame(shell); self.page_host.pack(side="left",fill="both",expand=True)
    self.mp_exe=tk.StringVar(value=self.cfg.get("mp_exe","") or detect_multiplayer_exe()); self.mp_name=tk.StringVar(value=""); self.mp_room=tk.StringVar(value="")
    self.pages={}; self.page_canvases={}; self._build_drive(); self._build_multiplayer(); self._build_content(); self._build_settings(); self._build_help()
    self.show_page("Drive")
 def _page(self,name):
    outer=ttk.Frame(self.page_host); self.pages[name]=outer
    canvas=tk.Canvas(outer,bg="#10171e",highlightthickness=0); bar=ttk.Scrollbar(outer,orient="vertical",command=canvas.yview)
    canvas.configure(yscrollcommand=bar.set); canvas.pack(side="left",fill="both",expand=True); bar.pack(side="right",fill="y")
    p=ttk.Frame(canvas,padding=(28,24,28,20)); window=canvas.create_window((0,0),window=p,anchor="nw"); self.page_canvases[name]=canvas
    p.bind("<Configure>",lambda e,c=canvas:c.configure(scrollregion=c.bbox("all")))
    canvas.bind("<Configure>",lambda e,c=canvas,w=window:c.itemconfigure(w,width=e.width))
    ttk.Label(p,text=name.upper(),foreground="#f0a64a",font=("Segoe UI Semibold",9)).pack(anchor="w")
    return p
 def _heading(self,p,title,subtitle):
    ttk.Label(p,text=title,style="Title.TLabel").pack(anchor="w",pady=(5,2))
    ttk.Label(p,text=subtitle,style="Sub.TLabel").pack(anchor="w",pady=(0,18))
 def show_page(self,name):
    for p in self.pages.values(): p.pack_forget()
    self.pages[name].pack(fill="both",expand=True)
    if name=="Drive": self.update_previews(); self.checks()
 def _build_drive(self):
    p=self._page("Drive"); self._heading(p,"Ready for your next run?","Choose a route and train, plan the service, then start OpenBVE.")
    row=ttk.Frame(p); row.pack(fill="x",pady=(0,12)); ttk.Button(row,text="▶   START DUTY IN OPENBVE",style="Accent.TButton",command=self.launch).pack(side="left"); ttk.Button(row,text="Conductor panel",command=self.conductor).pack(side="left",padx=8)
    self.status=tk.StringVar(value="Choose content folders to begin"); ttk.Label(row,textvariable=self.status,style="Sub.TLabel").pack(side="right")
    self.route_hint=tk.StringVar(value="OpenBVE reads the route timetable data")
    top=ttk.Frame(p); top.pack(fill="both",expand=True); top.columnconfigure(0,weight=3); top.columnconfigure(1,weight=2); top.rowconfigure(0,weight=1)
    mapc=self.card(top,manager="grid"); mapc.grid(row=0,column=0,sticky="nsew",padx=(0,10))
    ttk.Label(mapc,text="ROUTE MAP",background="#1b252e",foreground="#f0a64a",font=("Segoe UI Semibold",9)).pack(anchor="w",padx=14,pady=(12,6))
    self.map_preview_image=tk.Label(mapc,text="Choose a route to preview its map",bg="#17222c",fg="#95a9b7",height=8); self.map_preview_image.pack(fill="both",expand=True,padx=12)
    self.map_title=tk.StringVar(value="No route selected"); ttk.Label(mapc,textvariable=self.map_title,background="#1b252e",font=("Segoe UI Semibold",14)).pack(anchor="w",padx=14,pady=(9,1))
    ttk.Label(mapc,textvariable=self.route_hint,style="Muted.TLabel").pack(anchor="w",padx=14,pady=(0,6))
    ttk.Button(mapc,text="Choose map PNG…",command=self.choose_map_preview).pack(anchor="w",padx=14,pady=(0,10))
    tc=self.card(top,manager="grid"); tc.grid(row=0,column=1,sticky="nsew",padx=(10,0))
    ttk.Label(tc,text="YOUR TRAIN",background="#1b252e",foreground="#f0a64a",font=("Segoe UI Semibold",9)).pack(anchor="w",padx=14,pady=(12,6))
    self.train_preview_image=tk.Label(tc,text="Choose a train to preview it",bg="#17222c",fg="#95a9b7",height=8); self.train_preview_image.pack(fill="both",expand=True,padx=12)
    self.train_title=tk.StringVar(value="No train selected"); ttk.Label(tc,textvariable=self.train_title,background="#1b252e",font=("Segoe UI Semibold",14)).pack(anchor="w",padx=14,pady=(9,1))
    ttk.Label(tc,text="PNG preview from the add-on or a selected image",style="Muted.TLabel",wraplength=320).pack(anchor="w",padx=14,pady=(0,6))
    ttk.Button(tc,text="Choose train PNG…",command=self.choose_train_preview).pack(anchor="w",padx=14,pady=(0,10))
    self._heading(p,"Plan this service","Pick a route, train, program and timetable for your run.")
    c=self.card(p); g=ttk.Frame(c,style="Card.TFrame"); g.pack(fill="x",padx=14,pady=10)
    for i in range(2): g.columnconfigure(i,weight=1)
    self.rc=self.field(g,"ROUTE",self.r,0,0,[]); self.tc=self.field(g,"TRAIN",self.t,0,1,[])
    self.rc.bind("<<ComboboxSelected>>",lambda e:self.update_previews()); self.tc.bind("<<ComboboxSelected>>",lambda e:self.update_previews())
    self.field(g,"SERVICE PROGRAM",self.prog,1,0,PROGRAMS); self.schedule_combo=self.field(g,"OPENBVE TIMETABLE",self.sched,1,1,["OpenBVE route default"])
    self.field(g,"RUN DATE",self.day,2,0); self.field(g,"START TIME",self.tmval,2,1)
    ttk.Label(c,text="OpenBVE builds the actual timetable from route data. Date, time and program are saved in your local run card.",style="Muted.TLabel",wraplength=850).pack(anchor="w",padx=16,pady=(0,10))
    row=ttk.Frame(c,style="Card.TFrame"); row.pack(fill="x",padx=14,pady=(0,12))
    ttk.Checkbutton(row,text="Open conductor companion with this run",variable=self.cond).pack(side="left"); ttk.Button(row,text="Save run card",command=self.save).pack(side="right")
 def _build_content(self):
    p=self._page("Content"); self._heading(p,"Your content library","Connect OpenBVE routes and trains. OpenLine scans for compatible files.")
    for label,var,cmd,hint in (("ROUTE LIBRARY",self.rr,self.pick_routes,"Usually the Railway\\Route folder"),("TRAIN LIBRARY",self.tr,self.pick_trains,"Usually the Train folder")):
        c=self.card(p); ttk.Label(c,text=label,background="#1b252e",foreground="#f0a64a",font=("Segoe UI Semibold",9)).pack(anchor="w",padx=14,pady=(12,5))
        row=ttk.Frame(c,style="Card.TFrame"); row.pack(fill="x",padx=12); ttk.Entry(row,textvariable=var).pack(side="left",fill="x",expand=True,padx=(0,8)); ttk.Button(row,text="Browse…",command=cmd).pack(side="right")
        ttk.Label(c,text=hint,style="Muted.TLabel").pack(anchor="w",padx=14,pady=(5,12))
    ttk.Button(p,text="Refresh libraries",command=self.refresh).pack(anchor="w",pady=14)
    self.section(p,"PRE-FLIGHT","OpenLine checks your folders and selected content before launch")
    c=self.card(p); self.tree=ttk.Treeview(c,columns=("state",),show="tree headings",height=7); self.tree.heading("#0",text="CHECK"); self.tree.heading("state",text="STATUS"); self.tree.column("#0",width=310); self.tree.column("state",width=150,anchor="center"); self.tree.pack(fill="x",padx=12,pady=12); ttk.Button(c,text="Run checks now",command=self.checks).pack(anchor="e",padx=12,pady=(0,12))
 def _build_settings(self):
    p=self._page("Settings"); self._heading(p,"Settings & updates","Choose the simulator and manage the OpenLine update channel.")
    c=self.card(p); ttk.Label(c,text="OPENBVE APPLICATION",background="#1b252e",foreground="#f0a64a",font=("Segoe UI Semibold",9)).pack(anchor="w",padx=14,pady=(12,5))
    row=ttk.Frame(c,style="Card.TFrame"); row.pack(fill="x",padx=12); ttk.Entry(row,textvariable=self.ex).pack(side="left",fill="x",expand=True,padx=(0,8)); ttk.Button(row,text="Browse…",command=self.pick_exe).pack(side="right")
    ttk.Label(c,text="Choose OpenBve.exe. The simulator is installed separately.",style="Muted.TLabel").pack(anchor="w",padx=14,pady=6)
    ttk.Button(c,text="Get OpenBVE 1.14.1.2",command=lambda:webbrowser.open("https://github.com/leezer3/OpenBVE/releases/download/1.14.1.2/OpenBVE-1.14.1.2-setup.exe")).pack(anchor="w",padx=14,pady=(0,12))
    u=self.card(p); ttk.Label(u,text="IN-APP UPDATE CHANNEL",background="#1b252e",foreground="#f0a64a",font=("Segoe UI Semibold",9)).pack(anchor="w",padx=14,pady=(12,5)); ttk.Entry(u,textvariable=self.update_feed).pack(fill="x",padx=12)
    self.update_status=tk.StringVar(value="Save a public HTTPS manifest URL to enable updates"); ttk.Label(u,textvariable=self.update_status,style="Muted.TLabel",wraplength=800).pack(anchor="w",padx=14,pady=6)
    row=ttk.Frame(u,style="Card.TFrame"); row.pack(fill="x",padx=12,pady=(0,12)); ttk.Button(row,text="Save channel",command=self.save_update_feed).pack(side="left"); ttk.Button(row,text="Check for updates",command=self.check_updates).pack(side="left",padx=8)
 def _build_multiplayer(self):
    p=self._page("Multiplayer"); self._heading(p,"OpenBVE Multiplayer","Open the multiplayer edition you installed and continue in its built-in multiplayer screen.")
    c=self.card(p); ttk.Label(c,text="INSTALLED MULTIPLAYER APP",background="#1b252e",foreground="#f0a64a",font=("Segoe UI Semibold",9)).pack(anchor="w",padx=14,pady=(12,5))
    row=ttk.Frame(c,style="Card.TFrame"); row.pack(fill="x",padx=12); ttk.Entry(row,textvariable=self.mp_exe).pack(side="left",fill="x",expand=True,padx=(0,8)); ttk.Button(row,text="Browse…",command=self.pick_mp_exe).pack(side="right")
    self.mp_detect_status=tk.StringVar(value=("Multiplayer app detected · "+str(Path(self.mp_exe.get()).parent) if detect_multiplayer_files(self.mp_exe.get()) else "No multiplayer installation detected"))
    ttk.Label(c,textvariable=self.mp_detect_status,style="Muted.TLabel",wraplength=840).pack(anchor="w",padx=14,pady=6)
    row=ttk.Frame(c,style="Card.TFrame"); row.pack(fill="x",padx=12,pady=(2,12)); ttk.Button(row,text="Detect installed build",command=self.detect_mp).pack(side="left"); ttk.Button(row,text="Download multiplayer build",command=lambda:webbrowser.open("https://www.openbvenews.com/downloads/fetch/235")).pack(side="left",padx=8); ttk.Button(row,text="OPEN MULTIPLAYER",style="Accent.TButton",command=self.launch_multiplayer).pack(side="right")
    c=self.card(p); ttk.Label(c,text="WHAT HAPPENS NEXT",background="#1b252e",foreground="#f0a64a",font=("Segoe UI Semibold",9)).pack(anchor="w",padx=14,pady=(12,5))
    ttk.Label(c,text="OpenLine detects the installed OpenBVE Multiplayer app and opens its own start screen. Choose the multiplayer option there to host or join; server discovery and connection are handled by that app. OpenLine does not send made-up server command-line options.",style="Muted.TLabel",wraplength=840,justify="left").pack(anchor="w",padx=16,pady=(0,12))
    c=self.card(p); ttk.Label(c,text="SHARE THIS RUN PLAN",background="#1b252e",foreground="#f0a64a",font=("Segoe UI Semibold",9)).pack(anchor="w",padx=14,pady=(12,5))
    g=ttk.Frame(c,style="Card.TFrame"); g.pack(fill="x",padx=14,pady=(0,10)); g.columnconfigure(0,weight=1); g.columnconfigure(1,weight=1)
    self.field(g,"SESSION LABEL (OPTIONAL)",self.mp_room,0,0); self.field(g,"YOUR NAME (OPTIONAL)",self.mp_name,0,1)
    ttk.Label(c,text="Copy a run-plan note for other players. Select the same route, train, and add-on versions in the multiplayer app before you connect.",style="Muted.TLabel",wraplength=840).pack(anchor="w",padx=16,pady=(0,8))
    ttk.Button(c,text="Copy run plan",command=self.copy_session_card).pack(anchor="e",padx=14,pady=(0,12))
 def pick_mp_exe(self):
    p=filedialog.askopenfilename(title="Choose OpenBVE Multiplayer OpenBve.exe",filetypes=[("OpenBVE","OpenBve.exe"),("Applications","*.exe"),("All files","*.*")])
    if p:self.mp_exe.set(p);self.cfg["mp_exe"]=p;write_cfg(self.cfg);self.mp_detect_status.set("Multiplayer build selected" if detect_multiplayer_files(p) else "Selected file is not a recognized multiplayer installation")
 def detect_mp(self):
    p=detect_multiplayer_exe()
    if p:
        self.mp_exe.set(p);self.cfg["mp_exe"]=p;write_cfg(self.cfg);self.mp_detect_status.set("Detected installed multiplayer build · "+str(Path(p).parent))
    else:self.mp_detect_status.set("No registered multiplayer build found · use Browse or Download")
 def copy_session_card(self):
    route=self.selected(self.r,self.rm); train=self.selected(self.t,self.tm)
    text="OpenLine Desk multiplayer run plan"+chr(10)
    text+=f"Session: {self.mp_room.get().strip() or 'Open run'}"+chr(10)+"Player: "+(self.mp_name.get().strip() or "Not set")+chr(10)
    text+="Route: "+(route.stem if route else "Select route on Drive")+"; Train: "+(train.name if train else "Select train on Drive")
    text+=chr(10)+f"Run: {self.day.get()} at {self.tmval.get()} · {self.sched.get()}"+chr(10)+"Select this same route, train and add-on versions in OpenBVE Multiplayer, then host or join there."
    self.clipboard_clear();self.clipboard_append(text);self.update();messagebox.showinfo("Run plan copied","The run plan is copied. OpenBVE Multiplayer handles hosting and joining.")
 def launch_multiplayer(self):
    r=self.selected(self.r,self.rm);t=self.selected(self.t,self.tm);e=Path(self.mp_exe.get()) if self.mp_exe.get().strip() else None
    if not r or not r.is_file() or not t or not (t/"train.dat").is_file():
        messagebox.showerror("Run not ready","Choose a valid route and train on the Drive page first.");return
    if not e or not e.is_file():
        messagebox.showinfo("Multiplayer build needed","Choose the OpenBVE Multiplayer OpenBve.exe from its installation.");return
    if not detect_multiplayer_files(e):
        messagebox.showerror("Not a multiplayer installation","This folder is missing Multiplayer.dll or Server\Server.exe. Choose the OpenBVE Multiplayer installation, not standard OpenBVE.");return
    self.cfg["mp_exe"]=str(e);write_cfg(self.cfg);self.save(True)
    try:
        subprocess.Popen([str(e)],cwd=str(e.parent))
        self.status.set("OpenBVE Multiplayer launched · continue in its Multiplayer screen")
    except OSError as err:messagebox.showerror("Launch failed",f"Could not start the multiplayer build."+chr(10)+chr(10)+str(err))
 def _build_help(self):
    p=self._page("Help"); self._heading(p,"About OpenLine Desk","A community launcher, run planner, and multiplayer session companion for OpenBVE.")
    c=self.card(p); ttk.Label(c,text="START A RUN",background="#1b252e",foreground="#f0a64a",font=("Segoe UI Semibold",9)).pack(anchor="w",padx=14,pady=(12,5))
    ttk.Label(c,text="Choose folders under Content, return to Drive, pick a route and train, then press Start Duty. Previews use PNGs in add-on folders. Choose a PNG manually if the add-on has no suitable image.",style="Muted.TLabel",wraplength=820,justify="left").pack(anchor="w",padx=14,pady=(0,12))
    c=self.card(p); ttk.Label(c,text="OPENBVE INTEGRATION",background="#1b252e",foreground="#f0a64a",font=("Segoe UI Semibold",9)).pack(anchor="w",padx=14,pady=(12,5))
    ttk.Label(c,text="OpenLine starts OpenBVE with the selected route and train. Add-ons determine the timetable and program options supported by the simulator. Run date and time are saved on the run card; the conductor companion is a separate helper panel.",style="Muted.TLabel",wraplength=820,justify="left").pack(anchor="w",padx=14,pady=(0,12))
    ttk.Label(p,text="OpenLine Desk "+VERSION+"  ·  OpenBVE is a separate project",style="Sub.TLabel").pack(anchor="w",pady=16)
 def _image_for(self,widget,path,label):
    if not path or not Path(path).is_file():
        widget.configure(image="",text=label); widget.image=None; return
    try:
        image=tk.PhotoImage(file=str(path)); step=max(1,(image.width()+319)//320,(image.height()+169)//170)
        if step>1:image=image.subsample(step,step)
        widget.configure(image=image,text=""); widget.image=image
    except (tk.TclError,OSError):
        widget.configure(image="",text="Preview PNG could not be read"); widget.image=None
 def _train_preview_file(self,train):
    if not train:return None
    chosen=self.cfg.get("train_preview_overrides",{}).get(str(train))
    if chosen and Path(chosen).is_file():return Path(chosen)
    for name in ("preview.png","thumbnail.png","train.png","vehicle.png","image.png"):
        p=train/name
        if p.is_file():return p
    for p in sorted(train.rglob("*.png"),key=lambda x:str(x).lower()):
        if any(k in p.name.lower() for k in ("preview","thumbnail","vehicle","train")) and not any(k in p.name.lower() for k in ("panel","door","interior")):return p
    return None
 def _map_preview_file(self,route):
    if not route:return None
    chosen=self.cfg.get("map_preview_overrides",{}).get(str(route))
    if chosen and Path(chosen).is_file():return Path(chosen)
    try:lines=route.read_text(encoding="utf-8-sig",errors="ignore").splitlines()
    except OSError:lines=[]
    for line in lines:
        m=re.match(r"\s*Route\.Image\s*(?:,|\s)\s*\(?([^\s,)]+)",line,re.I)
        if not m and route.suffix.lower()==".rw":m=re.match(r"\s*Image\s*=\s*([^\s;]+)",line,re.I)
        if m:
            relpath=m.group(1).strip().strip('"').strip("'")
            for base in (route.parent,Path(self.rr.get()),Path(self.rr.get()).parent):
                candidate=(base/relpath).resolve()
                if candidate.is_file() and candidate.suffix.lower()==".png":return candidate
    for candidate in route.parent.glob("*.png"):
        if any(k in candidate.name.lower() for k in ("map","route","preview","line")):return candidate
    return None
 def _timetable_choices(self,route):
    found={}
    if route and route.is_file():
        try:lines=route.read_text(encoding="utf-8-sig",errors="ignore").splitlines()
        except OSError:lines=[]
        for line in lines:
            m=re.search(r'(?:Train\.)?Timetable\s*\(\s*(\d+)\s*\)\.(Day|Night)(?:\.Load)?\s*(?:=|,|\s)\s*\(?([A-Za-z0-9_.\\/-]+)',line,re.I)
            if m:found.setdefault(m.group(1),set()).add(m.group(2).title()+" · "+Path(m.group(3)).name)
    choices=["OpenBVE route default"]
    for index,variants in sorted(found.items(),key=lambda item:int(item[0])):
        for variant in sorted(variants):choices.append("OpenBVE timetable "+index+" · "+variant)
    self.schedule_combo.configure(values=choices)
    if self.sched.get() not in choices:self.sched.set(choices[0])
 def update_previews(self):
    train=self.selected(self.t,self.tm); route=self.selected(self.r,self.rm)
    self._image_for(self.train_preview_image,self._train_preview_file(train),"No train PNG found\nUse Choose PNG to set one")
    self._image_for(self.map_preview_image,self._map_preview_file(route),"No route map PNG found\nChoose one or use Route.Image")
    self.train_title.set(train.name if train else "No train selected")
    self.map_title.set(route.stem if route else "No route selected")
    self.route_hint.set(str(route.parent) if route else "OpenBVE reads the route timetable data")
    self._timetable_choices(route)
 def _choose_preview(self,kind):
    selected=self.selected(self.t,self.tm) if kind=="train" else self.selected(self.r,self.rm)
    if not selected:messagebox.showinfo("Select a "+kind,"Select a "+kind+" first.");return
    image=filedialog.askopenfilename(title="Choose a PNG preview",filetypes=[("PNG images","*.png")])
    if not image:return
    key="train_preview_overrides" if kind=="train" else "map_preview_overrides"
    overrides=self.cfg.setdefault(key,{ });overrides[str(selected)]=image;write_cfg(self.cfg);self.update_previews()
 def choose_train_preview(self):self._choose_preview("train")
 def choose_map_preview(self):self._choose_preview("map")
 def field(self,p,label,var,row,col,values=None):
    x=ttk.Frame(p,style="Card.TFrame"); x.grid(row=row,column=col,sticky="ew",padx=(0 if col==0 else 12,8),pady=6); ttk.Label(x,text=label,background="#1b252e",foreground="#93a5b4",font=("Segoe UI Semibold",8)).pack(anchor="w",pady=(0,4)); w=ttk.Combobox(x,textvariable=var,values=values,state=("readonly" if values else "normal")) if values is not None else ttk.Entry(x,textvariable=var); w.pack(fill="x"); return w
 def pick_routes(self):
    p=filedialog.askdirectory(title="Choose Railway\\Route folder")
    if p:self.rr.set(p);self.refresh()
 def pick_trains(self):
    p=filedialog.askdirectory(title="Choose Train folder")
    if p:self.tr.set(p);self.refresh()
 def pick_exe(self):
    p=filedialog.askopenfilename(title="Choose OpenBve.exe",filetypes=[("OpenBVE","OpenBve.exe"),("Applications","*.exe"),("All files","*.*")])
    if p:self.ex.set(p);self.persist()
 def persist(self): write_cfg({**self.cfg,"route_root":self.rr.get(),"train_root":self.tr.get(),"exe":self.ex.get()})
 def refresh(self):
    self.routes=files(self.rr.get(),{".csv",".rw"}); self.trainlist=trains(self.tr.get()); self.rm={rel(x,self.rr.get()):x for x in self.routes}; self.tm={rel(x,self.tr.get()):x for x in self.trainlist}
    self.rc.configure(values=list(self.rm));self.tc.configure(values=list(self.tm));self.persist()
    if self.routes and not self.r.get():self.r.set(next(iter(self.rm)))
    if self.trainlist and not self.t.get():self.t.set(next(iter(self.tm)))
    self.update_previews();self.checks()
 def selected(self,value,mapping):
    v=value.get().strip(); return mapping.get(v,Path(v) if v else None)
 def checks(self):
    if not hasattr(self,"tree"):return
    for x in self.tree.get_children():self.tree.delete(x)
    r=self.selected(self.r,self.rm);t=self.selected(self.t,self.tm);e=Path(self.ex.get()) if self.ex.get() else None
    rows=[("Route library","FOUND" if self.routes else ("SET FOLDER" if not self.rr.get().strip() or not Path(self.rr.get()).is_dir() else "NO ROUTES")),("Train library","FOUND" if self.trainlist else ("SET FOLDER" if not self.tr.get().strip() or not Path(self.tr.get()).is_dir() else "NO TRAINS")),("Selected route","READY" if r and r.is_file() and r.suffix.lower() in (".csv",".rw") else "SELECT ROUTE"),("Selected train","READY" if t and (t/"train.dat").is_file() else "SELECT TRAIN"),("OpenBVE app","READY" if e and e.is_file() else ("CHOOSE APP" if not self.ex.get() else "NOT FOUND"))]
    bad=0
    for n,v in rows:
        self.tree.insert("","end",text=n,values=(v,))
        if v in ("SET FOLDER","NO ROUTES","NO TRAINS","SELECT ROUTE","SELECT TRAIN","CHOOSE APP","NOT FOUND"):bad+=1
    self.status.set("Pre-flight looks good · Ready to launch" if not bad else f"{bad} item(s) need attention")
 def launch(self):
    self.update_previews();self.checks();r=self.selected(self.r,self.rm);t=self.selected(self.t,self.tm)
    if not r or not r.is_file() or r.suffix.lower() not in (".csv",".rw"):messagebox.showerror("Route needed","Choose a route CSV/RW or set the Railway\\Route folder.");return
    if not t or not (t/"train.dat").is_file():messagebox.showerror("Train needed","Choose a train folder containing train.dat.");return
    e=Path(self.ex.get()) if self.ex.get() else None
    if not e or not e.is_file():messagebox.showinfo("Choose OpenBVE","Select your OpenBve.exe.");self.pick_exe();e=Path(self.ex.get()) if self.ex.get() else None
    if not e or not e.is_file():return
    self.save(True)
    try:subprocess.Popen([str(e),f"/route={r}",f"/train={t}"],cwd=str(e.parent))
    except OSError as err:messagebox.showerror("Launch failed",f"OpenBVE could not be started.\n\n{err}");return
    self.status.set("OpenBVE launched · Run card saved")
    if self.cond.get():self.after(800,self.conductor)
 def save(self,silent=False):
    card={"route":str(self.selected(self.r,self.rm) or ""),"train":str(self.selected(self.t,self.tm) or ""),"program":self.prog.get(),"date":self.day.get(),"start_time":self.tmval.get(),"schedule":self.sched.get(),"conductor_companion":self.cond.get(),"saved_at":datetime.now().isoformat(timespec="seconds")}
    self.persist();write_cfg({**self.cfg,"route_root":self.rr.get(),"train_root":self.tr.get(),"exe":self.ex.get(),"last_run":card});self.cfg["last_run"]=card;self.status.set("Run card saved locally")
    if not silent:messagebox.showinfo("Run card saved",f"Saved to {CFG}")
 def save_update_feed(self):
    url=self.update_feed.get().strip()
    if url and not url.startswith("https://"):
        messagebox.showerror("HTTPS required","Update manifests must use an HTTPS URL.");return
    self.cfg["update_feed"]=url;write_cfg(self.cfg);self.update_status.set("Update channel saved" if url else "Update channel cleared")
 def check_updates(self):
    url=self.update_feed.get().strip()
    if not url or not url.startswith("https://"):
        messagebox.showinfo("Update channel needed","To receive updates without another ZIP, this app needs the public HTTPS URL of its release manifest. Save it here after the release channel is hosted.");return
    self.save_update_feed();self.update_status.set("Checking release channel…")
    threading.Thread(target=self._fetch_manifest,args=(url,),daemon=True).start()
 def _fetch_manifest(self,url):
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"OpenLineDesk-Updater/0.3.1"})
        with urllib.request.urlopen(req,timeout=15) as response: data=json.loads(response.read(100000).decode("utf-8"))
        version=str(data.get("version","")); asset=str(data.get("asset_url","")); digest=str(data.get("sha256",""))
        nums=lambda v: tuple(int(x) for x in re.findall(r"\d+",v))
        if not re.fullmatch(r"\d+\.\d+\.\d+",version) or not asset.startswith("https://") or not re.fullmatch(r"[0-9a-fA-F]{64}",digest): raise ValueError("The manifest must contain version, HTTPS asset_url, and SHA-256 fields.")
        if nums(version)<=nums(VERSION): self.after(0,lambda:self.update_status.set(f"You're up to date · {VERSION}"));return
        self.after(0,self._offer_update,version,asset,digest)
    except Exception as e:self.after(0,lambda err=e:self.update_status.set(f"Update check failed: {err}"))
 def _offer_update(self,version,asset,digest):
    if messagebox.askyesno("Update available",f"OpenLine Desk {version} is available. Download and install it now? The update replaces only the app script."):
        self.update_status.set(f"Downloading {version}…");threading.Thread(target=self._download_update,args=(version,asset,digest),daemon=True).start()
    else:self.update_status.set(f"Update {version} is available")
 def _download_update(self,version,asset,digest):
    try:
        with urllib.request.urlopen(urllib.request.Request(asset,headers={"User-Agent":"OpenLineDesk-Updater/0.3.1"}),timeout=30) as response: payload=response.read(10_000_001)
        if len(payload)>10_000_000: raise ValueError("Update script is larger than the 10 MB safety limit.")
        if hashlib.sha256(payload).hexdigest().lower()!=digest.lower(): raise ValueError("The downloaded update did not match its SHA-256 checksum.")
        candidate=payload.decode("utf-8-sig")
        if f'VERSION = "{version}"' not in candidate: raise ValueError("The update version did not match its manifest.")
        target=Path(__file__).resolve(); staged=target.with_name(target.name+".new"); helper=target.with_name("apply-openline-update.cmd")
        staged.write_bytes(payload)
        q=lambda x:'"'+str(x).replace('"','')+'"'
        pid=os.getpid(); lines=["@echo off","setlocal",f"set WAITPID={pid}",":wait",'tasklist /FI "PID eq %WAITPID%" | find "%WAITPID%" >nul','if not errorlevel 1 (timeout /t 1 /nobreak >nul & goto wait)',f"move /Y {q(staged)} {q(target)} >nul","if errorlevel 1 exit /b 1",f"start \"\" {q(sys.executable)} {q(target)}",'del "%~f0"']; helper.write_text("\r\n".join(lines)+"\r\n",encoding="utf-8")
        subprocess.Popen(["cmd.exe","/c","start","","/min",str(helper)],creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        self.after(0,lambda:self.update_status.set(f"Installing {version} · restarting OpenLine…"));self.after(500,self.destroy)
    except Exception as e:self.after(0,lambda err=e:self.update_status.set(f"Update failed: {err}"))
 def conductor(self):Conductor(self,self.selected(self.r,self.rm))

class Conductor(tk.Toplevel):
 def __init__(self,master,route):
    super().__init__(master);self.title("OpenLine · Conductor desk");self.geometry("540x630");self.stops=self.get_stops(route);self.i=0
    f=ttk.Frame(self,padding=20);f.pack(fill="both",expand=True);ttk.Label(f,text="CONDUCTOR COMPANION",foreground="#f0a64a",font=("Segoe UI Semibold",9)).pack(anchor="w");ttk.Label(f,text="Platform & onboard duties",style="Title.TLabel").pack(anchor="w",pady=5)
    ttk.Label(f,text="Station calls, platform checks and a run log. This sidecar cannot operate OpenBVE in-game doors or cameras.",style="Sub.TLabel",wraplength=500).pack(anchor="w",pady=(0,12))
    c=ttk.Frame(f,style="Card.TFrame");c.pack(fill="x");self.name=tk.StringVar(value=self.stops[0] if self.stops else "Add a station below");ttk.Label(c,text="CURRENT STOP",style="Muted.TLabel").pack(anchor="w",padx=14,pady=(12,3));ttk.Label(c,textvariable=self.name,background="#1b252e",foreground="#f2bd66",font=("Segoe UI Semibold",21)).pack(anchor="w",padx=14,pady=(0,12))
    row=ttk.Frame(f);row.pack(fill="x",pady=10);ttk.Button(row,text="‹ Previous",command=self.prev).pack(side="left");ttk.Button(row,text="Next stop ›",command=self.next).pack(side="left",padx=6);ttk.Button(row,text="Announce stop",style="Accent.TButton",command=self.announce).pack(side="right")
    c=ttk.Frame(f,style="Card.TFrame");c.pack(fill="x");self.checked=tk.BooleanVar();ttk.Label(c,text="PLATFORM CHECK",foreground="#edf4f7",background="#1b252e").pack(anchor="w",padx=14,pady=(11,5));ttk.Checkbutton(c,text="Platform and train sides checked",variable=self.checked).pack(anchor="w",padx=14,pady=4);row=ttk.Frame(c,style="Card.TFrame");row.pack(fill="x",padx=14,pady=10);ttk.Button(row,text="Doors clear · close up",command=self.close).pack(side="left");ttk.Button(row,text="Depart",command=self.depart).pack(side="left",padx=6)
    ttk.Label(f,text="STATION LIST · one per line",style="Muted.TLabel").pack(anchor="w",pady=(12,4));self.txt=tk.Text(f,height=6,bg="#0c141d",fg="#e8eef3",insertbackground="#e8eef3",relief="flat");self.txt.pack(fill="x");self.txt.insert("1.0","\n".join(self.stops));ttk.Button(f,text="Update station list",command=self.update).pack(anchor="e",pady=6)
    ttk.Label(f,text="ACTIVITY LOG",style="Muted.TLabel").pack(anchor="w");self.log=tk.Listbox(f,height=5,bg="#0c141d",fg="#c4d1d9",relief="flat",font=("Consolas",9));self.log.pack(fill="both",expand=True)
 def get_stops(self,r):
    if not r or not r.is_file():return []
    try:data=r.read_text(encoding="utf-8-sig",errors="ignore")
    except OSError:return []
    out=[]
    for line in data.splitlines():
        m=re.match(r"\s*Station\s*\.\s*Name\s*\[?\d*\]?\s*,\s*(.+)",line,re.I)
        if m:
            n=m.group(1).strip().strip('"')
            if n and n not in out:out.append(n)
    return out[:80]
 def logit(self,s):self.log.insert("end",f"{datetime.now():%H:%M:%S}  {s}");self.log.see("end")
 def update(self):
    self.stops=[x.strip() for x in self.txt.get("1.0","end").splitlines() if x.strip()];self.i=min(self.i,max(0,len(self.stops)-1));self.show();self.logit(f"Station list updated ({len(self.stops)})")
 def show(self):self.name.set(self.stops[self.i] if self.stops else "Add a station below")
 def prev(self):
    if self.stops:self.i=max(0,self.i-1);self.show()
 def next(self):
    if self.stops:self.i=min(len(self.stops)-1,self.i+1);self.show()
 def announce(self):
    if not self.stops:messagebox.showinfo("Station list is empty","Add stations below.",parent=self);return
    n=self.name.get();self.logit(f"Announcement: {n}")
    if sys.platform=="win32":
        phrase=f"This train is now arriving at {n}. Please mind the platform gap and take all personal belongings with you.".replace("'","''")
        cmd=f"Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak('{phrase}')"
        try:subprocess.Popen(["powershell","-NoProfile","-WindowStyle","Hidden","-Command",cmd],creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        except OSError:pass
 def close(self):
    if not self.checked.get():messagebox.showwarning("Check the platform","Mark the platform and train sides checked first.",parent=self);return
    self.logit("Doors clear · close-up completed")
 def depart(self):
    if not self.checked.get():messagebox.showwarning("Check the platform","Mark the platform and train sides checked first.",parent=self);return
    self.logit("Departure confirmed · "+self.name.get())
    if self.i<len(self.stops)-1:self.i+=1;self.show()

if __name__=="__main__":Desk().mainloop()






























