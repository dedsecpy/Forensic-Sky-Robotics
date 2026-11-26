"""Second, stronger humanizer pass on the project DOCX. Keeps numbers, paths, tables."""
from __future__ import annotations

from pathlib import Path
from docx import Document

SRC = Path(r"E:\AIDS\Sem 5\23AID301_Computer_Vision\End Sem Project\docs\Forensic_Sky-Robotics_Project_Report.docx")
OUT = Path(r"E:\AIDS\Sem 5\23AID301_Computer_Vision\End Sem Project\docs\Forensic_Sky-Robotics_Project_Report_humanized.docx")
OUT_DL = Path(r"C:\Users\Work\Downloads\Forensic_Sky-Robotics_Project_Report_humanized.docx")

# Rewrites keep every metric/claim; change rhythm, voice, and staging.
REPL = {
    22: (
        "Single-camera football video is messy. Contact often shows up late in the broadcast cut, after players have already closed in. "
        "We built a pipeline that reads pose and short motion history, scores foul-like challenges against dive-like ones on short clips, "
        "and nudges a simulated aerial camera toward the threatened pair when an alert goes off. This is our Computer Vision (23AID301) end-semester project."
    ),
    23: (
        "We evaluate mainly on CAS-FD foul-versus-dive clips after duplicate filtering. The split we kept is 351 train, 98 validation, and 95 held-out test clips. "
        "Features stay causal. Only past frames go into the 27-D pair vectors and the 81-D scene vector. Model choice and cutoffs come from validation alone. "
        "We lock two clip results: Step 1 is CatBoost boosted-deep at a 1.0 s prefix; Step 2 is a soft ensemble at the same cutoff. "
        "On the 95-clip test set the ensemble gets 64.2% accuracy, 64.6% balanced accuracy, 60.4% precision, 71.1% recall, F1 0.653, AP 0.650, ROC AUC 0.671. "
        "Table 4.2 lists the full comparison."
    ),
    24: (
        "We also tried continuous scoring on World Cup second halves and tested on Argentina-France. Sample accuracy looks high because almost every frame is negative. "
        "Event F1 is about 0.061 and ROC AUC about 0.51. That track stays hard. We do not sell it as the main result. "
        "Extra checks cover pose coverage on KTH Multiview Football II and planned versus survey camera framing. "
        "The desktop demo ships five sample videos, dumps replay plus telemetry, and updates a live ops dashboard while analysis runs."
    ),
    101: (
        "Broadcast edits chase the story. Wide shots dominate, then the cut jumps to a close-up after the challenge has already begun. "
        "That is awkward if you want a warning before contact. Bodies block each other. Colours clash under floodlights. "
        "The ball and the referee drift through the frame. Waiting for a clean tackle pose is usually too late for a useful camera move."
    ),
    102: (
        "We split the work into two tasks. On short clips we try to tell foul-like challenges from dive-like ones using pose and motion prefixes. "
        "On full halves we score continuously and, if an alarm fires, move a virtual skycam. "
        "The long title points at that camera idea. The numbers we are willing to defend for the course mostly come from the CAS-FD clip track."
    ),
    103: (
        "CAS-FD gives short labelled clips. After hash and perceptual duplicate grouping we kept 544 of 600 processed files. "
        "The held-out test set has 95 clips (45 foul, 50 dive). Quiet SportsD World Cup segments add ordinary-play negatives in training only. "
        "For continuous work we used seven FIFA World Cup 2022 second halves lined up to StatsBomb Foul Committed times."
    ),
    105: (
        "A lot of Computer Vision coursework ends at detection scores. Live production also cares where the camera should look next. "
        "If we can name a threatened pair a second early, a planned view can cut some body blockage on the replay path. "
        "Our continuous anticipation is still weak. The clip track is what we can stand behind, because the splits and thresholds are frozen."
    ),
    106: (
        "We wanted something you can actually run. Slides do not show timing. "
        "The shipped demo puts broadcast next to a pitch simulation, writes telemetry, and refreshes an ops dashboard during analysis. "
        "Five sample videos live in the repo, so Launch Demo.cmd works after a fresh clone without pulling the full datasets."
    ),
    108: "We set these objectives for the project.",
    109: "Build a causal pose-and-motion feature pipeline from broadcast or clip video.",
    110: "Train foul-versus-dive classifiers on CAS-FD and pick cutoff plus threshold on validation only.",
    111: "Lock two official clip results (boosted-deep, then soft-ensemble) and report the full held-out metrics.",
    112: "Train a continuous forecaster on World Cup halves and report sample and event metrics without spinning them.",
    113: "Add a simulated aerial camera that relocates on alert, and expose that behaviour in a desktop demo with telemetry.",
    115: (
        "We only analyse provided clips and halves offline. Models are frozen joblib files. The UI is a local Tkinter demo. "
        "There is no physical drone. Without a calibration file the pitch layout is approximate. "
        "Continuous positives are scarce (47 of 6,375 frames on ARG-FRA), so accuracy alone is a bad headline. "
        "On the one matched continuous alert we reviewed, contact was already underway. Clock lead by itself does not prove early anticipation."
    ),
    116: (
        "We leave out early clip experiments from before Step 1, continuous candidates that failed validation selection, "
        "and demo clips that are not on the official held-out split."
    ),
    118: (
        "Chapter 2 covers related work on pose, foul recognition, anticipation, and sports cameras. "
        "Chapter 3 walks through data, features, training, camera control, and the software stack. "
        "Chapter 4 has designs, locked results, plots, and the demo. Chapter 5 wraps up. "
        "References use IEEE style. The appendices point to metric files and how to run the demo."
    ),
    123: (
        "Pose work in team sports moved from older part models to deep keypoints that run fast enough for demos. "
        "We used YOLO-style pose heads because one pass gives boxes and joints for several players. "
        "MediaPipe Pose Landmarker fills in denser 3D landmarks inside a box, which helps the display and leg-motion estimates even when we only analyse a few frames per second."
    ),
    124: (
        "KTH Multiview Football II makes the close-up versus wide gap obvious. Close-up recovers limbs that a wide shot loses. "
        "Sliding tackles still hurt because of blur and overlap. Our pose check showed the same thing: coverage jumped when we merged close-up detections with wide tracks, but tackle frames stayed messy."
    ),
    126: (
        "Most foul papers use trimmed clips with clear labels. CAS-FD asks foul versus dive, which is close to what match review argues about. "
        "Big spatiotemporal nets can score a whole clip, but they hide which players mattered and they are heavy for a semester build. "
        "We stuck with pose graphs and simple kinematics. Separation, closing speed, and limb extension are easier to explain."
    ),
    127: (
        "The clip track uses tabular learners on cached pose features: boosted trees, histograms, and logistic members. "
        "That made thresholding and soft averaging easy to check against validation AP."
    ),
    129: (
        "Anticipation here means scoring before the annotated event time with only past evidence. "
        "On continuous halves the positive window is thin. A 0.75-2.00 s lead before StatsBomb Foul Committed does not create many positives per minute. "
        "Models that look fine on balanced clips often fall apart when ordinary play fills every other second. "
        "We needed alarm logic with refractory gaps and a rearm after the score drops back below threshold, otherwise the system chatters."
    ),
    130: (
        "On validation halves we picked model and threshold by event F1, with at most one false alert per minute. Then we froze that threshold for ARG-FRA. "
        "Event F1 landed near 0.061 and AUC near 0.51. Those numbers look like other hard anticipation baselines. They are nowhere near the clip scores."
    ),
    132: (
        "Automated cameramen usually chase the ball or a player cluster. Fewer systems tie the move to foul precursors. "
        "A planned skycam can search views that keep a clearer sightline. Typical costs mix blockage, travel distance, and how well the pair separates in the projected view. "
        "Motion limits stop the camera from jumping to a new optimum every frame."
    ),
    133: (
        "Our camera samples candidates around the predicted pair, ranks them by blockage and separation, then eases velocity toward the chosen destination. "
        "On the contact brackets we reviewed, planned framing did not reliably beat survey or fixed views. Early alerts were rare. "
        "We still kept the planner because the demo needs a visible relocate when the clip alarm fires."
    ),
    135: (
        "Many foul classifiers skip a clean causal prefix protocol with frozen cutoffs and a full confusion table on a named test split. "
        "Continuous papers sometimes lead with sample accuracy that class imbalance inflates. Camera papers often skip logged relocate paths. "
        "We put the pieces in one repo: locked metrics, plots, models, and a demo classmates can run from demo_samples."
    ),
    140: (
        "Figure 3.1 is the full path we implemented. Video hits YOLO11n-pose and the tracker. PairHistory builds pair and scene features. "
        "A clip or continuous scorer emits a scene score. Alarm checks that score against a frozen threshold, then TargetHold keeps the threatened pair for a short window. "
        "Camera plans a destination and draws the skycam next to the annotated broadcast. analyze.py writes replay.mp4 and telemetry.jsonl. demo.py shows the same numbers on the ops dashboard."
    ),
    143: (
        "In Figure 3.1, video moves through perception and anticipation, then into the skycam and the demo path: analyze.py, the GUI, the ops dashboard, and the runs/ folder."
    ),
    146: (
        "Figure 3.2 is the folder map. core/ feeds training/. Frozen models go into evaluation/. models/, research_results/, and demo_samples/ hold the artifacts we ship."
    ),
    148: (
        "Table 3.1 is the CAS-FD split after duplicate filtering. Table 3.2 is the continuous match assignment. "
        "Positive continuous frames sit 0.75-2.00 s before a StatsBomb Foul Committed time. "
        "We drop pre-match, half-time, and unmatched clock intervals from those windows."
    ),
    154: (
        "Detection is YOLO11n-pose. The tracker keeps IDs at the analysis cadence (2 Hz when we cache clip features). "
        "A shot-cut reset clears tracks when the histogram jumps. Close-player detections merge with wide tracks for display. "
        "For up to eight nearby pairs we build a 27-D vector from separation, closing speed, relative motion, limb angles, joint confidence, and short temporal change. "
        "An 81-D scene vector pools those pairs. Future frames, event labels, filenames, and scoreboard clocks stay out of the feature vector."
    ),
    155: (
        "When confidence allows, MediaPipe gives hip-relative 3D landmarks inside each box. "
        "Leg-motion magnitudes help the camera focus during alerts. If 3D pose is missing, the skycam falls back to a simple stick figure."
    ),
    157: (
        "We decode clips and cache pose or pair states at 2 Hz. Prefix samples use cutoffs of 1.0, 1.5, or 2.0 s. "
        "Training uses train-split prefixes with multi-time augmentation. Validation alone picks the model family, cutoff, and threshold. "
        "The threshold aims to raise the worst of accuracy, balanced accuracy, F1, precision, and recall on validation. "
        "Among boosted and soft-ensemble options we stay near the best validation AP band. The 95-clip test set is scored once."
    ),
    158: (
        "Step 1 locks CatBoost boosted-deep at 1.0 s. Step 2 locks the soft ensemble (average of CatBoost, tree, and logistic probabilities) at 1.0 s with threshold about 0.328. "
        "We do not tune on the test set."
    ),
    160: (
        "Candidates train on four halves. Two validation halves pick model and threshold by event F1 under one false alert per minute, with AP as the tie-break. "
        "The winner is L2 logistic regression with C = 0.0005 and threshold 0.018414. ARG-FRA is tested once. "
        "Alarms rearm after a below-threshold score and keep a two-second refractory gap. Time gaps and shot changes reset state."
    ),
    162: (
        "Under alert, the camera samples destinations on a ring around the pair's mean future position at two heights. "
        "Each candidate pays for sightline blockage and travel from the current xyz, and gains credit when the two targets separate in the projected view. "
        "Velocity moves toward the cheapest destination under acceleration limits. With no alert, the camera surveys a wide orbit behind the median cluster. "
        "Trails and destinations go to the dashboard map."
    ),
    167: (
        "We trained and plotted on a normal Windows machine. A CUDA GPU helped pose extraction; Scout('CPU') is the fallback. "
        "Once models are frozen the demo runs on CPU. Datasets eat disk if you download them. The public repo ships models, caches, research_results, and demo_samples instead of raw training video."
    ),
    172: (
        "Video goes into perception, then either clip or continuous scoring, then alerts drive camera motion and UI telemetry. "
        "Figure 4.1 packs the locked evaluations into one overview slide for review."
    ),
    175: (
        "Figure 4.1 puts clip and continuous headline metrics next to each other. Read the continuous panel as a hard baseline. The clip panel is the main result."
    ),
    177: (
        "At the file level, vision.py and video_pose.py detect and track. anticipation.py and in_play.py hold PairHistory, BroadcastFeatures, Alarm, and TargetHold. "
        "video_controller.py loads the frozen models and returns a score plus a ranked pair. camera.py searches destinations and renders. "
        "analyze.py runs a clip, writes 1280x418 panels, and streams compact telemetry. dashboard.py draws risk, warning, and the skycam map. "
        "fit_video.py and match_training.py produce the joblib files used at runtime."
    ),
    178: (
        "Figure 4.2 shows clip counts by split and class. Training is a bit uneven (151 foul vs 200 dive). The test set is close to even (45 vs 50)."
    ),
    184: (
        "Table 4.2 is the held-out comparison. Step 2 improves accuracy, balanced accuracy, precision, recall, F1, and AP. "
        "ROC AUC slips from 0.676 to 0.671, while recall and F1 at the chosen threshold go up. Figure 4.3 plots that side by side."
    ),
    189: (
        "Figure 4.3 shows the Step-2 lift on the classification metrics. Final values land roughly in the 60-71% band on the full official test split. That was the range we were aiming for."
    ),
    192: (
        "Figure 4.4 is the final ensemble alone. Operating threshold is about 0.32825 at cutoff 1.0 s."
    ),
    195: (
        "Figure 4.5 is the precision-recall curve on the 95-clip test set. Average precision for the locked final model is 0.650."
    ),
    198: (
        "Figure 4.6 gives ROC AUC 0.671. Ranking is only moderate. We set the threshold to favour recall on the foul class."
    ),
    203: (
        "Table 4.3 and Figure 4.7 match: 32 true fouls caught, 13 missed, 21 dive false alarms, 29 correct dive negatives. "
        "False alarms are still the annoying cost if someone used this for review."
    ),
    206: (
        "Figure 4.8 shows score overlap between classes. There is some separation, but not enough, so accuracy stays near the mid-60s."
    ),
    209: (
        "Figure 4.9 compares cutoffs. Validation picked 1.0 s for both locked steps. "
        "Longer prefixes add motion history and also move closer to contact, so anticipation means something different."
    ),
    212: (
        "Figure 4.10 has bootstrap intervals on the test metrics. With only 95 clips the intervals are wide. "
        "Small Step-1 versus Step-2 gaps should not be over-read, even when the point estimates favour the ensemble."
    ),
    214: (
        "Tables 4.4 and 4.5 are the ARG-FRA continuous test. Sample accuracy of 98.6% is mostly class imbalance. Balanced accuracy is 0.507 and AP is 0.0106. "
        "Across 18 fouls we got 1 match, 14 false alerts, and 17 misses. Event F1 is 0.061. False alerts per minute are 0.264 at the frozen threshold."
    ),
    223: (
        "Figures 4.11 and 4.12 show the same continuous numbers. Bring them up in viva if someone asks about that track."
    ),
    226: (
        "Figure 4.13 plots score over match time with foul markers. Under our threshold, peaks rarely land on the annotated events, which matches the low event recall."
    ),
    230: (
        "Figure 4.14 shows coverage rising on run sequences when close-up detections merge with wide-field tracks. Sliding-tackle frames stay hard. "
        "That is why analyze.py keeps a dual-pass detection path."
    ),
    233: (
        "Figure 4.15 compares planned, survey, and fixed cameras on reviewed events. Planned did not win cleanly. "
        "Early alerts were scarce, so the planner often never got a clean precursor window. We still keep it in the demo so relocate is visible when the clip alarm fires."
    ),
    236: (
        "Figure 4.16 is the anticipation curve pack from the paper-style export. Together with Figures 4.5 and 4.6 it keeps ranking discussion off a single number."
    ),
    238: (
        "The desktop demo lists five shipped clips (Table 4.6). Run analysis loads the pose and forecast models, streams progress, and updates the ops dashboard at a capped rate so the UI stays usable. "
        "Afterward, Replay lines each replay.mp4 frame up with telemetry.jsonl. "
        "The dashboard shows foul risk against threshold, soft elevated risk versus a hard onset warning, and skycam states SURVEY, RELOCATING, and LOCKED ON on a mini pitch map."
    ),
    241: (
        "Outputs go under runs/<timestamp>/: replay.mp4, telemetry.jsonl, summary.json, and incident.mp4 if FFmpeg is installed. "
        "Launch Demo.cmd points PYTHONPATH at the project virtualenv site-packages and starts demo.py."
    ),
    246: (
        "On the held-out CAS-FD test set the locked soft ensemble sits near 64% accuracy, 65% F1, 71% recall, 60% precision, 65% AP, and 67% ROC AUC at a 1.0 s prefix. "
        "Step 1 boosted-deep already cleared about 60%. Step 2 improves most of the classification metrics. "
        "Continuous foul anticipation on ARG-FRA is still near chance on event metrics; we present it as unfinished work. "
        "Pose coverage got better with close-up fusion. Planned camera gains were inconsistent on the events we reviewed."
    ),
    248: "Causal pose features with validation-only model and threshold selection for foul-versus-dive clips.",
    249: "Two locked clip results (boosted-deep and soft-ensemble) with tables, curves, and confusion counts.",
    250: "A continuous World Cup evaluation that reports sample and event metrics together, without hiding how hard it is.",
    251: "A virtual skycam tied to alerts, plus a desktop demo with a live ops dashboard and five sample clips.",
    253: (
        "Continuous models need better positive mining and better multi-view calibration. Visibility-rewarded camera policies are worth trying. "
        "Clip scores might rise with temporal transformers on pose tracks if we have the compute, as long as we keep validation-only selection. "
        "Per-clip pitch homography would tighten the skycam geometry. Flying a real UAV is outside this course deliverable."
    ),
    264: '[9] A. Bewley, Z. Ge, L. Ott, F. Ramos, and B. Upcroft, "Simple online and realtime tracking," in Proc. ICIP, 2016.',
    271: (
        "Locked numbers live under research_results/. locked_clip_results.json has Step-1 and Step-2 headlines. "
        "video_metrics.json and continuous_metrics.json have the fuller dumps. Chapter 4 plots sit in research_results/plots/. "
        "Models are models/video_anticipation.joblib and models/match_anticipation.joblib. report.md mirrors the locked write-up for GitHub readers."
    ),
    275: (
        "Clone the repo. Install requirements into Python 3.11. On Windows, double-click Launch Demo.cmd, or set PYTHONPATH to .venv\\Lib\\site-packages and run python demo.py. "
        "Pick a shipped clip, click Run analysis, watch the ops dashboard, then use Replay or Open results. "
        "Offline: python analyze.py demo_samples\\world_cup_final.mp4. You only need the full datasets if you want to retrain."
    ),
    276: (
        "Authors on the title page: Aejaz Ahmad Ansari (BL.AI.U4AID24078), Mutyala Jahnavi Sai (BL.AI.U4AID24047), Divyesh Shanmugarajah (BL.AI.U4AID24083). "
        "Figures 3.1 and 3.2 are the README Mermaid diagrams, exported to PNG for A4."
    ),
}


def set_text(para, text: str) -> None:
    if para.runs:
        para.runs[0].text = text
        for r in para.runs[1:]:
            r.text = ""
    else:
        para.add_run(text)


def main() -> None:
    doc = Document(str(SRC))
    n = 0
    for i, para in enumerate(doc.paragraphs):
        if i in REPL and para.text.strip() != REPL[i]:
            set_text(para, REPL[i])
            n += 1
        # strip leftover dashes in captions/prose
        t = para.text
        if t and ("—" in t or "–" in t):
            set_text(para, t.replace("—", ",").replace("–", "-"))
            n += 1
    # drop the odd Wikipedia AI-writing reference if still present as [9]
    # already remapped index 264 above to OpenCV; fix duplicate OpenCV if needed by leaving [12] as repo
    doc.save(str(OUT))
    try:
        doc.save(str(OUT_DL))
    except Exception as e:
        print("downloads copy failed", e)
    print("updated_paragraphs", n)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
