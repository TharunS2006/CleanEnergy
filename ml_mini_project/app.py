"""
Hospital Patient Segmentation: web app (Streamlit)
Run:  streamlit run app.py
"""
import numpy as np, pandas as pd
import streamlit as st
import plotly.express as px
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, davies_bouldin_score

st.set_page_config(page_title="Hospital Patient Segmentation", page_icon="🏥", layout="wide")
FEATS = ["Pregnancies","Glucose","BloodPressure","SkinThickness","Insulin","BMI","DiabetesPedigreeFunction","Age"]
MISSING_COLS = ["Glucose","BloodPressure","SkinThickness","Insulin","BMI"]
RS = 42

@st.cache_data
def load():
    raw = pd.read_csv("data/diabetes.csv")
    df = raw.copy(); df[MISSING_COLS] = df[MISSING_COLS].replace(0, np.nan)
    imp = SimpleImputer(strategy="median").fit(df[FEATS])
    X_imp = pd.DataFrame(imp.transform(df[FEATS]), columns=FEATS)
    sc = StandardScaler().fit(X_imp)
    X = sc.transform(X_imp)
    return raw, X_imp, X, imp, sc, raw["Outcome"].values

raw, X_imp, X, imp, sc, y = load()
Z = PCA(n_components=2, random_state=RS).fit(X)
Zc = Z.transform(X); ev = Z.explained_variance_ratio_

@st.cache_data
def run_kmeans(k):
    km = KMeans(n_clusters=k, n_init=10, random_state=RS).fit(X)
    return km.labels_, km.cluster_centers_, silhouette_score(X, km.labels_), davies_bouldin_score(X, km.labels_)

def names_for(k, labels):
    """Readable names from the profiles (only for k=3); otherwise 'Cluster i'."""
    if k != 3: return {i: f"Cluster {i}" for i in range(k)}
    t = X_imp.copy(); t["c"] = labels; m = t.groupby("c")[["Age","BMI"]].mean()
    old = m["Age"].idxmax(); rest = m.drop(index=old); high_bmi = rest["BMI"].idxmax(); low = rest["BMI"].idxmin()
    return {old: f"Cluster {old}: older, many pregnancies", high_bmi: f"Cluster {high_bmi}: younger, high BMI and insulin", low: f"Cluster {low}: younger, lower-risk profile"}

def profile(labels, nm=None):
    t = X_imp.copy(); t["cluster"] = labels; t["Outcome"] = y
    g = t.groupby("cluster").agg(patients=("Outcome","size"), **{c:(c,"mean") for c in FEATS}, diabetes_rate_pct=("Outcome", lambda s: 100*s.mean())).round(2)
    if nm: g.insert(0, "group", [nm.get(i, str(i)) for i in g.index])
    return g

st.title("🏥 Hospital Patient Segmentation")
st.caption("Clustering patients by clinical attributes (Pima Indians Diabetes data) with K-Means and DBSCAN. The diabetes label is NOT used to form clusters. It is used afterwards only to check them.")
page = st.sidebar.radio("Go to", ["1. Dataset", "2. K-Means", "3. DBSCAN", "4. Find a patient's group", "5. Summary and limits"])
st.sidebar.markdown("---")
st.sidebar.markdown("**Team**  \nTamilmani B (111624102217)  \nYuvraj U (111624102247)  \nVishnu Vardhan A (111624102241)")

if page.startswith("1"):
    c1,c2,c3 = st.columns(3); c1.metric("Patients", len(raw)); c2.metric("Features", len(FEATS)); c3.metric("Diabetes rate", f"{100*y.mean():.1f}%")
    st.subheader("Raw data (first rows)"); st.dataframe(raw.head(15), width="stretch")
    st.subheader("Cleaning: zeros that cannot be real values")
    miss = (raw[MISSING_COLS]==0).sum().rename("zeros treated as missing").to_frame(); miss["share %"] = (100*miss.iloc[:,0]/len(raw)).round(1)
    st.dataframe(miss); st.caption("Median imputation, then standardisation (mean 0, std 1). Insulin and skin thickness are heavily imputed.")
    f = st.selectbox("Feature distribution", FEATS)
    st.plotly_chart(px.histogram(X_imp, x=f, nbins=30, title=f"Distribution of {f} (after cleaning)"), width="stretch")
    st.plotly_chart(px.imshow(X_imp.corr().round(2), text_auto=True, color_continuous_scale="RdBu_r", zmin=-1, zmax=1, title="Feature correlation"), width="stretch")

