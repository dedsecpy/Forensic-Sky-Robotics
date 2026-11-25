# Demo real-time dashboard design

**Date:** 2026-11-26  
**Status:** Approved by user (Approach 1; choices C/C/C; proceed without further gates)

## Goal

Professional ops HUD under the dual-pane simulation showing foul anticipation accurately, with soft elevated risk + hard onset warning, and camera relocate map + status strip. Live during analysis and synced during Replay. Smooth, not choppy.

## Approach

Tkinter dashboard panel in `evaluation/demo.py` driven by telemetry. Analysis emits compact UI samples + occasional preview frames; Replay indexes `telemetry.jsonl` 1:1 with `replay.mp4`.

## Layout

Dark HUD (~190px) under preview: Risk gauge | Warning board | Camera strip + mini pitch (current ♦, dest ○, trail, pair dots).

## Data

Extend telemetry with `alarm_hold`, `threshold`, `camera_dest`, `camera_speed`. Progress callback may pass `telemetry=` and throttled `frame=`. Soft elevated when score ≥ 0.65×threshold; hard warning on onset/hold window.

## Smoothness

Fixed preview size; Replay uses constant frame delay from video FPS; UI telemetry/frame updates capped (~12 Hz) during analysis; Canvas redraws only on new samples.
