import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Compare graph forecasts by validation AP, keeping the test matches for reporting."""
import json
import numpy as np
import torch
from sklearn.metrics import average_precision_score,precision_recall_curve,precision_score,recall_score
from graph_model import GraphForecast
from learning import training_data
from prepare import ROOT,OUT

def main():
    torch.manual_seed(42)
    torch.set_num_threads(3)
    seq,y,split=training_data(graph=True)
    # Use batches to keep memory bounded on the demonstration laptop.
    def batch(idx):
        return tuple(torch.from_numpy(np.stack([seq[i][j] for i in idx])) for j in (0,1))
    def predict(indices):
        model.eval()
        with torch.no_grad():
            return np.concatenate([model(*batch(idx)).sigmoid().numpy() for idx in np.array_split(indices,max(1,len(indices)//192))])
    model=GraphForecast()
    optim=torch.optim.AdamW(model.parameters(),lr=.001)
    train,val,test=[np.flatnonzero(split==s) for s in ('train','validation','test')]
    rng=np.random.default_rng(42)
    loss=torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(6.))
    best=-1; best_state=None
    for epoch in range(7):
        model.train()
        for idx in np.array_split(rng.permutation(train),max(1,len(train)//192)):
            optim.zero_grad()
            loss(model(*batch(idx)),torch.tensor(y[idx],dtype=torch.float32)).backward()
            optim.step()
        pv=predict(val);ap=average_precision_score(y[val],pv)
        if ap>best:
            best=ap;best_state={k:v.detach().clone() for k,v in model.state_dict().items()}
    model.load_state_dict(best_state)
    torch.save(best_state,ROOT/'models/graph.pt')
    pv=predict(val);pt=predict(test)
    p,r,th=precision_recall_curve(y[val],pv)
    threshold=float(th[np.argmax((2*p*r/(p+r+1e-10))[:-1])])
    base=json.loads((OUT/'evaluation.json').read_text())
    report=dict(selected='graph' if best>max(base['validation_AP'].values()) else base['selected'],graph_validation_AP=best,
        graph_threshold=threshold,graph_test_AP=float(average_precision_score(y[test],pt)),
        graph_test_precision=float(precision_score(y[test],pt>=threshold)),graph_test_recall=float(recall_score(y[test],pt>=threshold)))
    (OUT/'model_selection.json').write_text(json.dumps(report,indent=2))
    print(report)
if __name__=='__main__': main()

