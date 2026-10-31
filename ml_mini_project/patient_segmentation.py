"""
Hospital Patient Segmentation using K-Means and DBSCAN
Dataset: Pima Indians Diabetes Database (768 patients, 8 clinical attributes)
Goal: discover patient groups from clinical attributes WITHOUT using the Outcome label.
Run: python3 patient_segmentation.py
"""
import json, warnings
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, seaborn as sns
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score, adjusted_rand_score
warnings.filterwarnings("ignore")
RS = 42
FEATS = ["Pregnancies","Glucose","BloodPressure","SkinThickness","Insulin","BMI","DiabetesPedigreeFunction","Age"]
df = pd.read_csv("data/diabetes.csv")

# ---- 1. Data cleaning: zeros in these columns are impossible values = missing ----
MISSING_COLS = ["Glucose","BloodPressure","SkinThickness","Insulin","BMI"]
miss = (df[MISSING_COLS]==0).sum()
raw = df.copy()
df[MISSING_COLS] = df[MISSING_COLS].replace(0, np.nan)
X_imp = pd.DataFrame(SimpleImputer(strategy="median").fit_transform(df[FEATS]), columns=FEATS)
X = StandardScaler().fit_transform(X_imp)
y = df["Outcome"].values   # NOT used for clustering; only for checking afterwards

# ---- 2. EDA figures ----
fig, axs = plt.subplots(2,4, figsize=(14,6))
for a,c in zip(axs.ravel(), FEATS):
    sns.histplot(X_imp[c], kde=True, ax=a, color="#2b5c8a"); a.set_title(c, fontsize=9); a.set_xlabel("")
plt.tight_layout(); plt.savefig("figures/01_distributions.png", dpi=130); plt.close()
plt.figure(figsize=(7,5.5)); sns.heatmap(X_imp.corr(), annot=True, fmt=".2f", cmap="coolwarm", center=0, annot_kws={"size":7})
plt.title("Feature correlation (after cleaning)"); plt.tight_layout(); plt.savefig("figures/02_correlation.png", dpi=130); plt.close()
plt.figure(figsize=(6,3.5)); miss.plot(kind="bar", color="#e08a2e"); plt.ylabel("Zero values treated as missing"); plt.title("Missing values per column"); plt.tight_layout(); plt.savefig("figures/03_missing.png", dpi=130); plt.close()

# ---- 3. K-Means: choose k ----
rows=[]
for k in range(2,9):
    km = KMeans(n_clusters=k, n_init=10, random_state=RS).fit(X)
    rows.append(dict(k=k, inertia=km.inertia_, silhouette=silhouette_score(X, km.labels_),
                     davies_bouldin=davies_bouldin_score(X, km.labels_), calinski_harabasz=calinski_harabasz_score(X, km.labels_)))
km_tab = pd.DataFrame(rows); km_tab.to_csv("results/kmeans_k_selection.csv", index=False)
fig, axs = plt.subplots(1,3, figsize=(13,3.6))
axs[0].plot(km_tab.k, km_tab.inertia, "o-"); axs[0].set_title("Elbow (inertia)")
axs[1].plot(km_tab.k, km_tab.silhouette, "o-", color="green"); axs[1].set_title("Silhouette (higher is better)")
axs[2].plot(km_tab.k, km_tab.davies_bouldin, "o-", color="red"); axs[2].set_title("Davies-Bouldin (lower is better)")
for a in axs: a.set_xlabel("k")
plt.tight_layout(); plt.savefig("figures/04_kmeans_k_selection.png", dpi=130); plt.close()
K = 3   # chosen after reading the table below (see report); not just the max silhouette
km = KMeans(n_clusters=K, n_init=10, random_state=RS).fit(X)
lab_km = km.labels_
# stability across seeds
base = lab_km; aris=[]
for s in range(10):
    l = KMeans(n_clusters=K, n_init=10, random_state=100+s).fit(X).labels_
    aris.append(adjusted_rand_score(base, l))

# ---- 4. DBSCAN ----
MIN_S = 16   # about 2 x number of features, a common rule of thumb
nn = NearestNeighbors(n_neighbors=MIN_S).fit(X); dist,_ = nn.kneighbors(X); kd = np.sort(dist[:,-1])
plt.figure(figsize=(6,3.8)); plt.plot(kd); plt.xlabel("Patients sorted by distance"); plt.ylabel(f"Distance to {MIN_S}th neighbour"); plt.title("k-distance plot for choosing eps"); plt.tight_layout(); plt.savefig("figures/05_dbscan_kdistance.png", dpi=130); plt.close()
grid=[]
for eps in np.arange(1.0, 3.01, 0.1):
    for ms in (5, 8, 12, 16):
        l = DBSCAN(eps=eps, min_samples=ms).fit(X).labels_
        ncl = len(set(l)) - (1 if -1 in l else 0); noise = float((l==-1).mean())
        sil = silhouette_score(X[l!=-1], l[l!=-1]) if ncl>=2 else np.nan
        sizes = [int((l==c).sum()) for c in set(l) if c!=-1]
        smallest = round(100*min(sizes)/len(l),1) if sizes else 0.0
        grid.append(dict(eps=round(float(eps),2), min_samples=ms, clusters=ncl, noise_pct=round(100*noise,1), smallest_cluster_pct=smallest, silhouette_non_noise=sil))
