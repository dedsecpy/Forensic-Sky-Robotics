import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Generate all final-result PNG plots from saved metrics and predictions."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import precision_recall_curve,roc_curve,confusion_matrix,ConfusionMatrixDisplay
from fit_video import RESULT,read_rows
from prepare import ROOT

OUT=RESULT/'plots'
TEAL='#125f72';RED='#b33f36';AMBER='#995521';GRAY='#6b6b6b';GREEN='#2f6b4f'

def load(name):return json.loads((RESULT/name).read_text())
def cols(file,keys):
    rows=read_rows(RESULT/file)
    return tuple(np.array([float(r[k]) for r in rows]) for k in keys)
def save(fig,name):
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/f'{name}.png'
    fig.savefig(path,dpi=220,bbox_inches='tight',facecolor='white')
    plt.close(fig)
    print('wrote',path)

def style(ax):
    ax.spines[['right','top']].set_visible(False)
    ax.grid(alpha=.18,linestyle='--')

def bar_metrics(ax,metrics,title,color=TEAL):
    labels=list(metrics);vals=[metrics[k] for k in labels]
    bars=ax.bar(range(len(labels)),vals,color=color,edgecolor='white')
    ax.set_xticks(range(len(labels)),labels,rotation=25,ha='right')
    ax.set_ylim(0,1.05);ax.set_title(title)
    for b,v in zip(bars,vals):ax.text(b.get_x()+b.get_width()/2,v+.02,f'{v:.3f}',ha='center',va='bottom',fontsize=8)
    style(ax)

def plot_confusion(cm,title,name,labels=('Neg','Pos')):
    fig,ax=plt.subplots(figsize=(4.8,4.2),layout='constrained')
    disp=ConfusionMatrixDisplay(confusion_matrix=np.asarray(cm),display_labels=labels)
    disp.plot(ax=ax,cmap='Blues',colorbar=False,values_format='d')
    ax.set_title(title);save(fig,name)

def plot_roc_pr(y,s,th,title_prefix,stem):
    y=np.asarray(y);s=np.asarray(s)
    p,r,_=precision_recall_curve(y,s);fpr,tpr,_=roc_curve(y,s)
    pred=s>=th;cm=confusion_matrix(y,pred,labels=[0,1])
    # PR
    fig,ax=plt.subplots(figsize=(5.2,4.2),layout='constrained')
    ax.step(r,p,where='post',lw=2,color=TEAL)
    ax.axhline(y.mean(),color=AMBER,ls='--',label=f'Prevalence {y.mean():.3f}')
    ax.scatter([pred[y==1].mean() if y.sum() else 0],[pred[y==0].mean() and (pred&(y==1)).sum()/max(1,pred.sum())],s=1,alpha=0)
    # operating point from threshold
    tp=((s>=th)&(y==1)).sum();fp=((s>=th)&(y==0)).sum();fn=((s<th)&(y==1)).sum()
    prec=tp/max(1,tp+fp);rec=tp/max(1,tp+fn)
    ax.scatter([rec],[prec],s=55,color=RED,zorder=4,label='Operating point')
    ax.set(title=f'{title_prefix} — Precision–Recall',xlabel='Recall',ylabel='Precision',xlim=(-.02,1.02),ylim=(-.02,1.02))
    ax.legend(fontsize=8);style(ax);save(fig,f'{stem}_pr')
    # ROC
    fig,ax=plt.subplots(figsize=(5.2,4.2),layout='constrained')
    ax.plot(fpr,tpr,lw=2,color=TEAL,label='ROC')
    ax.plot([0,1],[0,1],'--',color=GRAY)
    fpr_op=fp/max(1,(y==0).sum());tpr_op=tp/max(1,(y==1).sum())
    ax.scatter([fpr_op],[tpr_op],s=55,color=RED,zorder=4,label='Operating point')
    ax.set(title=f'{title_prefix} — ROC',xlabel='False positive rate',ylabel='True positive rate',xlim=(0,1),ylim=(0,1))
    ax.legend(fontsize=8);style(ax);save(fig,f'{stem}_roc')
    plot_confusion(cm,f'{title_prefix} — Confusion matrix',f'{stem}_confusion')
    # score histograms
    fig,ax=plt.subplots(figsize=(5.6,4.0),layout='constrained')
    ax.hist(s[y==0],bins=28,alpha=.65,color=GRAY,label='Negative',density=True)
    ax.hist(s[y==1],bins=28,alpha=.65,color=TEAL,label='Positive',density=True)
    ax.axvline(th,color=RED,ls='--',lw=1.6,label=f'Threshold {th:.3f}')
    ax.set(title=f'{title_prefix} — Score distributions',xlabel='Score',ylabel='Density')
    ax.legend(fontsize=8);style(ax);save(fig,f'{stem}_scores')

