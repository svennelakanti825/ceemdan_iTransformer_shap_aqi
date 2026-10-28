from pathlib import Path
import os
REPO = Path(__file__).resolve().parents[3]
_OUT = Path(__file__).resolve().parents[1] / 'si_rebuild'
for _d in ('tables', 'figures', 'source_results'):
    (_OUT / _d).mkdir(parents=True, exist_ok=True)
os.chdir(_OUT)
import pandas as pd, numpy as np, shutil, hashlib, json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from scipy.cluster.hierarchy import linkage, leaves_list
class _Results:
 def __truediv__(self, name):
  for d in (REPO/'results'/'02_r1_ext'/'reports', REPO/'results'/'01_baselines', REPO/'results'/'03_bg_check'):
   for p in (d/name, d/Path(name).name):
    if p.exists(): return p
  raise FileNotFoundError(name)
T=_Results(); O=Path('.')
def table(name,caption,label,heads,rows,spec=None,note=''):
 if spec is None:spec='l'+'r'*(len(heads)-1)
 text='\\begin{table}[!htbp]\n\\centering\n\\caption{'+caption+'}\\label{'+label+'}\n\\setlength{\\tabcolsep}{4pt}\n\\begin{tabular}{'+spec+'}\n\\toprule\n'+' & '.join(heads)+' \\\\\n\\midrule\n'
 text+=''.join(' & '.join(map(str,row))+' \\\\\n' for row in rows)
 text+='\\bottomrule\n\\end{tabular}\n'
 if note:text+='\\par\\smallskip\\begin{minipage}{0.98\\linewidth}\\footnotesize '+note+'\\end{minipage}\n'
 text+='\\end{table}\n';(O/'tables'/f'{name}.tex').write_text(text)
f=lambda x,n=3:f'{x:.{n}f}'
base=pd.read_csv(T/'phase1_colab_comparison_metrics.csv'); comp=pd.read_csv(T/'comparison_v2_full.csv'); abl=pd.read_csv(T/'ablation13ch_vs_proposed_lb7.csv');main=pd.read_csv(T/'v2_metrics.csv');ms=pd.read_csv(T/'multiseed_summary_lb7.csv')
models=[]
for _,r in base[base.lookback==7].iterrows():models.append(dict(model='LSTM (Keras)' if r.model=='LSTM' else r.model,r2=r.R2,rmse=r.RMSE,mae=r.MAE,mape=r.MAPE,**{c:r[c] for c in ['r2_pre','mae_pre','r2_lock','mae_lock']}))
for _,r in comp[comp.lookback==7].iterrows():
 name={'CEEMDAN+iTransformer-v2':'CEEMDAN+iTransformer','iTransformer':'Plain iTransformer','LSTM':'LSTM (PyTorch)'}.get(r.model,r.model)
 models.append(dict(model=name,**{c:r[c] for c in ['r2','rmse','mae','mape','r2_pre','mae_pre','r2_lock','mae_lock']}))
