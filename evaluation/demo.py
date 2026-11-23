import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Desktop clip selector, processor and synchronized replay viewer."""
import csv
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from pathlib import Path
import cv2
from PIL import Image, ImageTk
from prepare import ROOT, OUT

class Demo:
    def __init__(self,window):
        self.w=window
        self.w.title('Forensic Sky-Robotics | Match review')
        self.events=queue.Queue()
        self.cap=None
        self.timer=None
        self.output=None
        self.busy=False
        rows=list(csv.DictReader((OUT/'clips.csv').open(encoding='utf8')))
        self.rows={r['uid']:ROOT/r['clip'] for r in rows}
        sample=next((r for r in rows if r['split']=='test' and r['foul_within_2s']=='1'),rows[0])
        default=sample['uid']
        examples={'World Cup final | Argentina - France':ROOT/'demo_samples/world_cup_final.mp4',
                  'Reviewed challenge | CAS-FD 105':ROOT/'datasets/cas_fd/test/foul/action_105_clip_0.mp4'}
        for label,path in examples.items():
            if path.exists():self.rows[label]=path
        if next(iter(examples)) in self.rows:default=next(iter(examples))
        self.choice=tk.StringVar(value=default)
        self.state=tk.StringVar(value='Choose a match clip and run analysis.')
        shell=ttk.Frame(window,padding=12); shell.pack(fill='both',expand=True)
        ttk.Label(shell,text='Forensic Sky-Robotics',font=('Segoe UI',20,'bold')).pack(anchor='w')
        toolbar=ttk.Frame(shell); toolbar.pack(fill='x',pady=8)
        self.combo=ttk.Combobox(toolbar,textvariable=self.choice,values=sorted(self.rows),width=48)
        self.combo.pack(side='left',fill='x',expand=True)
        ttk.Button(toolbar,text='Browse MP4',command=self.browse).pack(side='left',padx=4)
        self.run=ttk.Button(toolbar,text='Run analysis',command=self.start); self.run.pack(side='left')
        self.preview=ttk.Label(shell);self.preview.pack()
        self.combo.bind('<<ComboboxSelected>>',lambda _: self.thumbnail())
        self.thumbnail()
        actions=ttk.Frame(shell);actions.pack(fill='x',pady=8)
        ttk.Label(actions,textvariable=self.state).pack(side='left')
        self.open_btn=ttk.Button(actions,text='Open results',state='disabled',command=lambda:os.startfile(self.output));self.open_btn.pack(side='right')
        self.replay_btn=ttk.Button(actions,text='Replay',state='disabled',command=self.play);self.replay_btn.pack(side='right',padx=4)
        self.w.after(100,self.poll)
    def path(self):
        return self.rows.get(self.choice.get(),Path(self.choice.get()))
    def browse(self):
        if self.busy:return
        f=filedialog.askopenfilename(filetypes=[('Match videos','*.mp4 *.avi *.mov *.mkv')])
        if f:self.choice.set(f);self.thumbnail()
    def stop_playback(self):
        if self.timer:self.w.after_cancel(self.timer);self.timer=None
        if self.cap:self.cap.release();self.cap=None
    def display(self,im):
        pil=Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB))
        pil.thumbnail((min(1152,self.w.winfo_screenwidth()-65),520))
        self.photo=ImageTk.PhotoImage(pil);self.preview.configure(image=self.photo)
    def thumbnail(self):
        self.stop_playback()
        c=cv2.VideoCapture(str(self.path()));ok,im=c.read();c.release()
        if ok:self.display(im)
    def start(self):
        if self.busy:return
        path=self.path()
        if not path.is_file():messagebox.showerror('Clip','Select a readable match clip.');return
        self.stop_playback();self.busy=True;self.run.configure(state='disabled');self.combo.configure(state='disabled')
        self.open_btn.configure(state='disabled');self.replay_btn.configure(state='disabled')
        self.state.set('Loading pose and forecasting models…')
        def work():
            try:
                from analyze import analyze
                result=analyze(path,progress=lambda msg:self.events.put(('progress',msg)))
                self.events.put(('done',result))
            except Exception as exc:self.events.put(('error',str(exc)))
        threading.Thread(target=work,daemon=True).start()
    def poll(self):
        while not self.events.empty():
            kind,v=self.events.get()
            if kind=='progress':self.state.set(v);continue
            self.busy=False;self.run.configure(state='normal');self.combo.configure(state='normal')
            if kind=='error':self.state.set('Analysis stopped');messagebox.showerror('Analysis',v)
            else:
                self.output=v;self.state.set('Analysis complete')
                self.open_btn.configure(state='normal');self.replay_btn.configure(state='normal');self.play()
        self.w.after(120,self.poll)
    def play(self):
        self.stop_playback()
        self.cap=cv2.VideoCapture(str(self.output/'replay.mp4'))
        delay=max(20,int(1000/max(1,self.cap.get(5))))
        def tick():
            self.timer=None
            ok,im=self.cap.read()
            if ok:self.display(im);self.timer=self.w.after(delay,tick)
            else:self.stop_playback()
        tick()

if __name__=='__main__':
    w=tk.Tk(); Demo(w);w.mainloop()