def main():
    v=load('video_metrics.json');c=load('continuous_metrics.json')
    cam=load('camera_metrics.json');pose=load('pose_metrics.json');d=load('deployment_clips_metrics.json')
    yc,sc=cols('half_ARG_FRA.csv',['label','score'])
    yv,sv=cols('test_prefix_predictions.csv',['label','score'])

    # --- Clip track ---
    plot_roc_pr(yv,sv,v['threshold'],'CAS-FD clip test','clip')
    fig,ax=plt.subplots(figsize=(7.4,4.4),layout='constrained')
    m={
        'Accuracy':v['test']['accuracy'],'Balanced acc.':v['test']['balanced_accuracy'],
        'Precision':v['test']['precision'],'Recall':v['test']['recall'],
        'F1':v['test']['F1'],'AP':v['test']['AP'],'ROC AUC':v['test']['AUROC']
    }
    bar_metrics(ax,m,'CAS-FD held-out test metrics',TEAL);save(fig,'clip_test_metrics')

    fig,ax=plt.subplots(figsize=(7.4,4.4),layout='constrained')
    mv={
        'Accuracy':v['validation']['accuracy'],'Balanced acc.':v['validation']['balanced_accuracy'],
        'Precision':v['validation']['precision'],'Recall':v['validation']['recall'],
        'F1':v['validation']['F1'],'AP':v['validation']['AP'],'ROC AUC':v['validation']['AUROC']
    }
    bar_metrics(ax,mv,'CAS-FD validation metrics',GREEN);save(fig,'clip_val_metrics')

    # Prefix sensitivity
    cuts=sorted(v['prefix_sensitivity'],key=float)
    fig,ax=plt.subplots(figsize=(7.2,4.4),layout='constrained')
    for key,color in [('F1',TEAL),('accuracy',GREEN),('AUROC',AMBER),('AP',RED)]:
        ax.plot([float(c) for c in cuts],[v['prefix_sensitivity'][c][key] for c in cuts],marker='o',lw=2,label=key,color=color)
    ax.set(title='CAS-FD prefix-length sensitivity (test)',xlabel='Prefix cutoff (s)',ylabel='Score',ylim=(0,1))
    ax.legend();style(ax);save(fig,'clip_prefix_sensitivity')

    # Top validation AP candidates
    items=sorted(v['validation_AP'].items(),key=lambda kv:kv[1],reverse=True)[:12]
    fig,ax=plt.subplots(figsize=(8.5,4.8),layout='constrained')
    ax.barh([k for k,_ in items][::-1],[x for _,x in items][::-1],color=TEAL)
    ax.set(title='Top validation average precision by model@cutoff',xlabel='Validation AP')
    style(ax);save(fig,'clip_val_ap_candidates')

    # Dataset split counts
    counts=v['counts']
    fig,axes=plt.subplots(1,3,figsize=(9.5,3.8),layout='constrained',sharey=True)
    for ax,split,title in zip(axes,('train','val','test'),('Train','Validation','Test')):
        foul=counts.get(f'{split}_foul',0);dive=counts.get(f'{split}_dive',0)
        ax.bar(['Foul','Dive'],[foul,dive],color=[RED,TEAL])
        ax.set_title(f'{title} ({foul+dive})');style(ax)
    fig.suptitle('CAS-FD retained split composition',fontsize=12);save(fig,'clip_split_counts')

    # Bootstrap CI bars
    lo,hi=v['clip_bootstrap_95_AP_AUROC_balacc']
    fig,ax=plt.subplots(figsize=(6.2,4.2),layout='constrained')
    names=['AP','ROC AUC','Balanced acc.']
    centers=[v['test']['AP'],v['test']['AUROC'],v['test']['balanced_accuracy']]
    yerr=np.vstack([np.array(centers)-np.array(lo),np.array(hi)-np.array(centers)])
    ax.bar(names,centers,yerr=yerr,capsize=5,color=TEAL,ecolor=GRAY)
    ax.set(title='CAS-FD test metrics with 95% clip-bootstrap CIs',ylim=(0,1));style(ax);save(fig,'clip_bootstrap_ci')

    # --- Continuous track ---
    plot_roc_pr(yc,sc,c['threshold'],'Continuous ARG–FRA final','continuous')
    fig,ax=plt.subplots(figsize=(7.4,4.4),layout='constrained')
    cm={
        'Accuracy':c['test']['accuracy'],'Balanced acc.':c['test']['balanced_accuracy'],
        'Precision':c['test']['precision'],'Recall':c['test']['recall'],
        'F1':c['test']['F1'],'AP':c['test']['AP'],'ROC AUC':c['test']['AUROC']
    }
    bar_metrics(ax,cm,'Continuous final sample metrics',AMBER);save(fig,'continuous_sample_metrics')

    ev=c['test_events']
    fig,ax=plt.subplots(figsize=(6.8,4.2),layout='constrained')
    em={'Precision':ev['precision'],'Recall':ev['recall'],'F1':ev['F1'],'FA / min':min(1.,ev['false_alarms_per_min'])}
    bar_metrics(ax,em,'Continuous final event metrics',RED);save(fig,'continuous_event_metrics')

    fig,ax=plt.subplots(figsize=(6.2,4.0),layout='constrained')
    ax.bar(['TP','FP','FN'],[ev['TP'],ev['FP'],ev['FN']],color=[GREEN,RED,AMBER])
    ax.set_title('Continuous final alert outcomes');style(ax);save(fig,'continuous_event_counts')

    # Validation candidates
    names=[];aps=[];f1s=[]
    for k,h in c['validation_candidates'].items():
        names.append(k);aps.append(h['AP']);f1s.append(h['event']['F1'])
    order=np.argsort(aps)
    fig,ax=plt.subplots(figsize=(8.0,4.6),layout='constrained')
    x=np.arange(len(names));w=.38
    ax.bar(x-w/2,[aps[i] for i in order],width=w,label='Val AP',color=TEAL)
    ax.bar(x+w/2,[f1s[i] for i in order],width=w,label='Val event F1',color=RED)
    ax.set_xticks(x,[names[i] for i in order],rotation=30,ha='right')
    ax.set_title('Continuous validation candidates');ax.legend();style(ax);save(fig,'continuous_val_candidates')

    # Clock-shift sensitivity
    shifts=sorted(c['event_clock_shift_sensitivity'],key=float)
    fig,ax=plt.subplots(figsize=(6.8,4.0),layout='constrained')
    ax.plot([float(s) for s in shifts],[c['event_clock_shift_sensitivity'][s]['F1'] for s in shifts],marker='o',lw=2,color=TEAL)
    ax.set(title='Event-clock shift sensitivity (test F1)',xlabel='Label shift (s)',ylabel='Event F1',ylim=(0,max(.2,max(c['event_clock_shift_sensitivity'][s]['F1'] for s in shifts)+.05)))
    style(ax);save(fig,'continuous_clock_shift')

    # Score timeline excerpt around alerts if available
    rows=read_rows(RESULT/'half_ARG_FRA.csv')
    t=np.array([float(r['period_s']) for r in rows]);lab=np.array([int(float(r['label'])) for r in rows]);score=np.array([float(r['score']) for r in rows])
    fig,ax=plt.subplots(figsize=(10,3.6),layout='constrained')
    ax.plot(t,score,lw=1.0,color=TEAL,label='Score')
    ax.axhline(c['threshold'],color=RED,ls='--',label='Threshold')
    ax.scatter(t[lab==1],score[lab==1],s=12,color=AMBER,label='Positive frames',zorder=3)
    ax.set(title='Continuous final score timeline',xlabel='Match period time (s)',ylabel='Score')
    ax.legend(fontsize=8,loc='upper right');style(ax);save(fig,'continuous_score_timeline')

    # --- Pose ---
    fig,axes=plt.subplots(1,2,figsize=(9.5,4.2),layout='constrained')
    for ax,(sid,title) in zip(axes,[('1','Run / sidestep'),('2','Sliding tackle')]):
        z=pose[sid]
        modes=['wide_only','pipeline','annotated_crop']
        labels=['Wide only','Wide+close-up','Annotated box']
        pck=[z[m]['PCK20_including_misses'] for m in modes]
        cov=[z[m]['coverage'] for m in modes]
        x=np.arange(len(modes));w=.35
        ax.bar(x-w/2,pck,width=w,label='PCK@0.2',color=TEAL)
        ax.bar(x+w/2,cov,width=w,label='Coverage',color=AMBER)
        ax.set_xticks(x,labels,rotation=15,ha='right');ax.set_ylim(0,1.05);ax.set_title(title);ax.legend(fontsize=8);style(ax)
    fig.suptitle('KTH pose benchmark');save(fig,'pose_pck_coverage')

    # --- Camera ---
    fig,axes=plt.subplots(1,2,figsize=(9.2,4.0),layout='constrained')
    for ax,key,title in zip(axes,('clip_review','final_review'),('CAS-FD reviewed clips','Final reviewed challenges')):
        z=cam[key]
        vals=[z['planned']['framed_clear'],z['survey']['framed_clear'],z['fixed']['framed_clear'],z['early_alerts']]
        ax.bar(['Planned\nclear','Survey\nclear','Fixed\nclear','Early\nalerts'],vals,color=[TEAL,GREEN,AMBER,RED])
        ax.set_title(f'{title} (n={z["events"]})');style(ax)
    fig.suptitle('Virtual camera evaluation');save(fig,'camera_evaluation')

    # --- Deployment continuous-on-clips ---
    fig,ax=plt.subplots(figsize=(7.0,4.2),layout='constrained')
    dm={
        'Accuracy':d['clip_prefix']['accuracy'],'Balanced acc.':d['clip_prefix']['balanced_accuracy'],
        'Precision':d['clip_prefix']['precision'],'Recall':d['clip_prefix']['recall'],
        'F1':d['clip_prefix']['F1'],'AP':d['clip_prefix']['AP'],'ROC AUC':d['clip_prefix']['AUROC']
    }
    bar_metrics(ax,dm,'Continuous model on held-out clip prefixes',GRAY);save(fig,'deployment_clip_metrics')

    # --- Combined overview dashboard ---
    fig,axes=plt.subplots(2,2,figsize=(11,8),layout='constrained')
    bar_metrics(axes[0,0],{
        'Acc':v['test']['accuracy'],'Bal':v['test']['balanced_accuracy'],'P':v['test']['precision'],
        'R':v['test']['recall'],'F1':v['test']['F1'],'AUC':v['test']['AUROC']
    },'Clip test (primary)',TEAL)
    bar_metrics(axes[0,1],{
        'Acc':c['test']['accuracy'],'Bal':c['test']['balanced_accuracy'],'P':c['test']['precision'],
        'R':c['test']['recall'],'F1':c['test']['F1'],'AUC':c['test']['AUROC']
    },'Continuous sample metrics',AMBER)
    bar_metrics(axes[1,0],{'Precision':ev['precision'],'Recall':ev['recall'],'F1':ev['F1']},'Continuous event metrics',RED)
    p,r,_=precision_recall_curve(yv,sv);axes[1,1].step(r,p,where='post',color=TEAL,lw=2)
    axes[1,1].axhline(yv.mean(),color=AMBER,ls='--');axes[1,1].set(title='Clip PR curve',xlabel='Recall',ylabel='Precision',xlim=(0,1),ylim=(0,1));style(axes[1,1])
    fig.suptitle('Forensic Sky-Robotics — final results overview',fontsize=13)
    save(fig,'overview_dashboard')

    # Also refresh the classic 2x2 anticipation curves into plots/
    fig,axs=plt.subplots(2,2,figsize=(9,7),layout='constrained')
    for j,(y,s,title,th,block) in enumerate([(yc,sc,'Continuous World Cup final',c['threshold'],c),(yv,sv,'Foul versus dive clip prefixes',v['threshold'],v)]):
        p,r,_=precision_recall_curve(y,s);fpr,tpr,_=roc_curve(y,s)
        ax=axs[0,j];ax.step(r,p,where='post',lw=1.6,color=TEAL);ax.axhline(y.mean(),color=AMBER,ls='--',label='Prevalence')
        m=block['test'];ax.scatter([m['recall']],[m['precision']],s=40,color=RED,label='Operating point',zorder=4)
        ax.set(title=title,xlabel='Recall',ylabel='Precision',xlim=(-.015,1.015),ylim=(-.02,1.02));ax.legend(fontsize=8);style(ax)
        ax=axs[1,j];ax.plot(fpr,tpr,color=TEAL,lw=1.6);ax.plot([0,1],[0,1],'--',color=GRAY)
        ax.set(xlabel='False positive rate',ylabel='True positive rate',xlim=(0,1),ylim=(0,1));style(ax)
    fig.suptitle('Precision–Recall and ROC (final)',fontsize=12)
    save(fig,'anticipation_curves')
    # keep root copy for REPORT embedding
    fig,axs=plt.subplots(2,2,figsize=(9,7),layout='constrained')
    for j,(y,s,title,th,block) in enumerate([(yc,sc,'Continuous World Cup final',c['threshold'],c),(yv,sv,'Foul versus dive clip prefixes',v['threshold'],v)]):
        p,r,_=precision_recall_curve(y,s);fpr,tpr,_=roc_curve(y,s)
        ax=axs[0,j];ax.step(r,p,where='post',lw=1.6,color=TEAL);ax.axhline(y.mean(),color=AMBER,ls='--',label='Prevalence')
        m=block['test'];ax.scatter([m['recall']],[m['precision']],s=40,color=RED,label='Operating point',zorder=4)
        ax.set(title=title,xlabel='Recall',ylabel='Precision',xlim=(-.015,1.015),ylim=(-.02,1.02));ax.legend(fontsize=8);style(ax)
        ax=axs[1,j];ax.plot(fpr,tpr,color=TEAL,lw=1.6);ax.plot([0,1],[0,1],'--',color=GRAY)
        ax.set(xlabel='False positive rate',ylabel='True positive rate',xlim=(0,1),ylim=(0,1));style(ax)
    fig.savefig(RESULT/'anticipation_curves.png',dpi=220,bbox_inches='tight',facecolor='white');plt.close(fig)
    print('All plots written to',OUT)

if __name__=='__main__':main()