print('Model labels',[(r['model'],r['r2']) for r in models])
models=sorted(models,key=lambda r:-r['r2'])
table('performance','Next-day AQI forecasting on 6,171 test windows from 18 cities, using a 7-day lookback. All entries are single runs with model seed 123.','tab:performance',['Model','$R^2$','RMSE','MAE','MAPE (\\%)'],[[r['model'],f(r['r2'],4),f(r['rmse'],2),f(r['mae'],2),f(r['mape'],2)] for r in models],note='RMSE and MAE are in AQI units. The Keras and PyTorch LSTMs are distinct implementations. These are implementation comparisons, not capacity-matched or equally tuned architecture comparisons.')
short=['CEEMDAN+iTransformer','Plain iTransformer','Raw-AQI history ablation']
table('seeds','Model-seed variability at a 7-day lookback. Mean $\\pm$ sample standard deviation over five model seeds; the main CEEMDAN realisation is fixed.','tab:seeds',['Model','$R^2$','RMSE','MAE'],[[short[i]]+[f"${r['mean_'+c]:.3f} \\pm {r['std_'+c]:.3f}$" for c in ['r2','rmse','mae']] for i,(_,r) in enumerate(ms.iterrows())])
table('lookback','Lookback selection and test performance of the augmented model. The 7-day lookback is selected by validation $R^2$; 30 days is the second-best validation configuration.','tab:lookback',['Lookback','Validation $R^2$','Test $n$','Test $R^2$','RMSE','MAE'],[[int(r.lookback),f(r.val_r2,4),int(r.n_pre+r.n_lock),f(r.r2,4),f(r.rmse,2),f(r.mae,2)] for _,r in main.iterrows()],note='Each row is a single run. Eligible target sets differ with lookback; these rows are not a matched-target significance test.')
table('period_performance','Forecast performance before restrictions and during lockdown/Unlock. Single runs at lookback 7, model seed 123.','tab:periodperformance',['Model','Pre $R^2$','Pre MAE','Later $R^2$','Later MAE'],[[r['model'],f(r['r2_pre']),f(r['mae_pre'],2),f(r['r2_lock']),f(r['mae_lock'],2)] for r in models],note='Pre: 1 July 2019--24 March 2020 ($n=4,502$). Later: 25 March--1 July 2020 ($n=1,669$). This calendar contrast does not estimate a causal lockdown effect.')
attr=pd.read_csv(T/'shap/shap8_attribution_matrix_lb7.csv',index_col=0);share=100*attr.div(attr.sum(axis=1),axis=0);channels=attr.columns[-5:];osc=share[channels[:4]].sum(axis=1);dec=share[channels].sum(axis=1);slow=share[channels[-1]]
summary=pd.DataFrame({'decomposition_share_pct':dec,'oscillatory_share_pct':osc,'slow_share_pct':slow,'slow_within_decomposition_pct':100*slow/dec});summary.to_csv(O/'source_results/derived_attribution_shares.csv')
table('attribution','Channel attribution shares for the eight-city subset. Values are percentages of the sum of mean absolute channel SHAP values.','tab:attribution',['City','Pollutants','IMF1--4','Slow','All decomp.'],[[c,f(100-dec[c],2),f(osc[c],2),f(slow[c],2),f(dec[c],2)] for c in attr.index],note='Past PM$_{2.5}$ is the highest-attribution channel in every city. The slow channel represents 77.9--94.7\\% of decomposition attribution. These shares are model explanations, not physical source fractions or fractions of forecast variance.')
cond=pd.read_csv(T/'r116_conditioning_runs_lb7.csv');labels={'bias':'Scalar bias','none':'No city term','scale_bias':'Scale and bias','vector_bias':'City vector and bias'}
table('conditioning','City-conditioning sensitivity at model seed 123 and lookback 7.','tab:conditioning',['Conditioning','Validation $R^2$','Test $R^2$','Test MAE'],[[labels[r.conditioning],f(r.val_r2,4),f(r.test_r2,4),f(r.test_mae,2)] for _,r in cond[cond.seed==123].iterrows()],note='The retained scalar bias follows the specified validation rule. Alternatives have one model seed each. The no-city-term arm is a diagnostic, not a candidate in the nested scale-versus-bias selection rule.')
# SI data tables, readable blocks rather than a single overwide table.
dat=pd.read_csv(REPO/'analyses'/'e1_verification'/'outputs'/'data_audit.csv');d=dat[dat.train>0]
table('coverage','Raw record coverage and AQI completeness for the 20 originally included cities; 18 are modelled under the revised protocol.','tab:coverage',['City','First raw date','First AQI date','Valid AQI','Missing (\\%)','Max gap'],[[r.city,r.raw_start,r.first_valid,int(r.valid_aqi),f(r.missing_aqi_pct,1),int(r.longest_gap)] for _,r in dat[(dat.train>0)|dat.city.isin(['Coimbatore','Guwahati'])].iterrows()],spec='lllrrr',note='All raw records end on 1 July 2020. Last valid AQI is 1 July 2020 except Brajrajnagar (12 June 2020) and Coimbatore (30 June 2020). Coimbatore and Guwahati have no training windows and are excluded from model fitting and forecast evaluation. Missing percentages and maximum gaps refer to the daily calendar between first and last valid AQI, excluding leading/trailing missingness. Full raw-row missing pollutant percentages are in Tables S3--S4.')
table('windows','Eligible AQI windows and decomposition-history gaps at lookback 7.','tab:windows',['City','Train','Val.','Test','Gap-ended','Compressed'],[[r.city,int(r.train),int(r.validation),int(r.test),int(r.test_filled_origin),int(r.test_history_compressed)] for _,r in d.iterrows()],note='Gap-ended: test windows whose last input day has filled AQI (59 total). Compressed: test windows for which the decomposition history skips at least one unavailable calendar day (2,427 total). These diagnostics were calculated from the archived data and published window rules; no model was retrained.')
pm=pd.read_csv(REPO/'analyses'/'e1_verification'/'outputs'/'pollutant_missing.csv').pivot(index='city',columns='pollutant',values='missing_pct').loc[d.city]
for i,cs in enumerate([['PM2.5','PM10','NO','NO2','NOx','NH3'],['CO','SO2','O3','Benzene','Toluene','Xylene']]):
 table('missing'+str(i),'Missing pollutant values as percentages of each city\'s raw rows before any target filtering or imputation.','tab:missing'+str(i),['City']+cs,[[c]+[f(pm.loc[c,k],1) for k in cs] for c in pm.index])