db_tab = pd.DataFrame(grid); db_tab.to_csv("results/dbscan_grid.csv", index=False)
# choose: at least 2 clusters, noise <= 25%, every cluster at least 5% of patients (a cluster of a few outliers is not a patient segment)
cand = db_tab[(db_tab.clusters>=2)&(db_tab.noise_pct<=25)&(db_tab.smallest_cluster_pct>=5)].sort_values("silhouette_non_noise", ascending=False)
cand_any = db_tab[(db_tab.clusters>=2)&(db_tab.noise_pct<=25)].sort_values("silhouette_non_noise", ascending=False)
if len(cand):
    best = cand.iloc[0]; db_eps, db_ms = float(best.eps), int(best.min_samples)
else:
    db_eps, db_ms = 2.0, 16
db = DBSCAN(eps=db_eps, min_samples=db_ms).fit(X); lab_db = db.labels_

# ---- 5. PCA plots ----
pca = PCA(n_components=2, random_state=RS).fit(X); Z = pca.transform(X)
ev = pca.explained_variance_ratio_
fig, axs = plt.subplots(1,2, figsize=(11,4.4))
for a,lab,t in [(axs[0],lab_km,f"K-Means (k={K})"),(axs[1],lab_db,f"DBSCAN (eps={db_eps}, min_samples={db_ms})")]:
    sc = a.scatter(Z[:,0], Z[:,1], c=lab, cmap="tab10", s=14, alpha=.8); a.set_title(t); a.set_xlabel(f"PC1 ({ev[0]*100:.0f}% variance)"); a.set_ylabel(f"PC2 ({ev[1]*100:.0f}% variance)")
plt.tight_layout(); plt.savefig("figures/06_pca_clusters.png", dpi=130); plt.close()

# ---- 6. Profiles (original units) ----
def profile(labels, name):
    t = X_imp.copy(); t["cluster"]=labels; t["Outcome"]=y
    g = t.groupby("cluster").agg(size=("Outcome","size"), **{c:(c,"mean") for c in FEATS}, diabetes_rate=("Outcome","mean")).round(2)
    g.to_csv(f"results/{name}_profiles.csv"); return g
prof_km = profile(lab_km,"kmeans"); prof_db = profile(lab_db,"dbscan")
# heatmap of standardised profile for K-Means
zt = pd.DataFrame(X, columns=FEATS); zt["c"]=lab_km; zp = zt.groupby("c").mean()
plt.figure(figsize=(9,3.2)); sns.heatmap(zp, annot=True, fmt=".2f", cmap="coolwarm", center=0, annot_kws={"size":8}); plt.title("K-Means clusters: mean of each standardised feature"); plt.ylabel("cluster"); plt.tight_layout(); plt.savefig("figures/07_kmeans_profile_heatmap.png", dpi=130); plt.close()
fig, ax = plt.subplots(figsize=(5.2,3.6)); prof_km["diabetes_rate"].mul(100).plot(kind="bar", color="#c0392b", ax=ax); ax.set_ylabel("% with diabetes (Outcome=1)"); ax.set_title("Diabetes rate per K-Means cluster\n(label NOT used for clustering)"); plt.xticks(rotation=0); plt.tight_layout(); plt.savefig("figures/08_kmeans_outcome_rate.png", dpi=130); plt.close()

# ---- 7. Compare and save ----
mask = lab_db!=-1
cmp_ari = adjusted_rand_score(lab_km[mask], lab_db[mask]) if len(set(lab_db[mask]))>1 else np.nan
out = df[["Outcome"]].copy(); out["kmeans_cluster"]=lab_km; out["dbscan_cluster"]=lab_db; out.to_csv("results/cluster_assignments.csv", index=False)
summary = dict(n=len(df), zeros_as_missing=miss.to_dict(), K=K, kmeans_silhouette=float(silhouette_score(X, lab_km)),
  kmeans_davies_bouldin=float(davies_bouldin_score(X, lab_km)), kmeans_stability_ari_mean=float(np.mean(aris)), kmeans_stability_ari_min=float(np.min(aris)),
  dbscan=dict(eps=db_eps, min_samples=db_ms, clusters=int(len(set(lab_db))-(1 if -1 in lab_db else 0)), noise_points=int((lab_db==-1).sum()),
              silhouette_non_noise=float(silhouette_score(X[mask], lab_db[mask])) if len(set(lab_db[mask]))>1 else None),
  ari_kmeans_vs_dbscan_non_noise=None if np.isnan(cmp_ari) else float(cmp_ari), pca_variance_2=float(ev.sum()),
  overall_diabetes_rate=float(y.mean()))
json.dump(summary, open("results/summary.json","w"), indent=2)
print("MISSING:", miss.to_dict()); print("\nK-MEANS SELECTION\n", km_tab.round(3).to_string(index=False))
print("\nDBSCAN valid configs (clusters>=2, noise<=25%), ignoring size rule\n", cand_any.head(8).round(3).to_string(index=False)); print("\nDBSCAN configs that also have every cluster >=5% of patients:", len(cand))
print("\nK-MEANS PROFILES\n", prof_km.to_string()); print("\nDBSCAN PROFILES\n", prof_db.to_string())
print("\nSUMMARY", json.dumps(summary, indent=1))
