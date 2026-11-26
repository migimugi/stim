"""1試行のDEMエラー成分とPyMatchingの復号経路を比較する。

実行: python plot_matching_trial.py --project /Users/hiroseminagi/Documents/stim
必要: stim, pymatching, numpy, matplotlib, plotly
DEMのサンプルであり、物理ゲート単位の発生履歴ではない。
"""
import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pymatching
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def canonical(a,b):
    return (a,-1) if b in (-1,None) else tuple(sorted((a,b)))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent/'matching_visualization')
    args=parser.parse_args()
    sys.path.insert(0,str(args.project.resolve()))
    from memory import MemoryCircuitBuilder
    out=args.output.resolve(); out.mkdir(parents=True,exist_ok=True)
    circuit=MemoryCircuitBuilder(distance=3,rounds=3,p_data=0.01).build()
    dem=circuit.detector_error_model(decompose_errors=True)
    matcher=pymatching.Matching.from_detector_error_model(dem)
    events,observables,errors=dem.compile_sampler(seed=42).sample(100,return_errors=True)
    shot=5
    terms=[i for i in dem.flattened() if i.type=='error']
    actual=set(); fired=[]
    for k in np.flatnonzero(errors[shot]):
        inst=terms[int(k)]; fired.append(str(inst))
        for group in inst.target_groups():
            ds=[t.val for t in group if t.is_relative_detector_id()]
            if not ds: continue
            if len(ds)>2: raise ValueError('Graphlike decomposition required')
            edge=canonical(ds[0],ds[1] if len(ds)==2 else -1)
            if edge in actual: actual.remove(edge)
            else: actual.add(edge)
    predicted={canonical(int(a),int(b)) for a,b in matcher.decode_to_edges_array(events[shot])}
    active=set(int(i) for i in np.flatnonzero(events[shot]))
    coords={int(k):v for k,v in circuit.get_detector_coordinates().items()}
    background={canonical(a,b) for a,b,_ in matcher.edges() if b is not None}
    prediction=int(matcher.decode(events[shot])[0]); truth=int(observables[shot,0])
    for edges in (actual,predicted):
        endpoints=set()
        for a,b in edges:
            for q in (a,b):
                if q==-1:continue
                if q in endpoints:endpoints.remove(q)
                else:endpoints.add(q)
        assert endpoints==active
    assert prediction==truth
    time_values={coords[d][2] for d in active}
    assert len(time_values)==1
    selected_time=next(iter(time_values))

    # Bは仮想境界の記号。短い枝の先端の位置には物理的な意味を持たせない。
    def endpoints(edge):
        a,b=edge; p=coords[a]
        return p,coords[b] if b!=-1 else [p[0]+1.2,p[1]+0.65,p[2]]

    font='/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
    font_manager.fontManager.addfont(font)
    plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name()
    plt.rcParams['font.size']=12
    orange='#ba5200'; blue='#2557ba'; grey='#d6dce2'
    titles=['発生したエラー（DEMの成分）','復号器が選んだエッジ']
    for kind in ['3d','round']:
        fig=plt.figure(figsize=(13,6.8 if kind=='3d' else 6.3),facecolor='white')
        for panel,(edges,color,title) in enumerate(zip((actual,predicted),(orange,blue),titles),start=1):
            ax=fig.add_subplot(1,2,panel,projection='3d' if kind=='3d' else None)
            ax.set_title(title,pad=18,fontweight='bold')
            displayed=[i for i in coords if kind=='3d' or coords[i][2]==selected_time]
            for edge in background:
                p,q=endpoints(edge)
                if kind=='round' and (p[2]!=selected_time or q[2]!=selected_time):continue
                v=np.array([p,q])
                if kind=='3d':ax.plot(v[:,0],v[:,1],v[:,2],color=grey,lw=.8,alpha=.65)
                else:ax.plot(v[:,0],v[:,1],color=grey,lw=1,zorder=1)
            ps=np.array([coords[i] for i in displayed])
            if kind=='3d':ax.scatter(ps[:,0],ps[:,1],ps[:,2],c=grey,s=15,depthshade=False)
            else:ax.scatter(ps[:,0],ps[:,1],c=grey,s=35,zorder=2)
            for edge in sorted(edges):
                p,q=endpoints(edge); v=np.array([p,q])
                style='-' if panel==1 else '--'
                if kind=='3d':ax.plot(v[:,0],v[:,1],v[:,2],color=color,lw=3.5,ls=style)
                else:ax.plot(v[:,0],v[:,1],color=color,lw=3.5,ls=style,zorder=3)
                if edge[1]==-1:
                    if kind=='3d':ax.scatter(*q,marker='s',color=color,s=35);ax.text(q[0]+.1,q[1]+.1,q[2],'B',color=color)
                    else:ax.scatter(q[0],q[1],marker='s',color=color,s=50,zorder=4);ax.text(q[0]+.12,q[1]+.1,'B',color=color)
            for i in sorted(active):
                x,y,t=coords[i]
                if kind=='3d':ax.scatter(x,y,t,color='#171717',s=48,depthshade=False);ax.text(x+.1,y+.1,t+.08,f'D{i}',fontsize=10)
                else:ax.scatter(x,y,color='#171717',s=70,zorder=5);ax.annotate(f'D{i}',(x,y),xytext=(6,-17),textcoords='offset points',fontsize=12)
            ax.set_xlabel('x');ax.set_ylabel('y');ax.set_xlim(-2,6);ax.set_ylim(-2,6.3)
            if kind=='3d':
                ax.set_zlabel('round_index（時間）');ax.set_zlim(-.1,3.3);ax.set_zticks([0,1,2,3]);ax.view_init(elev=24,azim=-56)
                ax.set_box_aspect((1,1,.8))
            else:
                ax.set_aspect('equal');ax.set_xticks(range(-1,6,2));ax.set_yticks(range(-1,6,2));ax.grid(alpha=.15)
        fig.suptitle(f'距離3・3ラウンド・p = 0.01 ｜ 試行 {shot+1}（index {shot}）',fontsize=16,y=.97)
        fig.text(.5,.055,'黒点：反応した検出器　 灰色：候補エッジ　 B：仮想境界（表示位置は便宜的）',ha='center',fontsize=11)
        fig.text(.5,.018,f'経路は異なるが、論理反転の実値 {truth} ／ 予測 {prediction} → 復号成功'+('　｜　3ラウンド目（t = 2）を拡大' if kind=='round' else ''),ha='center',fontsize=12)
        fig.subplots_adjust(left=.05,right=.94,bottom=.17,top=.85,wspace=.16)
        fig.savefig(out/f'matching_{kind}.png',dpi=180)
        plt.close(fig)

    fig=make_subplots(rows=1,cols=2,specs=[[{'type':'scene'},{'type':'scene'}]],subplot_titles=titles)
    for col,(edges,color) in enumerate(zip((actual,predicted),(orange,blue)),start=1):
        for group,groupcolor,width,dash,label in [(background,'#d6dce2',2,'solid','候補エッジ'),(edges,color,7,'solid' if col==1 else 'dash','発生エラー' if col==1 else '復号経路')]:
            xs=[];ys=[];zs=[]
            for edge in sorted(group):
                p,q=endpoints(edge)
                xs.extend([p[0],q[0],None]);ys.extend([p[1],q[1],None]);zs.extend([p[2],q[2],None])
            fig.add_trace(go.Scatter3d(x=xs,y=ys,z=zs,mode='lines',line=dict(color=groupcolor,width=width,dash=dash),name=label,showlegend=False,hoverinfo='skip'),row=1,col=col)
        for selected in [False,True]:
            ids=[i for i in coords if (i in active)==selected]
            fig.add_trace(go.Scatter3d(x=[coords[i][0] for i in ids],y=[coords[i][1] for i in ids],z=[coords[i][2] for i in ids],mode='markers+text' if selected else 'markers',text=[f'D{i}' for i in ids],textposition='top center',marker=dict(size=6 if selected else 2,color='#171717' if selected else '#c4cbd3'),customdata=[coords[i] for i in ids],hovertemplate='%{text}<br>x=%{x}, y=%{y}, t=%{z}<extra></extra>',showlegend=False),row=1,col=col)
        for edge in edges:
            if edge[1]==-1:
                _,q=endpoints(edge)
                fig.add_trace(go.Scatter3d(x=[q[0]],y=[q[1]],z=[q[2]],mode='markers+text',text=['B'],marker=dict(symbol='square',size=5,color=color),hovertemplate='仮想境界（位置は表示用）<extra></extra>',showlegend=False),row=1,col=col)
    scene=dict(xaxis=dict(title='x',range=[-2,6]),yaxis=dict(title='y',range=[-2,6.3]),zaxis=dict(title='round_index',range=[-.1,3.3],dtick=1),aspectmode='manual',aspectratio=dict(x=1,y=1,z=.8))
    fig.update_layout(title=f'試行 {shot+1}：発生したDEMエラーと復号経路 ／ 論理反転 実値 {truth}・予測 {prediction}',scene=scene,scene2=scene,height=740,margin=dict(l=15,r=15,b=80,t=90),paper_bgcolor='white',font=dict(size=14))
    fig.add_annotation(x=.5,y=-.08,xref='paper',yref='paper',text='ドラッグで回転・スクロールで拡大。Bは仮想境界。物理ゲート単位のエラー履歴ではなく、DEMのサンプル。',showarrow=False)
    fig.write_html(out/'matching_3d.html',include_plotlyjs=True,config={'scrollZoom':True})
    payload=dict(shot_index=shot,seed=42,batch_size=100,model='distance=3 rounds=3 p_data=0.01',fired_dem_errors=fired,actual_edges=sorted(actual),predicted_edges=sorted(predicted),active_detectors=sorted(active),actual_observable=truth,predicted_observable=prediction,coordinates=coords)
    (out/'trial.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:payload[k] for k in ['actual_edges','predicted_edges','active_detectors','actual_observable','predicted_observable']},ensure_ascii=False))
    print(out)


if __name__=='__main__':
    main()
