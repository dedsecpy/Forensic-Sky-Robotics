import sys
from pathlib import Path
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[0]
for _p in (_ROOT, _HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import bootstrap  # noqa: E402
"""Desktop clip selector, processor and synchronized replay viewer."""
import csv
import json
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from pathlib import Path
import cv2
from PIL import Image, ImageTk
from prepare import ROOT, OUT
from dashboard import Dashboard

PREVIEW_W, PREVIEW_H = 1152, 376


class Demo:
    def __init__(self, window):
        self.w = window
        self.w.title('Forensic Sky-Robotics | Match review')
        self.w.minsize(1180, 720)
        self.events = queue.Queue()
        self.cap = None
        self.timer = None
        self.output = None
        self.busy = False
        self.telemetry = []
        self.frame_i = 0
        self._last_ui = 0.0
        self._pending_tel = None
        self._pending_frame = None

        rows = list(csv.DictReader((OUT / 'clips.csv').open(encoding='utf8')))
        self.rows = {r['uid']: ROOT / r['clip'] for r in rows}
        sample = next((r for r in rows if r['split'] == 'test' and r['foul_within_2s'] == '1'), rows[0])
        default = sample['uid']
        examples = {
            'World Cup final | Argentina - France': ROOT / 'demo_samples/world_cup_final.mp4',
            'CAS-FD foul | challenge 105': ROOT / 'demo_samples/casfd_foul_105.mp4',
            'CAS-FD foul | challenge 128': ROOT / 'demo_samples/casfd_foul_128.mp4',
            'CAS-FD foul | challenge 107': ROOT / 'demo_samples/casfd_foul_107.mp4',
            'CAS-FD dive | challenge 101': ROOT / 'demo_samples/casfd_dive_101.mp4',
        }
        for label, path in examples.items():
            if path.exists():
                self.rows[label] = path
        if next(iter(examples)) in self.rows:
            default = next(iter(examples))

        self.choice = tk.StringVar(value=default)
        self.state = tk.StringVar(value='Choose a match clip and run analysis.')

        shell = ttk.Frame(window, padding=12)
        shell.pack(fill='both', expand=True)
        ttk.Label(shell, text='Forensic Sky-Robotics', font=('Segoe UI', 20, 'bold')).pack(anchor='w')

        toolbar = ttk.Frame(shell)
        toolbar.pack(fill='x', pady=8)
        self.combo = ttk.Combobox(toolbar, textvariable=self.choice, values=sorted(self.rows), width=48)
        self.combo.pack(side='left', fill='x', expand=True)
        ttk.Button(toolbar, text='Browse MP4', command=self.browse).pack(side='left', padx=4)
        self.run = ttk.Button(toolbar, text='Run analysis', command=self.start)
        self.run.pack(side='left')

        self.preview = ttk.Label(shell)
        self.preview.pack()
        self.dash = Dashboard(shell, width=PREVIEW_W, height=188)
        self.dash.pack(fill='x', pady=(10, 0))
        self.combo.bind('<<ComboboxSelected>>', lambda _: self.thumbnail())
        self.thumbnail()

        actions = ttk.Frame(shell)
        actions.pack(fill='x', pady=8)
        ttk.Label(actions, textvariable=self.state).pack(side='left')
        self.open_btn = ttk.Button(actions, text='Open results', state='disabled',
                                   command=lambda: os.startfile(self.output))
        self.open_btn.pack(side='right')
        self.replay_btn = ttk.Button(actions, text='Replay', state='disabled', command=self.play)
        self.replay_btn.pack(side='right', padx=4)
        self.w.after(50, self.poll)

    def path(self):
        return self.rows.get(self.choice.get(), Path(self.choice.get()))

    def browse(self):
        if self.busy:
            return
        f = filedialog.askopenfilename(filetypes=[('Match videos', '*.mp4 *.avi *.mov *.mkv')])
        if f:
            self.choice.set(f)
            self.thumbnail()

    def stop_playback(self):
        if self.timer:
            self.w.after_cancel(self.timer)
            self.timer = None
        if self.cap:
            self.cap.release()
            self.cap = None

    def display(self, im):
        rgb = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        scale = min(PREVIEW_W / w, PREVIEW_H / h)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        if (nw, nh) != (w, h):
            rgb = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA)
        canvas = Image.new('RGB', (PREVIEW_W, PREVIEW_H), (18, 22, 26))
        canvas.paste(Image.fromarray(rgb), ((PREVIEW_W - nw) // 2, (PREVIEW_H - nh) // 2))
        self.photo = ImageTk.PhotoImage(canvas)
        self.preview.configure(image=self.photo)

    def thumbnail(self):
        self.stop_playback()
        self.dash.reset()
        c = cv2.VideoCapture(str(self.path()))
        ok, im = c.read()
        c.release()
        if ok:
            self.display(im)

    def load_telemetry(self, run_dir):
        path = Path(run_dir) / 'telemetry.jsonl'
        rows = []
        if path.exists():
            with path.open(encoding='utf8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    players = rec.get('players') or []
                    ids = set(rec.get('target_ids') or [])
                    rows.append(dict(
                        time=rec.get('time'),
                        score=rec.get('score'),
                        alert=rec.get('alert'),
                        alarm_onset=rec.get('alarm_onset'),
                        alarm_hold=rec.get('alarm_hold'),
                        threshold=rec.get('threshold'),
                        target_ids=rec.get('target_ids') or [],
                        camera_xyz=rec.get('camera_xyz'),
                        camera_dest=rec.get('camera_dest'),
                        camera_speed=rec.get('camera_speed'),
                        look_at=rec.get('look_at'),
                        players_xy=[p['xy'] for p in players if 'xy' in p][:16],
                        pair_xy=[p['xy'] for p in players if p.get('id') in ids][:4],
                    ))
        return rows

    def start(self):
        if self.busy:
            return
        path = self.path()
        if not path.is_file():
            messagebox.showerror('Clip', 'Select a readable match clip.')
            return
        self.stop_playback()
        self.busy = True
        self.telemetry = []
        self.dash.reset()
        self.run.configure(state='disabled')
        self.combo.configure(state='disabled')
        self.open_btn.configure(state='disabled')
        self.replay_btn.configure(state='disabled')
        self.state.set('Loading pose and forecasting models…')
        self._last_ui = 0.0

        last = [0.0]

        def on_progress(msg, telemetry=None, frame=None):
            now = time.monotonic()
            self.events.put(('progress', msg))
            # Cap UI push rate so analysis stays smooth in the worker and Tk stays responsive.
            force = bool(telemetry and telemetry.get('alarm_onset'))
            if telemetry is not None or frame is not None:
                if force or now - last[0] >= (1 / 12):
                    last[0] = now
                    # Copy frame so OpenCV can reuse its buffer; drop backlog in poll.
                    fr = None if frame is None else frame.copy()
                    self.events.put(('live', (telemetry, fr)))

        def work():
            try:
                from analyze import analyze
                result = analyze(path, progress=on_progress)
                self.events.put(('done', result))
            except Exception as exc:
                self.events.put(('error', str(exc)))

        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        live = None
        progress_msg = None
        terminal = None
        while not self.events.empty():
            kind, v = self.events.get()
            if kind == 'progress':
                progress_msg = v
            elif kind == 'live':
                live = v  # keep only the newest preview/telemetry sample
            else:
                terminal = (kind, v)
        if progress_msg is not None:
            self.state.set(progress_msg)
        if live is not None:
            tel, frame = live
            if tel is not None:
                self.dash.update(tel)
            if frame is not None:
                self.display(frame)
        if terminal is not None:
            kind, v = terminal
            self.busy = False
            self.run.configure(state='normal')
            self.combo.configure(state='normal')
            if kind == 'error':
                self.state.set('Analysis stopped')
                messagebox.showerror('Analysis', v)
            else:
                self.output = v
                self.telemetry = self.load_telemetry(v)
                self.state.set('Analysis complete — live dashboard synced')
                self.open_btn.configure(state='normal')
                self.replay_btn.configure(state='normal')
                self.play()
        # keep flash animation alive during live hard-warning
        if self.busy and self.dash._flash > 0 and self.dash._last is not None:
            self.dash.draw(self.dash._last)
            self.dash._flash = max(0, self.dash._flash - 1)
        self.w.after(40, self.poll)

    def play(self):
        self.stop_playback()
        if self.output is None:
            return
        if not self.telemetry:
            self.telemetry = self.load_telemetry(self.output)
        self.dash.reset()
        self.cap = cv2.VideoCapture(str(self.output / 'replay.mp4'))
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 10
        # Slightly paced for readability without feeling laggy.
        delay = max(33, int(1000 / max(1.0, min(fps, 18))))
        self.frame_i = 0

        def tick():
            self.timer = None
            if self.cap is None:
                return
            ok, im = self.cap.read()
            if not ok:
                self.stop_playback()
                self.state.set('Replay finished')
                return
            self.display(im)
            if self.frame_i < len(self.telemetry):
                self.dash.update(self.telemetry[self.frame_i])
            self.frame_i += 1
            self.timer = self.w.after(delay, tick)

        self.state.set('Replaying with synced dashboard…')
        tick()


if __name__ == '__main__':
    w = tk.Tk()
    Demo(w)
    w.mainloop()
