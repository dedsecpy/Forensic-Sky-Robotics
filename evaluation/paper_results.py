import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Export paper tables and figures directly from saved predictions."""
import json
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import binomtest
from sklearn.metrics import precision_recall_curve,roc_curve,matthews_corrcoef
from fit_video import RESULT,read_rows,save_rows
from prepare import ROOT,OUT
from half_features import aligned,reference
from match_training import alarms
from match_corpus import GAMES

def read(name):return json.loads((RESULT/name).read_text())
def fmt(n):return f'{n:.3f}' if n is not None else '—'

def main():
    c=read('continuous_metrics.json');v=read('video_metrics.json');cam=read('camera_metrics.json');d=read('deployment_clips_metrics.json')
    pose=read('pose_metrics.json')
    test=aligned('ARG_FRA')
    def columns(file,keys):
        rr=read_rows(RESULT/file)
        return tuple(np.array([float(r[k]) for r in rr]) for k in keys)
    yc,sc=columns('half_ARG_FRA.csv',['label','score'])
    yv,sv=columns('test_prefix_predictions.csv',['label','score'])
    fig,axs=plt.subplots(2,2,figsize=(9,7),layout='constrained')
    for j,(y,s,title,th) in enumerate([(yc,sc,'Continuous World Cup final',c['threshold']),(yv,sv,'Foul versus dive clip prefixes',v['threshold'])]):
        p,r,_=precision_recall_curve(y,s);fpr,tpr,_=roc_curve(y,s)
        ax=axs[0,j];ax.step(r,p,where='post',lw=1.5,color='#125f72');ax.axhline(y.mean(),color='#995521',ls='--',label='Prevalence')
        m=(c if j==0 else v)['test'];ax.scatter([m['recall']],[m['precision']],s=34,color='#b33f36',label='Validation threshold',zorder=4)
        ax.set(title=title,xlabel='Recall',ylabel='Precision',xlim=(-.015,1.015),ylim=(-.02,1.02));ax.legend(fontsize=8)
        ax=axs[1,j];ax.plot(fpr,tpr,color='#125f72',lw=1.6);ax.plot([0,1],[0,1],'--',color='gray')
        ax.set(xlabel='False positive rate',ylabel='True positive rate',xlim=(0,1),ylim=(0,1))
    for ax in axs.flat:ax.spines[['right','top']].set_visible(False);ax.grid(alpha=.16)
    for ext in ['png','pdf']:fig.savefig(RESULT/f'anticipation_curves.{ext}',dpi=200)
    plt.close(fig)
    alarm_times=alarms(test,sc,c['threshold'])
    events=test['events'];used=set();audit=[]
    for a in alarm_times:
        k=next((i for i,e in enumerate(events) if i not in used and .75<=e-a<=2),None)
        if k is not None:used.add(k)
        idx=np.argmin(abs(test['clock']-a))
        audit.append(dict(alert_video_s=test['t'][idx],alert_period_s=a,matched_reference_event_s=events[k] if k is not None else '',
            lead_s=events[k]-a if k is not None else '',score=sc[idx]))
    save_rows(RESULT/'final_alarms.csv',audit)
    strata=[]
    for name,split in [(r[0],r[3]) for r in GAMES]+[('ARG_FRA','test')]:
        g=aligned(name);e,_=reference(name)
        strata.append(dict(match=name,split=split,samples=len(g['y']),sample_minutes=len(g['y'])/120,
            reference_events=len(e),eligible_events=len(g['events']),positive_samples=int(g['y'].sum()),
            fraction_samples_with_pair=float(g['valid'].mean()),positive_fraction_with_pair=float(g['valid'][g['y']==1].mean())))
    save_rows(RESULT/'continuous_splits.csv',strata)
    a=read_rows(RESULT/'all_clips.csv');ev=c['test_events'];ci=c['test_block_95_AP_AUROC'];vci=v['clip_bootstrap_95_AP_AUROC_balacc']
    def ci_prop(k,n):
        i=binomtest(k,n).proportion_ci()
        return f'{i.low:.3f}–{i.high:.3f}'
    lines=['# Forensic Sky-Robotics | Experimental results','',
        'The pipeline estimates player poses, scores approaching interactions, and moves a simulated camera. In a held-out World Cup half, one of 15 alerts fell within the specified window before a logged foul. Visual inspection of that alert shows player contact already in progress. Reliable anticipation of first physical contact and improved officiating remain unproven.','',
        '## Continuous World Cup foul forecasting','',
        'Each sample uses only video available at that instant. A positive sample falls 0.75–2.00 seconds before a StatsBomb Foul Committed timestamp. A threshold crossing can match one event. The alarm rearms after a below-threshold observation and has a two-second refractory interval. Time gaps and detected shot changes reset state. Pre-match programming, halftime and unmatched clock intervals are excluded. Stoppages, replay shots embedded in the aligned broadcast and frames with insufficient player pairs remain in the evaluation.','',
        '| Match | Split | Sample minutes | Fouls | Positive / total samples | Samples with a pair |',
        '|---|---|---:|---:|---:|---:|']
    for r in strata:lines.append(f"| {r['match']} | {r['split']} | {r['sample_minutes']:.2f} | {r['eligible_events']} | {r['positive_samples']} / {r['samples']} | {r['fraction_samples_with_pair']:.1%} |")
    lines+=['','Four matches trained the continuous model. Two separate matches selected the model and threshold by event F1 under a ceiling of one false alert per minute, breaking ties by average precision. The Argentina–France final supplied the test half. All seven matches are absent from the 39-match SportsD collection. All 97 recorded second-half fouls have an eligible observation window in these broadcasts.','',
        '| Validation candidate | Average precision | Event F1 | False alerts/min |','|---|---:|---:|---:|']
    for k,h in c['validation_candidates'].items():lines.append(f"| {k} | {h['AP']:.4f} | {h['event']['F1']:.4f} | {h['event']['false_alarms_per_min']:.3f} |")
    lines+=['',f"The selected model uses standardized pose and motion features with L2-regularized logistic regression (C = 0.0005). Its frozen threshold is {c['threshold']:.6f}.",
        '', '| Final event metric | Result |','|---|---:|',
        f"| Matched alerts / false alerts / missed events | {ev['TP']} / {ev['FP']} / {ev['FN']} |",
        f"| Precision (exact binomial 95% interval) | {fmt(ev['precision'])} ({ci_prop(ev['TP'],ev['TP']+ev['FP'])}) |",
        f"| Recall (exact binomial 95% interval) | {fmt(ev['recall'])} ({ci_prop(ev['TP'],ev['events'])}) |",
        f"| F1 | {fmt(ev['F1'])} |",f"| False alerts per sample-minute | {fmt(ev['false_alarms_per_min'])} |",
        f"| Lead against event clock, one matched alert | {fmt(ev['median_lead_seconds'])} s |",
        '', 'Confidence intervals for the alert counts are descriptive and assume independent trials. The sample-level intervals below resample one-minute blocks within the final. Neither interval measures uncertainty across future matches.',
        '', '| Sample metric | Continuous final | Supplementary clip model |','|---|---:|---:|']
    for k,title in [('n','Samples'),('positives','Positive samples'),('AP','Average precision'),('AUROC','ROC AUC'),('precision','Precision'),('recall','Recall'),('F1','F1'),('accuracy','Accuracy'),('balanced_accuracy','Balanced accuracy'),('Brier','Brier score')]:
        x,y=c['test'][k],v['test'][k];lines.append(f'| {title} | {x} | {y} |' if k in ('n','positives') else f'| {title} | {x:.4f} | {y:.4f} |')
    for title,vals in [('Specificity',[(c['test']['confusion'][0][0]/sum(c['test']['confusion'][0])),(v['test']['confusion'][0][0]/sum(v['test']['confusion'][0]))]),
            ('Matthews correlation',[matthews_corrcoef(yc,sc>=c['threshold']),matthews_corrcoef(yv,sv>=v['threshold'])]),
            ('Positive prevalence / constant-score AP',[yc.mean(),yv.mean()])]:
        lines.append(f'| {title} | {vals[0]:.4f} | {vals[1]:.4f} |')
    lines+=['',f"Final confusion counts (TN, FP, FN, TP) are {c['test']['confusion'][0]+c['test']['confusion'][1]}. Always predicting ordinary play yields {1-yc.mean():.2%} accuracy and zero foul recall. The 95% block-bootstrap intervals are {ci[0][0]:.4f}–{ci[1][0]:.4f} for average precision and {ci[0][1]:.3f}–{ci[1][1]:.3f} for ROC AUC.",
        '',f"The closing-speed and proximity baseline had test AP {c['closing_baseline']['test_AP']:.4f} and matched no events, with {c['closing_baseline']['test_events']['FP']} false alarms. Shifting the reference times by −1, −0.5, 0, +0.5 and +1 second yields respectively 0, 0, 1, 1 and 0 matched events. The single nominal hit occurs at video time 2491.0 s, during an ongoing challenge. The event-clock result alone cannot establish physiological or refereeing lead time.",
        '', '![Precision–recall and ROC curves](anticipation_curves.png)','',
        '## Short clips and dataset coverage','',
        f"All {len(a):,} clips were decoded, processed at 2 Hz and scored with the deployed model ({sum(int(r['observations']) for r in a):,} sampled frames, {sum(float(r['seconds']) for r in a)/60:.1f} minutes). SportsD supplies 726 World Cup on-ball decision clips. Its training split supplied background examples sufficiently distant from a recorded foul. CAS-FD supplies 600 foul/dive clips. Exact hashes and four-frame perceptual comparisons identified repeated footage. After grouping there were 351 training, 98 validation and 95 test clips. Source match identity is unavailable for CAS-FD, so additional same-match or alternative-angle overlap remains possible.",
        '',f"CAS-FD supplies clip labels only. For its auxiliary benchmark the model sees frames up to {v.get('cutoff',1.5):.1f} s into the clip (≥1 s candidates). {v['selected']} won on validation AP among the expanded model grid. Test accuracy {v['test']['accuracy']:.1%}, balanced accuracy {v['test']['balanced_accuracy']:.1%}, precision {v['test']['precision']:.1%}, recall {v['test']['recall']:.1%}, F1 {v['test']['F1']:.3f}, ROC AUC {v['test']['AUROC']:.3f}. The 95% clip-bootstrap AP interval was {vci[0][0]:.3f}–{vci[1][0]:.3f}. The kinematic baseline AP was {v['proximity_closing_baseline_test_AP']:.3f}. In positive clips the later prefix outranked the 0.5 s prefix only {v['within_foul_later_ranks_above_early']:.1%} of the time, counting ties as one half.",
        '',f"The continuous model applied to these same held-out clip prefixes obtained AP {d['clip_prefix']['AP']:.3f} and recall {d['clip_prefix']['recall']:.1%}. On {d['quiet_test_minutes']:.1f} minutes of held-out World Cup short clips distant from a logged foul it raised {d['quiet_test_alarms']} alerts ({d['quiet_test_alarms_per_min']:.2f}/min). Distant-event selection is a background proxy. Pooling those clips with the final would mix different sampling designs.",
        '', '## Camera placement before contact','',
        'A visual audit marked coarse onset brackets and future contact locations in 21 retained foul clips and four clearly visible challenges in the final. These are single-observer, visibility-selected annotations. At the last observation at least 0.5 s before the lower onset bound, freeze each camera and test whether the later annotated point falls in view. An early alert lies at least 0.5 s before the lower bound and at most 3.5 s before the upper bound. Exclude intervening shot changes from geometric comparison. Framed-and-clear means the 3D sightline to the point avoids modeled player bodies. All three cameras start from the same pose. The survey camera follows the median player position.',
        '', '| Source | Early alerts / reviewed | Comparable views | Planned framed and clear | Survey framed and clear | Fixed framed and clear |',
        '|---|---:|---:|---:|---:|---:|']
    for k,title in [('clip_review','CAS-FD'),('final_review','Final')]:
        z=cam[k];lines.append(f"| {title} | {z['early_alerts']} / {z['events']} | {z['same_shot_events']} | {z['planned']['framed_clear']} | {z['survey']['framed_clear']} | {z['fixed']['framed_clear']} |")
    lines+=['','In the one early-alert clip, the predicted region was 6.2% of the normalized unit-square diagonal from the visually marked point. In the final audit all early-alert checks were negative. On the comparable final events the peak modeled speed and acceleration through the assessment times reached 7 and 4 scene units/s and scene units/s². The planned camera showed no consistent visibility advantage. Ground-plane geometry is approximate and ignores broadcast panning between frames. Camera outcomes are simulator measurements. Ground-truth offender/victim track IDs, physical camera paths, multi-view visibility and referee verdicts are unavailable for these events, so actor-ID precision, physical view IoU and decision fairness remain unmeasured.',
        '', '## External football pose evaluation','',
        'KTH Multiview Football Dataset II supplies synchronized images, 2D labels, fitted 3D joints and orthographic cameras. The official reconstruction uses a unit cube. Errors below are expressed in torso lengths. An absolute error in millimetres would require a metric scale. The 12 common shoulder, elbow, wrist, hip, knee and ankle joints are evaluated on every image of both player-2 sequences. The pipeline matches the subject at box IoU ≥ 0.30. Coverage counts failures. PCK uses 20% of projected torso length and the all-image average counts missing bodies as zero. The 3D errors average over returned poses. MPJPE uses hip centering, camera coordinates and torso normalization. PA-MPJPE permits a similarity transform.',
        '', '| Sequence | Pose input | Returned / images | All-image 2D PCK | Normalized MPJPE | Normalized PA-MPJPE |',
        '|---|---|---:|---:|---:|---:|']
    for i,name in [('1','Run and sidestep'),('2','Sliding tackle')]:
        z=pose[i]
        for k,title in [('wide_only','Wide-field proposals'),('pipeline','Wide field + close-up'),('annotated_crop','Annotated player box')]:
            h=z[k];lines.append(f"| {name} | {title} | {h['returned']} / {z['images']} | {h['PCK20_including_misses']:.3f} | {fmt(h.get('torso_MPJPE'))} | {fmt(h.get('torso_PA_MPJPE'))} |")
    lines+=['','The run-and-sidestep sequence exposed the original close-up failure and informed the rendering change. The sliding-tackle sequence was reserved as a follow-up check. Both feature the same player. These results quantify pose estimation on KTH imagery. The close-up display pass supplements the fitted wide-field forecasting input; the Qatar results above use the frozen forecasting pipeline.',
        '', '## Data and reproducibility','',
        'The trained weights, original video manifests, event-clock anchors, sample-level predictions and per-event camera measurements are included in the project. The README lists the reproduction commands. Individual scores include validation and training rows clearly identified by their split. The model never receives future frames, event logs, camera annotations, filenames or scoreboards as numerical inputs. The original broadcast view itself can still correlate with an impending event.',
        '', 'Sources include [SportsD](https://huggingface.co/datasets/addisonwu05/sportsd), [CAS-FD](https://huggingface.co/datasets/jahid114593/foul-vs-dive-dataset), [StatsBomb Open Data](https://github.com/statsbomb/open-data), the [archived final](https://archive.org/details/argentina-vs-france-fifa-world-cup-2022-final), and the [KTH football benchmark](https://www.csc.kth.se/cvap/cvg/?page=footballdataset2). The other six full-broadcast URLs and checksums are in the [source manifest](../datasets/broadcast_halves/manifest.json). Cite Kazemi, Burenius, Azizpour and Sullivan, *Multi-view Body Part Recognition with Random Forests*, BMVC 2013, for KTH.']
    (RESULT/'REPORT.md').write_text('\n'.join(lines).replace('input; the Qatar','input. The Qatar')+'\n',encoding='utf8')
if __name__=='__main__':main()

