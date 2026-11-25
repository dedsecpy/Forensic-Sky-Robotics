"""Real-time foul anticipation + skycam ops HUD for the desktop demo."""
import math
import tkinter as tk
from tkinter import ttk


class Dashboard(ttk.Frame):
    BG = '#1a1f24'
    PANEL = '#232a31'
    MUTED = '#8b969f'
    TEXT = '#e8eef2'
    ACCENT = '#3db8e8'
    WARN = '#e8a23a'
    ALERT = '#e24b4b'
    GOOD = '#3ecf8e'
    PITCH = '#2f5a38'
    LINE = '#6d9a74'

    def __init__(self, master, width=1152, height=188):
        super().__init__(master)
        self.W, self.H = width, height
        self.canvas = tk.Canvas(self, width=width, height=height, highlightthickness=0,
                                bg=self.BG, bd=0)
        self.canvas.pack(fill='both', expand=True)
        self._flash = 0
        self._last = None
        self._trail = []
        self.draw(None)

    def reset(self):
        self._flash = 0
        self._last = None
        self._trail = []
        self.draw(None)

    def update(self, tel):
        if not tel:
            self.draw(None)
            return
        xyz = tel.get('camera_xyz')
        if xyz:
            pt = (float(xyz[0]), float(xyz[1]))
            if not self._trail or (abs(self._trail[-1][0] - pt[0]) + abs(self._trail[-1][1] - pt[1])) > 0.15:
                self._trail.append(pt)
                self._trail = self._trail[-60:]
        if tel.get('alarm_onset') or tel.get('alarm_hold'):
            self._flash = 8
        elif self._flash > 0:
            self._flash -= 1
        self._last = tel
        self.draw(tel)

    def draw(self, tel):
        c = self.canvas
        c.delete('all')
        w, h = self.W, self.H
        c.create_rectangle(0, 0, w, h, fill=self.BG, outline='')
        c.create_text(14, 14, anchor='w', text='OPS DASHBOARD', fill=self.MUTED,
                      font=('Segoe UI', 9, 'bold'))

        left, mid, right = 12, int(w * 0.34), int(w * 0.66)
        self._risk(c, left, 28, mid - left - 10, h - 40, tel)
        self._warn(c, mid, 28, right - mid - 10, h - 40, tel)
        self._camera(c, right, 28, w - right - 12, h - 40, tel)

    def _panel(self, c, x, y, pw, ph, title):
        c.create_rectangle(x, y, x + pw, y + ph, fill=self.PANEL, outline='#323b44')
        c.create_text(x + 10, y + 12, anchor='w', text=title, fill=self.MUTED,
                      font=('Segoe UI', 8, 'bold'))

    def _risk(self, c, x, y, pw, ph, tel):
        self._panel(c, x, y, pw, ph, 'FOUL RISK')
        score = None if tel is None else tel.get('score')
        th = 0.02 if tel is None else float(tel.get('threshold') or 0.02)
        t = 0.0 if tel is None else float(tel.get('time') or 0)
        if score is None:
            level, color, label = 0.0, self.MUTED, 'INSUFFICIENT TRACKS'
            shown = '—'
        else:
            score = float(score)
            shown = f'{score:.3f}'
            elev = score >= 0.65 * th
            hard = bool(tel.get('alarm_onset') or tel.get('alarm_hold') or
                        (tel.get('alert') and score >= th))
            if hard:
                level, color, label = min(1.0, score / max(th * 1.4, 1e-6)), self.ALERT, 'ANTICIPATED'
            elif elev:
                level, color, label = min(1.0, score / max(th * 1.4, 1e-6)), self.WARN, 'ELEVATED'
            else:
                level, color, label = min(1.0, score / max(th * 1.4, 1e-6)), self.GOOD, 'SURVEY'

        gx, gy, gw, gh = x + 14, y + 40, pw - 28, 18
        c.create_rectangle(gx, gy, gx + gw, gy + gh, fill='#12161a', outline='#3a4550')
        fill_w = max(2, int(gw * level)) if score is not None else 0
        if fill_w:
            c.create_rectangle(gx + 1, gy + 1, gx + fill_w, gy + gh - 1, fill=color, outline='')
        # threshold tick
        tx = gx + int(gw * min(1.0, th / max(th * 1.4, 1e-6)))
        c.create_line(tx, gy - 2, tx, gy + gh + 2, fill=self.TEXT, width=2)
        c.create_text(tx, gy + gh + 10, text='THR', fill=self.MUTED, font=('Segoe UI', 7))

        c.create_text(x + 14, y + 88, anchor='w', text=label, fill=color,
                      font=('Segoe UI', 14, 'bold'))
        c.create_text(x + 14, y + 118, anchor='w',
                      text=f'Score  {shown}    t = {t:05.2f}s',
                      fill=self.TEXT, font=('Consolas', 10))
        c.create_text(x + 14, y + 140, anchor='w',
                      text=f'Trigger  {th:.3f}',
                      fill=self.MUTED, font=('Consolas', 9))

    def _warn(self, c, x, y, pw, ph, tel):
        self._panel(c, x, y, pw, ph, 'ANTICIPATION')
        if tel is None:
            c.create_text(x + pw / 2, y + ph / 2, text='Waiting for analysis…',
                          fill=self.MUTED, font=('Segoe UI', 11))
            return

        score = tel.get('score')
        th = float(tel.get('threshold') or 0.02)
        onset = bool(tel.get('alarm_onset'))
        hold = bool(tel.get('alarm_hold'))
        alert = bool(tel.get('alert'))
        ids = tel.get('target_ids') or []
        hard = onset or hold or self._flash > 0
        elev = (score is not None and float(score) >= 0.65 * th) and not hard

        if hard:
            pulse = self._flash % 2 == 0
            banner = self.ALERT if pulse else '#7a1f1f'
            c.create_rectangle(x + 8, y + 28, x + pw - 8, y + ph - 12, fill=banner, outline='')
            c.create_text(x + pw / 2, y + 58, text='⚠  FOUL ANTICIPATED',
                          fill=self.TEXT, font=('Segoe UI', 15, 'bold'))
            pair = '  ·  '.join(f'#{i}' for i in ids) if ids else 'threatened pair'
            c.create_text(x + pw / 2, y + 92, text=f'Lock targets  {pair}',
                          fill=self.TEXT, font=('Segoe UI', 11))
            c.create_text(x + pw / 2, y + 118, text='Skycam relocating to clear sightline',
                          fill='#ffd0d0', font=('Segoe UI', 9))
        elif elev:
            c.create_rectangle(x + 8, y + 28, x + pw - 8, y + ph - 12, fill='#3a2e18', outline=self.WARN)
            c.create_text(x + pw / 2, y + 70, text='ELEVATED RISK',
                          fill=self.WARN, font=('Segoe UI', 14, 'bold'))
            c.create_text(x + pw / 2, y + 104, text='Monitoring closing challenge',
                          fill=self.TEXT, font=('Segoe UI', 10))
        elif alert:
            c.create_rectangle(x + 8, y + 28, x + pw - 8, y + ph - 12, fill='#1e3038', outline=self.ACCENT)
            pair = '  ·  '.join(f'#{i}' for i in ids) if ids else 'pair'
            c.create_text(x + pw / 2, y + 70, text='TRACKING CHALLENGE',
                          fill=self.ACCENT, font=('Segoe UI', 13, 'bold'))
            c.create_text(x + pw / 2, y + 104, text=f'Holding  {pair}',
                          fill=self.TEXT, font=('Segoe UI', 10))
        else:
            c.create_text(x + pw / 2, y + 72, text='NO FOUL SIGNAL',
                          fill=self.GOOD, font=('Segoe UI', 13, 'bold'))
            c.create_text(x + pw / 2, y + 104, text='Survey mode — continuous scoring',
                          fill=self.MUTED, font=('Segoe UI', 10))

    def _camera(self, c, x, y, pw, ph, tel):
        self._panel(c, x, y, pw, ph, 'VIRTUAL SKYCAM')
        # status strip
        mode, mcolor = 'SURVEY', self.GOOD
        detail = 'Wide orbit over play'
        if tel:
            alert = bool(tel.get('alert'))
            speed = float(tel.get('camera_speed') or 0)
            ids = tel.get('target_ids') or []
            dest = tel.get('camera_dest')
            xyz = tel.get('camera_xyz')
            dist = 0.0
            if dest and xyz:
                dist = math.dist(dest[:2], xyz[:2])
            if alert and (speed > 1.2 or dist > 2.5):
                mode, mcolor = 'RELOCATING', self.WARN
                detail = 'Moving to optimal vantage'
            elif alert:
                mode, mcolor = 'LOCKED ON', self.ALERT
                pair = '/'.join(f'#{i}' for i in ids) if ids else 'pair'
                detail = f'Framing {pair}'

        c.create_rectangle(x + 8, y + 26, x + pw - 8, y + 52, fill='#12161a', outline='#3a4550')
        c.create_oval(x + 16, y + 33, x + 30, y + 47, fill=mcolor, outline='')
        c.create_text(x + 38, y + 39, anchor='w', text=mode, fill=mcolor,
                      font=('Segoe UI', 10, 'bold'))
        c.create_text(x + pw - 14, y + 39, anchor='e', text=detail, fill=self.MUTED,
                      font=('Segoe UI', 8))

        # mini pitch
        mx, my, mw, mh = x + 10, y + 60, pw - 20, ph - 72
        c.create_rectangle(mx, my, mx + mw, my + mh, fill=self.PITCH, outline=self.LINE)
        c.create_line(mx + mw / 2, my, mx + mw / 2, my + mh, fill=self.LINE)
        c.create_oval(mx + mw / 2 - 16, my + mh / 2 - 16, mx + mw / 2 + 16, my + mh / 2 + 16,
                      outline=self.LINE)

        def map_xy(pos):
            # pitch approx x∈[-52,52], y∈[-5,70] → canvas
            px = mx + (float(pos[0]) + 52) / 104 * mw
            py = my + mh - (float(pos[1]) + 5) / 75 * mh
            return px, py

        if self._trail and len(self._trail) > 1:
            pts = []
            for p in self._trail:
                pts.extend(map_xy(p))
            c.create_line(*pts, fill='#e8b84a', width=2, smooth=True)

        if tel:
            for p in tel.get('players_xy') or []:
                u, v = map_xy(p)
                c.create_oval(u - 2, v - 2, u + 2, v + 2, fill='#b8c4bc', outline='')
            for p in tel.get('pair_xy') or []:
                u, v = map_xy(p)
                c.create_oval(u - 4, v - 4, u + 4, v + 4, fill=self.ACCENT, outline=self.TEXT)
            dest = tel.get('camera_dest')
            xyz = tel.get('camera_xyz')
            if dest and tel.get('alert'):
                du, dv = map_xy(dest)
                c.create_oval(du - 5, dv - 5, du + 5, dv + 5, outline='#ffd76a', width=2)
                c.create_text(du + 8, dv - 6, anchor='w', text='DEST', fill='#ffd76a',
                              font=('Segoe UI', 7, 'bold'))
                if xyz:
                    cu, cv = map_xy(xyz)
                    c.create_line(cu, cv, du, dv, fill='#ffd76a', width=2, arrow=tk.LAST)
            if xyz:
                cu, cv = map_xy(xyz)
                c.create_polygon(cu, cv - 6, cu + 5, cv + 4, cu - 5, cv + 4,
                                 fill='#ffd24a', outline='#fff3c0')