city=pd.read_csv(T/'r110_main_city_periods_lb7.csv')
table('city_accuracy','Per-city full-year AQI test performance of the augmented model (model seed 123; lookback 7).','tab:cityaccuracy',['City','$n$','$R^2$','RMSE','MAE'],[[r.city,int(r.n),f(r.r2),f(r.rmse,2),f(r.mae,2)] for _,r in city[city.period=='full'].iterrows()])
rows=[]
for c,g in city.groupby('city',sort=False):
 a=g.set_index('period'); rows.append([c,int(a.loc['pre_lockdown','n']),f(a.loc['pre_lockdown','mae'],2),int(a.loc['lockdown_unlock','n']),f(a.loc['lockdown_unlock','mae'],2),f(a.loc['lockdown_unlock','r2'])])
table('city_periods','Per-city AQI errors across the two test periods (model seed 123).','tab:cityperiods',['City','Pre $n$','Pre MAE','Later $n$','Later MAE','Later $R^2$'],rows)
per=pd.read_csv(T/'table8_channel_periods.csv')
for i,cs in enumerate([['IMF1','IMF2','IMF3'],['IMF4','IMF5+ (slow)']]):
 rows=[]
 for c,g in per.groupby('city',sort=False):
  ix=g.set_index('channel');rows.append([c]+[f"{ix.loc[k,'median_d']:.1f} [{ix.loc[k,'p5_d']:.1f}, {ix.loc[k,'p95_d']:.1f}]" for k in cs])
 table('periods'+str(i),'Zero-crossing scale diagnostics across decompositions: median [5th, 95th percentile]. Units are available-sample steps, equalling days only for uninterrupted histories.','tab:periods'+str(i),['City']+[k.replace('IMF5+ (slow)','Slow') for k in cs],rows,note='Statistics pool all available decomposition origins, including training, validation and test. Undefined scales (fewer than two crossings) are omitted. The slow channel is not interpreted as a periodic cycle. Full counts and unrounded diagnostics are in the source CSV.')
