#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube İndirici — Windows Masaüstü Uygulaması
Karanlık tema, ses+video birleştirme (HD), MP3 desteği
"""

import os, re, shutil, subprocess, threading, tempfile, ssl, sys
import tkinter as tk
from tkinter import filedialog, messagebox

# Windows'ta ffmpeg/komut penceresi açılmasın
CREATE_NO_WINDOW = 0x08000000
SUBPROCESS_FLAGS = CREATE_NO_WINDOW if sys.platform == "win32" else 0

# certifi — SSL düzeltmesi
try:
    import certifi
    os.environ["SSL_CERT_FILE"] = certifi.where()
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
    ssl._create_default_https_context = ssl.create_default_context
except ImportError:
    pass

try:
    from pytubefix import YouTube
except ImportError:
    try:
        from pytube import YouTube
    except ImportError:
        YouTube = None

# ---------- Yardımcılar ----------
def ffmpeg_bul():
    # 1) PyInstaller paketi: _MEIPASS geçici klasörü
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        aday = os.path.join(meipass, "ffmpeg.exe")
        if os.path.exists(aday):
            return aday
        # exe ile aynı klasör
        aday2 = os.path.join(os.path.dirname(sys.executable), "ffmpeg.exe")
        if os.path.exists(aday2):
            return aday2
    # 2) PATH'te var mı?
    f = shutil.which("ffmpeg")
    if f: return f
    # 3) Script olarak çalışıyorsa yanındaki ffmpeg.exe
    kendi = os.path.dirname(os.path.abspath(__file__))
    aday = os.path.join(kendi, "ffmpeg.exe")
    if os.path.exists(aday): return aday
    # 4) Bilinen Windows konumları
    for p in [r"C:\ffmpeg\bin\ffmpeg.exe",
              os.path.expandvars(r"%LOCALAPPDATA%\ffmpeg\bin\ffmpeg.exe")]:
        if os.path.exists(p): return p
    return None

FFMPEG = ffmpeg_bul()

URL_RE = re.compile(
    r"(https?://)?(www\.|m\.|music\.)?"
    r"(youtube\.com/(watch\?v=|shorts/|live/)|youtu\.be/)[\w\-]{6,}"
)

def gecerli(url): return bool(URL_RE.search(url or ""))
def temiz_ad(ad):
    ad = re.sub(r'[\\/:*?"<>|]+', "", ad or "").strip()
    return ad[:120] or "video"
def sure(s):
    if not s: return "—"
    s=int(s); dk=s//60; sa=dk//60; dk=dk%60; s=s%60
    return f"{sa}:{dk:02d}:{s:02d}" if sa else f"{dk}:{s:02d}"

# ---------- Renkler ----------
BG      = "#0f0f0f"
PANEL   = "#1a1a1a"
BORDER  = "#2a2a2a"
ACCENT  = "#ff4444"
ACCENT2 = "#cc2222"
FG      = "#f0f0f0"
MUTED   = "#888888"
SUCCESS = "#22cc66"
FONT    = "Segoe UI"
MONO    = "Consolas"

# ---------- Özel widget'lar ----------
class FlatButton(tk.Label):
    def __init__(self, parent, text, command, bg=ACCENT, fg="#fff",
                 font_size=13, pad_x=24, pad_y=10, **kw):
        super().__init__(parent, text=text, bg=bg, fg=fg,
                         font=(FONT, font_size, "bold"),
                         padx=pad_x, pady=pad_y, cursor="hand2", **kw)
        self._cmd=command; self._bg=bg
        self._hover = ACCENT2 if bg==ACCENT else "#2e2e2e"
        self.bind("<Button-1>", lambda e: command())
        self.bind("<Enter>",    lambda e: self.config(bg=self._hover))
        self.bind("<Leave>",    lambda e: self.config(bg=self._bg))

class ModernEntry(tk.Frame):
    def __init__(self, parent, placeholder="", **kw):
        super().__init__(parent, bg=PANEL)
        self._ph=placeholder; self._ph_aktif=True
        self.var=tk.StringVar()
        self.entry=tk.Entry(self, textvariable=self.var, bg=PANEL, fg=MUTED,
                            insertbackground=FG, relief="flat",
                            font=(MONO,12), bd=0, **kw)
        self.entry.pack(fill="x")
        self.cizgi=tk.Frame(self, bg=BORDER, height=1)
        self.cizgi.pack(fill="x", pady=(4,0))
        self.entry.insert(0, placeholder)
        self.entry.bind("<FocusIn>",  self._on)
        self.entry.bind("<FocusOut>", self._off)

    def _on(self, e):
        self.cizgi.config(bg=ACCENT)
        if self._ph_aktif:
            self.entry.delete(0,"end"); self.entry.config(fg=FG)
            self._ph_aktif=False

    def _off(self, e):
        self.cizgi.config(bg=BORDER)
        if not self.entry.get():
            self.entry.insert(0,self._ph); self.entry.config(fg=MUTED)
            self._ph_aktif=True

    def get(self):
        return "" if self._ph_aktif else self.var.get().strip()

class ModernProgress(tk.Canvas):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BORDER, height=3,
                         highlightthickness=0, **kw)
        self._y=0; self.bind("<Configure>", self._ciz)

    def set(self, y):
        self._y=max(0,min(100,y)); self._ciz()

    def _ciz(self, e=None):
        self.delete("all")
        w=self.winfo_width()
        if w>1 and self._y>0:
            self.create_rectangle(0,0,w*self._y/100,3,fill=ACCENT,outline="")

# ---------- Ana uygulama ----------
class App:
    def __init__(self, root: tk.Tk):
        self.root=root; self.yt=None
        self.kaliteler=[]; self.hedef=os.path.expanduser("~\\Downloads")
        self.mesgul=False

        root.title("YouTube İndirici")
        root.geometry("560x600")
        root.resizable(False,False)
        root.configure(bg=BG)

        # Windows görev çubuğu simgesi ve karanlık başlık çubuğu
        try:
            root.iconbitmap(default="icon.ico")
        except Exception:
            pass
        try:
            root.tk.call("tk::unsupported::MacWindowStyle","style",root._w,"moveableModal","")
        except Exception:
            pass
        # Windows 10/11 karanlık başlık çubuğu
        try:
            import ctypes
            HWND = ctypes.windll.user32.GetParent(root.winfo_id())
            ctypes.windll.dwmapi.DwmSetWindowAttribute(HWND, 20, ctypes.byref(ctypes.c_int(1)), 4)
        except Exception:
            pass

        self._ui()
        if YouTube is None:
            self._durum("pytubefix bulunamadı — yeniden kurun.", ACCENT)

    def _ui(self):
        pad=dict(padx=28)

        tk.Frame(self.root,bg=BG,height=28).pack()

        # Başlık
        hdr=tk.Frame(self.root,bg=BG)
        hdr.pack(fill="x",**pad)
        tk.Label(hdr,text="▶",bg=BG,fg=ACCENT,font=(FONT,26,"bold")).pack(side="left")
        ttl=tk.Frame(hdr,bg=BG)
        ttl.pack(side="left",padx=(10,0))
        tk.Label(ttl,text="YouTube İndirici",bg=BG,fg=FG,
                 font=(FONT,19,"bold")).pack(anchor="w")
        tk.Label(ttl,text="MP3 · MP4 — bilgisayarına kaydet",
                 bg=BG,fg=MUTED,font=(FONT,11)).pack(anchor="w")

        tk.Frame(self.root,bg=BG,height=22).pack()

        # URL
        ub=tk.Frame(self.root,bg=BG)
        ub.pack(fill="x",**pad)
        tk.Label(ub,text="Bağlantı",bg=BG,fg=MUTED,font=(FONT,9)).pack(anchor="w")
        tk.Frame(ub,bg=BG,height=5).pack()
        us=tk.Frame(ub,bg=BG)
        us.pack(fill="x")
        self.url_e=ModernEntry(us, placeholder="https://www.youtube.com/watch?v=…")
        self.url_e.pack(side="left",fill="x",expand=True)
        self.url_e.entry.bind("<Return>", lambda e: self._getir())
        tk.Frame(us,bg=BG,width=12).pack(side="left")
        self.btn_getir=FlatButton(us,"Getir",self._getir,font_size=11,pad_x=16,pad_y=7)
        self.btn_getir.pack(side="left")

        tk.Frame(self.root,bg=BG,height=20).pack()

        # Video kartı
        kw=tk.Frame(self.root,bg=BG)
        kw.pack(fill="x",**pad)
        self.kart=tk.Frame(kw,bg=PANEL)
        self.kart.pack(fill="x")
        tk.Frame(self.kart,bg=ACCENT,width=4).pack(side="left",fill="y")
        ki=tk.Frame(self.kart,bg=PANEL)
        ki.pack(side="left",fill="both",expand=True,padx=14,pady=12)
        self.lbl_baslik=tk.Label(ki,text="—  video bekleniyor",bg=PANEL,fg=FG,
                                  font=(FONT,12,"bold"),anchor="w",
                                  wraplength=430,justify="left")
        self.lbl_baslik.pack(anchor="w")
        self.lbl_meta=tk.Label(ki,text="",bg=PANEL,fg=MUTED,font=(FONT,10),anchor="w")
        self.lbl_meta.pack(anchor="w",pady=(3,0))

        tk.Frame(self.root,bg=BG,height=18).pack()

        # Biçim & çözünürlük
        sec=tk.Frame(self.root,bg=BG)
        sec.pack(fill="x",**pad)
        tk.Label(sec,text="Biçim",bg=BG,fg=MUTED,font=(FONT,9)).grid(row=0,column=0,sticky="w")
        tk.Label(sec,text="Çözünürlük",bg=BG,fg=MUTED,font=(FONT,9)).grid(row=0,column=1,sticky="w",padx=(24,0))

        self.bicim_var=tk.StringVar(value="mp4")
        bf=tk.Frame(sec,bg=BG)
        bf.grid(row=1,column=0,sticky="w",pady=(5,0))
        for val,txt in [("mp4","📹  MP4"),("mp3","🎵  MP3")]:
            tk.Radiobutton(bf,text=txt,value=val,variable=self.bicim_var,
                           command=self._bicim_degisti,bg=BG,fg=FG,
                           selectcolor=BG,activebackground=BG,
                           activeforeground=ACCENT,font=(FONT,12),
                           cursor="hand2").pack(side="left",padx=(0,14))

        kf=tk.Frame(sec,bg=BG)
        kf.grid(row=1,column=1,sticky="w",padx=(24,0),pady=(5,0))
        self.kalite_var=tk.StringVar()
        self.kalite_menu=tk.OptionMenu(kf,self.kalite_var,"—")
        self.kalite_menu.config(bg=PANEL,fg=FG,activebackground=BORDER,
                                activeforeground=FG,font=(FONT,11),
                                relief="flat",bd=0,highlightthickness=0,
                                cursor="hand2")
        self.kalite_menu["menu"].config(bg=PANEL,fg=FG,
                                        activebackground=ACCENT,
                                        activeforeground="#fff",font=(FONT,11))
        self.kalite_menu.pack()

        tk.Frame(self.root,bg=BG,height=14).pack()

        # Kayıt yeri
        ks=tk.Frame(self.root,bg=BG)
        ks.pack(fill="x",**pad)
        tk.Label(ks,text="Kayıt:",bg=BG,fg=MUTED,font=(FONT,10)).pack(side="left")
        self.lbl_klasor=tk.Label(ks,text=self._kis(self.hedef),
                                  bg=BG,fg=MUTED,font=(MONO,10))
        self.lbl_klasor.pack(side="left",padx=(8,12))
        deg=tk.Label(ks,text="Değiştir →",bg=BG,fg=ACCENT,font=(FONT,10),cursor="hand2")
        deg.pack(side="left")
        deg.bind("<Button-1>", lambda e: self._klasor())

        tk.Frame(self.root,bg=BG,height=18).pack()

        # İndir butonu
        bw=tk.Frame(self.root,bg=BG)
        bw.pack(fill="x",**pad)
        self.btn_indir=FlatButton(bw,"⬇  İndir",self._indir,
                                   pad_x=0,pad_y=11,font_size=13)
        self.btn_indir.pack(fill="x")

        tk.Frame(self.root,bg=BG,height=12).pack()

        # İlerleme
        self.progress=ModernProgress(self.root)
        self.progress.pack(fill="x",padx=28)

        tk.Frame(self.root,bg=BG,height=10).pack()

        ffmpeg_durum = "Hazır." if FFMPEG else "Hazır · ffmpeg bulunamadı (m4a inecek, HD birleştirilmeyecek)."
        self.lbl_durum=tk.Label(self.root,text=ffmpeg_durum,
                                 bg=BG,fg=MUTED,font=(FONT,10))
        self.lbl_durum.pack(**pad,anchor="w")

        self._bicim_degisti()

    def _kis(self, y):
        ev=os.path.expanduser("~")
        return y.replace(ev,"~") if y.startswith(ev) else y

    def _durum(self,m,r=MUTED): self.lbl_durum.config(text=m,fg=r)

    def _kilit(self,k):
        self.mesgul=k
        r="#444" if k else ACCENT
        self.btn_getir.config(bg=r,cursor="watch" if k else "hand2")
        self.btn_indir.config(bg=r,cursor="watch" if k else "hand2")

    def _bicim_degisti(self):
        mp4=self.bicim_var.get()=="mp4"
        self.kalite_menu.config(state="normal" if (mp4 and self.kaliteler) else "disabled")
        self.btn_indir.config(text="⬇  MP4 indir" if mp4 else "⬇  MP3 indir")

    def _klasor(self):
        y=filedialog.askdirectory(initialdir=self.hedef)
        if y: self.hedef=y; self.lbl_klasor.config(text=self._kis(y))

    # ---- Bilgi getir ----
    def _getir(self):
        if self.mesgul: return
        url=self.url_e.get()
        if not gecerli(url):
            messagebox.showwarning("Geçersiz","Lütfen geçerli bir YouTube bağlantısı girin.")
            return
        self._kilit(True); self._durum("Video bilgisi alınıyor…")
        threading.Thread(target=self._getir_is,args=(url,),daemon=True).start()

    def _getir_is(self,url):
        try:
            yt=YouTube(url,on_progress_callback=self._progress_cb)
            adapt=list(yt.streams.filter(adaptive=True,file_extension="mp4",only_video=True)
                       .order_by("resolution").desc())
            prog=list(yt.streams.filter(progressive=True,file_extension="mp4")
                      .order_by("resolution").desc())
            kal,grd=[],set()
            for s in adapt+prog:
                if s.resolution and s.resolution not in grd:
                    grd.add(s.resolution)
                    mb=round(s.filesize/1_048_576,1) if s.filesize else None
                    tip="HD" if s.is_adaptive else "SD"
                    et=f"{s.resolution}  ·  {tip}"+(f"  ·  {mb} MB" if mb else "")
                    kal.append((s.itag,s.resolution,et,s.is_adaptive))
            self.root.after(0,self._getir_yaz,yt,kal)
        except Exception as e:
            self.root.after(0,self._getir_hata,str(e))

    def _getir_yaz(self,yt,kal):
        self.yt=yt; self.kaliteler=kal
        self.lbl_baslik.config(text=yt.title)
        self.lbl_meta.config(text=f"{yt.author}  ·  {sure(yt.length)}")
        m=self.kalite_menu["menu"]; m.delete(0,"end")
        for itag,coz,et,ad in kal:
            m.add_command(label=et,command=lambda v=et: self.kalite_var.set(v))
        if kal: self.kalite_var.set(kal[0][2])
        self._bicim_degisti()
        self._durum("Hazır — biçim seçip İndir'e bas.",SUCCESS)
        self._kilit(False)

    def _getir_hata(self,msg):
        self._kilit(False); self._durum("Bilgi alınamadı.",ACCENT)
        messagebox.showerror("Hata",f"Video bilgisi alınamadı:\n\n{msg}")

    def _progress_cb(self,stream,chunk,kalan):
        t=stream.filesize or 1
        self.root.after(0,self.progress.set,(t-kalan)/t*100)

    # ---- İndir ----
    def _indir(self):
        if self.mesgul: return
        if not self.yt:
            messagebox.showinfo("Önce getir","Önce bir bağlantı yapıştırıp Getir'e bas.")
            return
        self._kilit(True); self.progress.set(0)
        bicim=self.bicim_var.get()
        et=self.kalite_var.get()
        sec=next(((i,a) for i,_,e,a in self.kaliteler if e==et),(None,False))
        itag,adaptive=sec
        self._durum("İndiriliyor…")
        threading.Thread(target=self._indir_is,args=(bicim,itag,adaptive),daemon=True).start()

    def _indir_is(self,bicim,itag,adaptive):
        gecici=[]
        try:
            ad=temiz_ad(self.yt.title)
            if bicim=="mp3":
                ak=self.yt.streams.filter(only_audio=True).order_by("abr").desc().first()
                if not ak: raise RuntimeError("Ses akışı bulunamadı.")
                ham=ak.download(output_path=tempfile.gettempdir(),
                                filename=f"_ses_{os.getpid()}")
                gecici.append(ham)
                if FFMPEG:
                    hedef=os.path.join(self.hedef,f"{ad}.mp3")
                    self.root.after(0,lambda: self._durum("MP3'e dönüştürülüyor…"))
                    subprocess.run([FFMPEG,"-y","-i",ham,"-vn",
                                    "-codec:a","libmp3lame","-q:a","2",hedef],
                                   check=True, capture_output=True,
                                   creationflags=SUBPROCESS_FLAGS)
                    son=hedef
                else:
                    son=os.path.join(self.hedef,f"{ad}.m4a")
                    shutil.move(ham,son); gecici.clear()
            else:
                ak=(self.yt.streams.get_by_itag(int(itag)) if itag
                    else self.yt.streams.get_highest_resolution())
                if not ak: raise RuntimeError("Video akışı bulunamadı.")
                if adaptive and FFMPEG:
                    self.root.after(0,lambda: self._durum("Video indiriliyor… (HD)"))
                    vp=ak.download(output_path=tempfile.gettempdir(),
                                   filename=f"_vid_{os.getpid()}")
                    gecici.append(vp)
                    sa=self.yt.streams.filter(only_audio=True).order_by("abr").desc().first()
                    self.root.after(0,lambda: self._durum("Ses indiriliyor…"))
                    sp=sa.download(output_path=tempfile.gettempdir(),
                                   filename=f"_ses_{os.getpid()}")
                    gecici.append(sp)
                    son=os.path.join(self.hedef,f"{ad}.mp4")
                    self.root.after(0,lambda: self._durum("Birleştiriliyor… (bu biraz sürebilir)"))
                    result = subprocess.run(
                        [FFMPEG,"-y","-i",vp,"-i",sp,
                         "-c:v","copy","-c:a","aac","-strict","experimental",
                         "-movflags","+faststart", son],
                        capture_output=True,
                        creationflags=SUBPROCESS_FLAGS)
                    # returncode 0 veya 1 olabilir ama dosya oluştuysa başarılıdır
                    if not os.path.exists(son) or os.path.getsize(son) < 1024:
                        raise subprocess.CalledProcessError(
                            result.returncode, FFMPEG, result.stderr)
                else:
                    son=ak.download(output_path=self.hedef,filename=f"{ad}.mp4")
            self.root.after(0,self._indir_bitti,son)
        except subprocess.CalledProcessError as e:
            self.root.after(0,self._indir_hata,f"ffmpeg hatası:\n{e.stderr.decode(errors='replace')}")
        except Exception as e:
            self.root.after(0,self._indir_hata,str(e))
        finally:
            for g in gecici:
                try: os.remove(g)
                except OSError: pass

    def _indir_bitti(self,yol):
        self.progress.set(100); self._kilit(False)
        self._durum(f"✓  {os.path.basename(yol)}",SUCCESS)
        if messagebox.askyesno("Bitti! 🎉",
                               f"İndirildi:\n{os.path.basename(yol)}\n\n"
                               "Klasörde göstereyim mi?"):
            try: subprocess.run(["explorer","/select,",yol])
            except Exception: pass

    def _indir_hata(self,msg):
        self._kilit(False); self.progress.set(0)
        self._durum("İndirme başarısız.",ACCENT)
        messagebox.showerror("Hata",f"İndirme başarısız:\n\n{msg}")


def main():
    root=tk.Tk()
    App(root)
    root.mainloop()

if __name__=="__main__":
    main()