elif page.startswith("2"):
    k = st.slider("Number of clusters (k)", 2, 8, 3)
    labels, cent, sil, dbi = run_kmeans(k)
    c1,c2,c3 = st.columns(3); c1.metric("Silhouette (higher is better)", f"{sil:.3f}"); c2.metric("Davies-Bouldin (lower is better)", f"{dbi:.3f}"); c3.metric("Clusters", k)
    nm = names_for(k, labels)
    plot = pd.DataFrame({"PC1":Zc[:,0], "PC2":Zc[:,1], "cluster":[nm[l] for l in labels]})
    st.plotly_chart(px.scatter(plot, x="PC1", y="PC2", color="cluster", opacity=.8, title=f"K-Means (k={k}) on the first two principal components ({100*ev.sum():.0f}% of variance)"), width="stretch")
    st.subheader("Cluster profiles (average in original units)"); prof = profile(labels, nm); st.dataframe(prof, width="stretch")
    st.plotly_chart(px.bar(prof.reset_index(), x="cluster", y="diabetes_rate_pct", text="diabetes_rate_pct", title="Diabetes rate in each cluster (label not used for clustering)"), width="stretch")
    ks = pd.DataFrame([dict(k=kk, silhouette=run_kmeans(kk)[2], davies_bouldin=run_kmeans(kk)[3]) for kk in range(2,9)])
    st.plotly_chart(px.line(ks, x="k", y=["silhouette","davies_bouldin"], markers=True, title="Choosing k"), width="stretch")
    st.info("Silhouette is about the same for k=2 and k=3 and then falls, so k=3 is a judgement for interpretability, not a clear optimum.")

elif page.startswith("3"):
    c1,c2 = st.columns(2); eps = c1.slider("eps (neighbourhood size)", 0.5, 3.5, 2.0, 0.1); ms = c2.slider("min_samples", 3, 25, 16)
    lab = DBSCAN(eps=eps, min_samples=ms).fit(X).labels_
    ncl = len(set(lab)) - (1 if -1 in lab else 0); noise = int((lab==-1).sum())
    m1,m2,m3 = st.columns(3); m1.metric("Clusters found", ncl); m2.metric("Noise patients", noise); m3.metric("Noise share", f"{100*noise/len(lab):.1f}%")
    plot = pd.DataFrame({"PC1":Zc[:,0], "PC2":Zc[:,1], "group":["noise" if l==-1 else f"cluster {l}" for l in lab]})
    st.plotly_chart(px.scatter(plot, x="PC1", y="PC2", color="group", opacity=.8, title=f"DBSCAN (eps={eps}, min_samples={ms})"), width="stretch")
    st.subheader("Group profiles"); st.dataframe(profile(lab), width="stretch")
    st.info("With these data DBSCAN finds one dense group plus outliers at most settings. Try eps 2.1 and min_samples 5: it finds a second cluster of only a few patients, which is a pocket of outliers, not a patient segment.")

elif page.startswith("4"):
    st.subheader("Which K-Means group is a patient most similar to?")
    labels, cent, _, _ = run_kmeans(3); nm = names_for(3, labels)
    c = st.columns(4); vals = {}
    defaults = dict(Pregnancies=3, Glucose=120, BloodPressure=70, SkinThickness=29, Insulin=125, BMI=32.0, DiabetesPedigreeFunction=0.47, Age=33)
    for i,f in enumerate(FEATS):
        vals[f] = c[i%4].number_input(f, min_value=0.0, value=float(defaults[f]), step=0.01 if f=="DiabetesPedigreeFunction" else 1.0)
    if st.button("Find group"):
        row = pd.DataFrame([vals]); row[MISSING_COLS] = row[MISSING_COLS].replace(0, np.nan)
        zs = sc.transform(pd.DataFrame(imp.transform(row[FEATS]), columns=FEATS))
        d = np.linalg.norm(cent - zs, axis=1); g = int(np.argmin(d))
        st.success(f"Most similar to: **{nm[g]}**")
        prof = profile(labels, nm); st.write("Average profile of that group:"); st.dataframe(prof.loc[[g]], width="stretch")
        st.warning("This only says which group of past patients has similar measurements. It is NOT a diagnosis and must not be used for medical decisions.")

else:
    st.subheader("Summary")
    st.markdown("""
- **K-Means (k=3)** gives three stable groups (248, 335 and 185 patients): younger lower-risk (diabetes 13%), older with many pregnancies (52%), and younger with high BMI and insulin (52%).
- **Stability:** re-running with 10 random starts gives almost identical clusters (adjusted Rand index 0.991).
- **Weak separation:** silhouette is only 0.195, so groups overlap. The data is closer to one continuous cloud than to three distinct types.
- **DBSCAN** finds one main group plus 88 unusual patients (higher glucose and insulin), so it works better as an outlier detector here.
""")
    st.subheader("Limits")
    st.markdown("""
- Only women aged 21+ of Pima heritage, 768 patients.
- Insulin (about half) and skin thickness (about 30%) are filled with the median.
- Clusters describe similar measurements. They are not diagnoses.
""")