s2=pd.read_csv(T/'s2_summary_lb7.csv'); sn={'d1b':'Calendar with short-gap filling','d1a':'Calendar excluding missing days','steps':'Consecutive observations'}
table('gap_sensitivity','Window-construction sensitivity on the same 5,828 test targets. Five model seeds per arm.','tab:gaps',['Construction','$R^2$','RMSE','MAE'],[[sn[r.arm]]+[f"${r['mean_common_'+k]:.3f} \\pm {r['std_common_'+k]:.3f}$" for k in ['r2','rmse','mae']] for _,r in s2.iterrows()],note='The no-fill arm removes filled target-history input days; pollutant imputation and compressed decomposition histories remain. It does not establish end-to-end online validity.')
# Detailed SHAP table: normalize full-precision per-city inputs, not rounded summary.
rows=[]
for k in attr.columns:rows.append([k.replace('PM2.5',r'PM$_{2.5}$').replace('IMF5+ (slow)','Slow')]+[f(share.loc[c,k],3) for c in ['Delhi','Mumbai','Bengaluru']])
table('full_shap','Complete channel attribution shares for the three focus cities at lookback 7 (percent of total mean absolute SHAP).','tab:fullshap',['Channel','Delhi','Mumbai','Bengaluru'],rows,note='Full-precision mean absolute values are supplied in the source results. Shares are calculated before rounding; apparent zeros at three decimals are not evidence of an absent physical effect.')
bg=pd.read_csv(T/'shap/bg_check_summary_lb7.csv')
table('background','Sensitivity to the SHAP training-background sample.','tab:background',['City','Sample','Decomp. (\\%)','IMF1--4 (\\%)','$\\rho$'],[[r.city,r.background,f(r.decomposition_share_pct,2),f(r.imf1_4_share_pct,2),f(r.spearman_rho_vs_original,3)] for _,r in bg.iterrows()],spec='llrrr',note='Each background has 50 windows and each city has the same 100 explained test windows. Both new draws exclude the original background; the two new draws need not be mutually disjoint. $\\rho$ compares all 17 channel ranks with the original background.')
# Verify saved predictions against supplied aggregate results.
pred=np.load(REPO/'results'/'02_r1_ext'/'reports'/'r116_test_predictions_lb7.npz'); yy=pred['y_test']; pp=pred['pred__bias__123'];r2=1-((yy-pp)**2).sum()/((yy-yy.mean())**2).sum();rmse=np.sqrt(np.mean((yy-pp)**2));assert abs(r2-main.iloc[0].r2)<1e-6
print('Prediction check',r2,rmse)
# Figures in vector PDF.
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
def save(fig,name):
 fig.savefig(O/'figures'/f'{name}.pdf',bbox_inches='tight');fig.savefig(O/'figures'/f'{name}.png',dpi=160,bbox_inches='tight');plt.close(fig)
fig,ax=plt.subplots(figsize=(10,4.6));ax.set(xlim=(-.15,10.15),ylim=(0,5));ax.axis('off')
boxes=[(0,3.25,3,1.25,'A  City daily records','12 pollutant channels + AQI\nCommon target-date partitions\nTraining-only scaling'),(3.5,3.25,3,1.25,'B  Historical decomposition','180–365 available samples\n30-step AR boundary extension\nCEEMDAN: first 4 IMFs + slow'),(7,3.25,3,1.25,'C  Forecast input','7 consecutive calendar days\n12 pollutants + 5 components\n17 channels; target = next-day AQI'),(7,0.7,3,1.25,'D  Shared iTransformer','One token per channel\nChannel attention + city bias\nNext-day forecast'),(2.7,0.7,3.5,1.25,'E  Channel-level KernelSHAP','Whole channel histories replaced\n50 background + 100 test windows\nAttribution to model inputs')]
for x,y,w,h,title,body in boxes:
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.02',fc='#f0f4f7',ec='#63798b',lw=1));ax.text(x+.14,y+h-.16,title,va='top',weight='bold',fontsize=9);ax.text(x+.14,y+h-.47,body,va='top',fontsize=8.5,linespacing=1.55)
for a,b in [((3,3.9),(3.5,3.9)),((6.5,3.9),(7,3.9)),((8.5,3.25),(8.5,1.95)),((7,1.3),(6.2,1.3))]:ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=13,color='#37556b'))
ax.text(0,0.13,'Scope: historical-value decomposition; longer gaps are compressed, so scale estimates are sample-based.',fontsize=9,color='#6b3535');save(fig,'pipeline')
# figure 2 stacked shares and clustered heatmap
order=leaves_list(linkage(share.to_numpy(),method='average',metric='euclidean'));order_c=share.index[order]
fig,(ax,hm)=plt.subplots(1,2,figsize=(11,4.8),gridspec_kw={'width_ratios':[1,1.9]})
y=np.arange(8);ax.barh(y,100-dec.loc[order_c],color='#426f8f',label='Pollutants');ax.barh(y,slow.loc[order_c],left=100-dec.loc[order_c],color='#d19b42',label='Slow');ax.barh(y,osc.loc[order_c],left=100-osc.loc[order_c],color='#8c597f',label='IMF1–4');ax.set(yticks=y,yticklabels=order_c,xlim=(0,100),xlabel='Attribution share (%)');ax.invert_yaxis();ax.set_title('a  Attribution by channel family',loc='left',weight='bold');ax.legend(loc='lower center',bbox_to_anchor=(.5,-.3),ncol=3,fontsize=8,frameon=False)
im=hm.imshow(share.loc[order_c],aspect='auto',cmap='Blues',vmin=0,vmax=80);hm.set(yticks=y,yticklabels=[],xticks=np.arange(17),xticklabels=[c.replace('IMF5+ (slow)','Slow') for c in share.columns]);hm.tick_params(axis='x',rotation=70);hm.set_title('b  Channel shares in clustered city order',loc='left',weight='bold');fig.colorbar(im,ax=hm,shrink=.7,label='Share (%)');fig.subplots_adjust(wspace=.15,bottom=.28);save(fig,'attribution')
# Figure 3 comparisons; choose proportion shares with consistent common bars, no missing values invented.
focus=['Delhi','Mumbai','Bengaluru']; second=pd.read_csv(T/'shap/r117_decomp_seed_shap_lb7.csv'); second=second[second.period=='all'].set_index('city'); lb=pd.read_csv(T/'shap/shap_v2_lb30_vs_lb7_comparison.csv'); print('LB',lb.columns.tolist())
pmattr=pd.read_csv(T/'shap/shap_v2_pm25_attribution_lb7.csv',index_col=0);pmshare=100*pmattr.div(pmattr.sum(axis=1),axis=0)
fig,axes=plt.subplots(1,2,figsize=(10,4.2));x=np.arange(3);w=.24
for j,(label,vals) in enumerate([('AQI main',[dec[c] for c in focus]),('AQI seed 42',[second.loc[c,'channel_share_pct_dseed42'] for c in focus]),('PM2.5 target',[pmshare.loc[c].iloc[-5:].sum() for c in focus])]):axes[0].bar(x+(j-1)*w,vals,w,label=label,color=['#426f8f','#a0b7c8','#d19b42'][j])
axes[0].set(xticks=x,xticklabels=focus,ylabel='Decomposition attribution (%)',ylim=(0,105));axes[0].set_title('a  Target and decomposition realisation',loc='left',weight='bold');axes[0].legend(frameon=False,fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.13),ncol=3)
for j,(label,vals) in enumerate([('AQI target',[osc[c] for c in focus]),('PM2.5 target',[pmshare.loc[c].iloc[-5:-1].sum() for c in focus])]):axes[1].bar(x+(j-.5)*.3,vals,.3,label=label,color=['#426f8f','#8c597f'][j])
axes[1].set(xticks=x,xticklabels=focus,ylabel='IMF1–4 attribution (%)',ylim=(0,42));axes[1].set_title('b  Oscillatory-channel attribution',loc='left',weight='bold');axes[1].legend(frameon=False,fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.13),ncol=2);fig.tight_layout();fig.subplots_adjust(bottom=.24);save(fig,'sensitivity')
# inventory for provenance
manifest=[]
for p in (O/'source_results').rglob('*'):
 if p.is_file() and p.name != "manifest.json":manifest.append({'path':str(p.relative_to(O)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(O/'source_results/manifest.json').write_text(json.dumps(manifest,indent=2))

for p in (O/'tables').glob('*.tex'):
 s=p.read_text()
 for a,b in [('PM10',r'PM$_{10}$'),('PM2.5',r'PM$_{2.5}$'),('NO2',r'NO$_2$'),('NOx',r'NO$_x$'),('NH3',r'NH$_3$'),('SO2',r'SO$_2$'),('O3',r'O$_3$')]: s=s.replace(a,b)
 p.write_text(s)
