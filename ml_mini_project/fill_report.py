"""Fills the college report format (report_template_format.docx) with the project content.
Run: python build_college_report.py  (after patient_segmentation.py has produced results/)"""
import copy, re, json
import pandas as pd
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

TITLE = "Hospital Patient Segmentation using K-Means and DBSCAN"
STUDENTS = [("Tamil Mani B","111624102217"),("A Vishnu Vardhan","111624102241"),("Yuvaraj U","111624102247")]
GUIDE = "Dr. RAMALAKSHMI R"; CLASS = "CSE - B"
S = json.load(open("results/summary.json")); kprof = pd.read_csv("results/kmeans_profiles.csv"); dprof = pd.read_csv("results/dbscan_profiles.csv")
ksel = pd.read_csv("results/kmeans_k_selection.csv"); dgrid = pd.read_csv("results/dbscan_grid.csv")
raw = pd.read_csv("data/diabetes.csv")

d = Document("report_template_format.docx"); P = list(d.paragraphs); T = list(d.tables)
BODY = P[78]; H2 = P[79]; BUL = P[162]; NUM = P[102]
CENTER = WD_ALIGN_PARAGRAPH.CENTER

def set_text(p, text):
    rs = p.runs
    if rs:
        for r in rs[1:]: r._r.getparent().remove(r._r)
        rs[0].text = text
    else: p.add_run(text)

def clone(like, text, ref_el, bold=None, italic=None, size=None, align=None, font=None):
    while hasattr(ref_el, '_p'): ref_el = ref_el._p
    new = copy.deepcopy(like._p); ref_el.addnext(new); p = Paragraph(new, like._parent); set_text(p, text)
    r = p.runs[0]
    if bold is not None: r.bold = bold
    if italic is not None: r.italic = italic
    if size: r.font.size = Pt(size)
    if font: r.font.name = font; r._r.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), font)
    if align is not None: p.alignment = align
    return p

def paras(ref, texts, like=None):
    cur = ref._p if hasattr(ref, "_p") else ref
    out = None
    for t in texts:
        out = clone(like or BODY, t, cur); cur = out._p
    return out

def shade(cell, fill="D9D9D9"):
    tcPr = cell._tc.get_or_add_tcPr()
    for s in tcPr.findall(qn("w:shd")): tcPr.remove(s)
    from docx.oxml import OxmlElement
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), fill); tcPr.append(shd)

def new_table(ref_el, head, rows, widths, size=9.5):
    t = d.add_table(rows=1, cols=len(head)); t.style = "Table Grid"
    for i, h in enumerate(head):
        c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(size); shade(c)
    for row in rows:
        cs = t.add_row().cells
        for i, v in enumerate(row):
            cs[i].text = ""; r = cs[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(size)
    for row in t.rows:
        for i, w in enumerate(widths): row.cells[i].width = Cm(w)
    ref_el.addnext(t._tbl); return t

def picture(ref_el, path, width, caption):
    p = d.add_paragraph(); p.alignment = CENTER; p.add_run().add_picture(path, width=Cm(width)); ref_el.addnext(p._p)
    cap = clone(BODY, caption, p._p, italic=True, size=10, align=CENTER); return cap

def fill_table(t, rows, start=1):
    while len(t.rows) < start + len(rows):
        t._tbl.append(copy.deepcopy(t.rows[-1]._tr))
    while len(t.rows) > start + len(rows):
        t._tbl.remove(t.rows[-1]._tr)
    for ri, row in enumerate(rows):
        for ci, v in enumerate(row):
            cell = t.rows[start + ri].cells[ci]; ps = cell.paragraphs
            for extra in ps[1:]: extra._p.getparent().remove(extra._p)
            set_text(ps[0], str(v))

# ------------------------------------------------ cover, certificate, declaration
for r in P[2].runs: r.text = r.text.replace("[Enter the Approved Mini Project Title]", TITLE)
r = P[3].runs
r[2].text = "\n" + "\n".join(f"{n} ({g})" for n, g in STUDENTS); r[3].text = ""; r[4].text = f"\nClass / Section: {CLASS}"
for r in P[4].runs: r.text = r.text.replace("[Faculty Guide Name]", GUIDE)
for p in P:
    for r in p.runs:
        r.text = (r.text.replace("[Enter Project Title]", TITLE).replace("[Student Name(s)]", ", ".join(n for n, _ in STUDENTS[:-1]) + " and " + STUDENTS[-1][0])
                  .replace("[Class/Section]", CLASS).replace("[2026–2027]", "2026–2027").replace("[2026 – 2027]", "2026 – 2027"))
c = T[0].rows[1].cells[0]; set_text(c.paragraphs[0], "Faculty Guide\nName: " + GUIDE)
for extra in c.paragraphs[1:]: extra._p.getparent().remove(extra._p)

# ------------------------------------------------ abstract
n = S["n"]; ds = S["dbscan"]
ABSTRACT = (f"Hospitals treat patients whose clinical profiles differ widely, and grouping similar patients can support screening and follow-up planning. "
 f"This project applies unsupervised machine learning to segment patients using the Pima Indians Diabetes Database, which has {n} patient records and eight clinical attributes. "
 f"The diabetes label was not used to form clusters; it was used only afterwards to validate them. Impossible zero values in glucose, blood pressure, skin thickness, insulin and BMI were treated as missing and replaced by the median, and all features were standardised. "
 f"K-Means (k = 2 to 8) and DBSCAN (a grid of eps and min_samples values) were compared using inertia, the silhouette score, the Davies-Bouldin index, the Calinski-Harabasz index and the adjusted Rand index. "
 f"K-Means with k = 3 gave three stable groups of 248, 335 and 185 patients (mean adjusted Rand index {S['kmeans_stability_ari_mean']:.3f} over ten random starts) with diabetes rates of 52%, 13% and 52%, against 34.9% overall. "
 f"The silhouette score was only {S['kmeans_silhouette']:.3f}, which shows that the groups overlap and are not sharply separated. DBSCAN found one dense group and {ds['noise_points']} outlying patients, so it behaved as an outlier detector and not as a segmentation method. "
 "A Streamlit web application was built to explore the clusters and to place a new patient in the most similar group. K-Means was the more useful method for patient segmentation on this data. The groups describe similar measurements and are not diagnoses.")
set_text(P[48], ABSTRACT)
set_text(P[49], "Keywords: Patient segmentation, K-Means, DBSCAN, Clustering, Pima Indians Diabetes")
P[49].runs[0].bold = False

# ------------------------------------------------ 1 introduction
set_text(P[78], "Healthcare organisations record clinical measurements such as blood glucose, blood pressure, body mass index and age for every patient. Patients with similar measurements often need similar care, but grouping them by hand is slow when there are many patients and many attributes. Machine learning, in particular unsupervised clustering, can group patients automatically from the data without any predefined labels. Diabetes is a useful test case because it is a common long-term condition in which several measurements influence risk together.")
set_text(P[80], "Hospitals have limited time and resources. If groups of patients with different risk profiles can be found, screening, counselling and follow-up can be planned for each group. Doctors, hospital administrators and public-health planners may benefit. A second motivation is to learn how clustering behaves on real, imperfect medical data that has missing values and overlapping groups.")
set_text(P[82], "Included: unsupervised segmentation of 768 patients using eight clinical attributes; data cleaning and scaling; K-Means and DBSCAN; evaluation with internal measures; validation of the groups against the diabetes label after clustering; and a web application to explore the results. Excluded: diagnosing or predicting diabetes, supervised models, clinical validation by doctors, other datasets, and deployment in a hospital.")
last = paras(P[84], [])  # placeholder to keep API simple
set_text(P[84], "Practical applications of patient segmentation include:")
last = paras(P[84], ["Targeted screening and awareness programmes for each patient group.", "Planning of follow-up visits and hospital resources by group size and risk.", "Spotting unusual patients whose measurements differ from most others.", "A starting point for later supervised models and feature studies."], like=BUL)

# ------------------------------------------------ 2 problem
set_text(P[100], "To divide the 768 patients of the Pima Indians Diabetes Database into groups with similar clinical profiles using K-Means and DBSCAN, without using the diabetes label, and to measure how well separated and how stable the groups are and whether they differ in diabetes rate.")
for p, t in zip(P[102:106], ["To clean and prepare the clinical data (missing values and scaling) so that distance-based clustering is meaningful.",
    "To apply K-Means for k = 2 to 8 and DBSCAN over a grid of eps and min_samples values.",
    "To evaluate the clusters using the silhouette score, Davies-Bouldin index, Calinski-Harabasz index and stability across random starts, and to compare the two methods.",
    "To describe each group, check it against the diabetes label after clustering, and present the results in a web application."]): set_text(p, t)
set_text(P[107], "A small number of patient groups with clearly described average profiles, quality scores for each method, a comparison of K-Means and DBSCAN, an honest statement of how well the groups are separated, and a working web application.")

# ------------------------------------------------ 3 literature survey
set_text(P[126], "The sources below describe the dataset, the two clustering methods and the evaluation measures used in this project.")
fill_table(T[1], [
 ("1", "Smith et al., 1988", "Using the ADAP learning algorithm to forecast the onset of diabetes mellitus", "ADAP, an adaptive learning algorithm", "Introduced the Pima dataset. Predicts diabetes onset (supervised) and does not group patients. Limited to one population."),
 ("2", "MacQueen, 1967; Lloyd, 1982", "Some methods for classification and analysis of multivariate observations; Least squares quantization in PCM", "K-Means", "Simple and fast. Needs k in advance, assumes roughly round clusters, and is sensitive to scaling and outliers."),
 ("3", "Ester et al., 1996", "A density-based algorithm for discovering clusters in large spatial databases with noise", "DBSCAN", "Finds clusters of any shape and marks noise. One global eps struggles when densities differ, and results depend on eps and min_samples."),
 ("4", "Rousseeuw, 1987", "Silhouettes: a graphical aid to the interpretation and validation of cluster analysis", "Silhouette coefficient", "Label-free measure of cohesion and separation from -1 to 1. Values near 0 mean overlapping clusters."),
 ("5", "Davies and Bouldin, 1979", "A cluster separation measure", "Davies-Bouldin index", "Lower values mean more compact and better separated clusters. Assumes roughly spherical clusters.")])

# ------------------------------------------------ 4 dataset
set_text(P[145], "Platform: Kaggle")
set_text(P[146], "Dataset Name: Pima Indians Diabetes Database (originally from the National Institute of Diabetes and Digestive and Kidney Diseases)\nDataset URL: https://www.kaggle.com/datasets/uciml/pima-indians-diabetes-database\nAccess Date: 31-10-2026")
miss = {"Glucose": 5, "BloodPressure": 35, "SkinThickness": 227, "Insulin": 374, "BMI": 11}
fill_table(T[2], [("Number of Instances", "768 patients (women aged 21 or older, of Pima Indian heritage)"), ("Number of Attributes", "9 (8 input features and 1 outcome column)"),
 ("Target Variable", "Outcome (1 = diabetes, 0 = no diabetes). Not used for clustering; used only afterwards to validate the groups."), ("Data Type", "Numerical (integer and decimal)"),
 ("Missing Values", "No blank cells, but zeros that cannot be real values: Glucose 5, BloodPressure 35, SkinThickness 227, Insulin 374, BMI 11. These were treated as missing. Duplicate records: 0."),
 ("Class Distribution", "500 patients without diabetes (65.1%) and 268 with diabetes (34.9%)")])
fill_table(T[3], [("Pregnancies", "Integer", "Number of times pregnant", "Input"), ("Glucose", "Integer", "Plasma glucose concentration 2 hours after an oral glucose tolerance test", "Input"),
 ("BloodPressure", "Integer", "Diastolic blood pressure (mm Hg)", "Input"), ("SkinThickness", "Integer", "Triceps skin fold thickness (mm)", "Input"),
 ("Insulin", "Integer", "2-hour serum insulin (mu U/ml)", "Input"), ("BMI", "Decimal", "Body mass index (weight in kg / height in m squared)", "Input"),
 ("DiabetesPedigreeFunction", "Decimal", "Score of diabetes in the family history", "Input"), ("Age", "Integer", "Age in years", "Input"),
 ("Outcome", "Integer (0/1)", "Diabetes diagnosis", "Target (validation only)")])
note = clone(BODY, "Note: the file used (768 rows, 9 columns) is a copy of the standard version of this dataset. Please compare it with the Kaggle download before submission.", T[3]._tbl, italic=True, size=10)

# ------------------------------------------------ 5 methodology
set_text(P[162], "Handling missing values: zeros in Glucose, BloodPressure, SkinThickness, Insulin and BMI were treated as missing and replaced with the column median.")
set_text(P[163], "Removing duplicates: checked, and no duplicate records were found.")
set_text(P[164], "Outlier treatment: no records were removed. Extreme values (for example insulin up to 846) were kept, and DBSCAN was used to flag unusual patients.")
set_text(P[165], "Encoding categorical variables: not required, because all attributes are numerical.")
set_text(P[166], "Feature scaling / normalization: standardisation (mean 0, standard deviation 1) with StandardScaler, because K-Means and DBSCAN use distances.")
set_text(P[167], "Train-validation-test split: not applicable. Clustering is unsupervised, so all 768 patients were used. The Outcome label was used only after clustering.")
alg = paras(P[169], [], like=BODY)
set_text(P[169], "K-Means divides the patients into k groups by repeatedly assigning each patient to the nearest cluster centre and moving each centre to the mean of its group. We used k-means++ initialisation, 10 random starts for each k and random_state = 42, and tried k = 2 to 8. Stability was tested by repeating K-Means with ten different random seeds and comparing the results with the adjusted Rand index.")
alg = paras(P[169], ["DBSCAN groups patients who lie in dense regions and marks isolated patients as noise. It has two settings: eps (neighbourhood radius) and min_samples (patients needed to form a dense region). We searched eps from 1.0 to 3.0 in steps of 0.1 with min_samples of 5, 8, 12 and 16, and used a k-distance plot with min_samples = 16 to understand the scale of eps. A setting was accepted only if it gave at least two clusters, under 25% noise and every cluster holding at least 5% of the patients. No setting passed, so the final run used eps = 2.0 and min_samples = 16.",
 "Principal component analysis (PCA) was used only to draw the clusters in two dimensions. The clustering itself used all eight standardised features."])
set_text(P[171], "All measures except the last do not need the diabetes label, which suits unsupervised learning.")
fill_table(T[4], [
 ("Inertia", "Sum of squared distances from each patient to its cluster centre", "Used for the elbow plot. It always falls as k rises, so it cannot choose k alone."),
 ("Silhouette Score", "s = (b - a) / max(a, b), where a is the mean distance to the patient's own cluster and b the mean distance to the nearest other cluster. Range -1 to 1.", "Label-free measure of how well separated the clusters are."),
 ("Davies-Bouldin Index", "Average over clusters of the largest ratio of (spread of two clusters) to (distance between their centres). Lower is better.", "Compares compactness with separation."),
 ("Calinski-Harabasz Index", "Ratio of between-cluster dispersion to within-cluster dispersion. Higher is better.", "Second check on separation."),
 ("Adjusted Rand Index (ARI)", "Agreement between two clusterings, corrected for chance. 1 = identical, 0 = random.", "Used for stability across random starts and for comparing K-Means with DBSCAN."),
 ("Diabetes rate per cluster", "Share of patients with Outcome = 1 in each cluster", "External check, done after clustering, of whether groups carry clinical meaning.")])

# ------------------------------------------------ 6 implementation
fill_table(T[5], [("Programming Language", "Python 3", "Implementation"), ("Development Environment", "Python scripts run from the PowerShell terminal; web browser (Google Chrome) for the web application", "Coding, running and demonstration"),
 ("Libraries", "NumPy, Pandas, Matplotlib, Seaborn, Scikit-learn, Plotly, Streamlit, python-docx", "Data processing, modelling, charts and web application"),
 ("Hardware", "Standard Windows laptop or PC. No GPU needed because the dataset has only 768 rows.", "Execution environment")])
fill_table(T[6], [("Data loading and cleaning", "Reads the CSV, treats impossible zeros as missing, fills them with the median", "diabetes.csv", "Clean feature table"),
 ("Preprocessing", "Standardises all eight features", "Clean feature table", "Standardised matrix"),
 ("K-Means module", "Runs k = 2 to 8, computes metrics, fits k = 3, tests stability", "Standardised matrix", "Labels, metric table, profiles"),
 ("DBSCAN module", "Draws k-distance plot, searches eps and min_samples, fits the final model", "Standardised matrix", "Labels, noise count, grid table"),
 ("Visualisation and profiling", "PCA plots, profile heatmap, diabetes rate per cluster", "Labels and features", "Figures and CSV results"),
 ("Web application (Streamlit)", "Five pages: dataset, K-Means, DBSCAN, patient lookup, summary", "CSV, slider values, patient values", "Interactive charts and tables")])
snips = [("Cleaning and scaling:", 'MISSING_COLS = ["Glucose","BloodPressure","SkinThickness","Insulin","BMI"]\ndf[MISSING_COLS] = df[MISSING_COLS].replace(0, np.nan)\nX_imp = pd.DataFrame(SimpleImputer(strategy="median").fit_transform(df[FEATS]), columns=FEATS)\nX = StandardScaler().fit_transform(X_imp)'),
 ("K-Means over k = 2 to 8, and the final model:", 'for k in range(2, 9):\n    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)\n    sil = silhouette_score(X, km.labels_)\n    dbi = davies_bouldin_score(X, km.labels_)\nkm = KMeans(n_clusters=3, n_init=10, random_state=42).fit(X)'),
 ("DBSCAN grid search and the final model:", 'for eps in np.arange(1.0, 3.01, 0.1):\n    for ms in (5, 8, 12, 16):\n        labels = DBSCAN(eps=eps, min_samples=ms).fit(X).labels_\ndb = DBSCAN(eps=2.0, min_samples=16).fit(X)'),
 ("PCA for the two-dimensional plots:", 'pca = PCA(n_components=2, random_state=42).fit(X)\nZ = pca.transform(X)')]
set_text(P[184], "Only the main parts of the code are shown here. The complete code is in Appendix B and is submitted separately.")
cur = P[184]
for cap, code in snips:
    cur = clone(BODY, cap, cur._p, bold=True); cur = clone(BODY, code, cur._p, size=9, font="Courier New")

# ------------------------------------------------ 7 results
set_text(P[201], "Before clustering, the data was examined. Insulin is strongly skewed to the right (skewness 3.38 after cleaning), as are the diabetes pedigree function (1.92) and age (1.13). Pregnancies and age are correlated (0.54), skin thickness and BMI are correlated (0.54), and glucose and insulin are correlated (0.42). Because several features move together, the data is expected to form overlapping groups and not sharply separated ones.")
cur = P[201]
cur = picture(cur._p, "figures/03_missing.png", 7, "Figure 7.1: Zero values treated as missing, by column")
cur = picture(cur._p, "figures/01_distributions.png", 13, "Figure 7.2: Distribution of each feature after cleaning")
cur = picture(cur._p, "figures/02_correlation.png", 9, "Figure 7.3: Correlation between the features")
set_text(T[7].rows[0].cells[1].paragraphs[0], "Clusters / noise"); set_text(T[7].rows[0].cells[2].paragraphs[0], "Silhouette")
set_text(T[7].rows[0].cells[3].paragraphs[0], "Davies-Bouldin"); set_text(T[7].rows[0].cells[4].paragraphs[0], "Stability (ARI, 10 seeds)")
fill_table(T[7], [("K-Means, k = 2", "2", "0.196", "1.920", "0.997", "Highest silhouette; splits younger lower-risk from older higher-risk patients"),
 ("K-Means, k = 3 (chosen)", "3", "0.195", "1.834", "0.991", "Three balanced groups that can be described clearly"),
 ("K-Means, k = 4", "4", "0.190", "1.617", "0.959", "Lower Davies-Bouldin but less stable"),
 ("DBSCAN, eps 2.0, min_samples 16", "1 cluster + 88 noise", "Not defined (one cluster)", "Not defined", "Not applicable", "One dense group and outliers")])
cur = clone(BODY, "Table 7.2 compares the methods. The full K-Means results for k = 2 to 8 are in Appendix C. The silhouette scores are almost the same for k = 2 and k = 3 and then fall, and there is no sharp bend in the inertia curve, so k = 3 was chosen as a judgement for interpretability and balanced group sizes, not because the metrics clearly prefer it.", T[7]._tbl)
cur = picture(cur._p, "figures/04_kmeans_k_selection.png", 15.5, "Figure 7.4: Elbow, silhouette and Davies-Bouldin for k = 2 to 8")
cur = clone(BODY, "Average profile of each K-Means group (original units):", cur._p, bold=True)
rows = [(int(r["cluster"]), int(r["size"]), f"{r['Age']:.0f}", f"{r['Pregnancies']:.1f}", f"{r['Glucose']:.0f}", f"{r['BMI']:.1f}", f"{r['Insulin']:.0f}", f"{100*r['diabetes_rate']:.0f}%") for _, r in kprof.iterrows()]
tb = new_table(cur._p, ["Cluster", "Patients", "Age", "Pregnancies", "Glucose", "BMI", "Insulin", "Diabetes rate"], rows, [1.8, 2, 1.6, 2.4, 2, 1.6, 1.8, 2.6]); cur = tb._tbl
cur = paras(type("X", (), {"_p": cur})(), ["Cluster 0 (248 patients): older (average 46), many pregnancies (7.4), higher blood pressure; diabetes rate 52%. Cluster 1 (335 patients): younger (average 26), lowest glucose and BMI; diabetes rate 13%. Cluster 2 (185 patients): younger (average 29), highest BMI (39.2), skin thickness and insulin, high glucose; diabetes rate 52%."])
cur = picture(cur._p, "figures/07_kmeans_profile_heatmap.png", 12.5, "Figure 7.5: Average of each standardised feature in each K-Means cluster")
cur = picture(cur._p, "figures/06_pca_clusters.png", 14.5, "Figure 7.6: K-Means (left) and DBSCAN (right) shown on the first two principal components (47% of the variance)")

set_text(P[204], "Confusion matrices are not used because clustering has no true labels. Instead, the groups were checked against the diabetes label after clustering, and the main errors and weaknesses are described below.")
cur = P[204]
ct = [("K-Means cluster 0", 120, 128, 248, "52%"), ("K-Means cluster 1", 291, 44, 335, "13%"), ("K-Means cluster 2", 89, 96, 185, "52%"), ("DBSCAN noise (-1)", 40, 48, 88, "55%"), ("DBSCAN cluster 0", 460, 220, 680, "32%")]
tb = new_table(cur._p, ["Group", "No diabetes", "Diabetes", "Total", "Diabetes rate"], ct, [5, 3, 3, 2.5, 3]); cur = tb._tbl
cur = paras(type("X", (), {"_p": cur})(), ["Table 7.3: Cross-tabulation of clusters and the diabetes label (the label was not used to build the clusters)."])
cur = picture(cur._p, "figures/08_kmeans_outcome_rate.png", 7, "Figure 7.7: Diabetes rate in each K-Means cluster")
err = ["The clusters overlap. The silhouette score of 0.195 is low, and in Figure 7.6 the three groups touch each other.",
       "Insulin (374 values, 48.7%) and skin thickness (227 values, 29.6%) are heavily filled with the median, which may hide real differences between patients.",
       "Choosing k = 3 is a judgement, because k = 2 has almost the same silhouette score.",
       "About 28% of the patients in the older, high-risk group and about 13% in the younger low-risk group are examples that do not match their group's diabetes rate, so group membership says little about any single patient."]
err[3] = "Group membership says little about any single patient: 44 patients in the lowest-risk group (cluster 1) have diabetes, and 120 patients in cluster 0 do not."
cur = paras(type("X", (), {"_p": cur})(), err, like=BUL)

set_text(P[206], "K-Means gave more useful segments than DBSCAN. The three groups differ in age, body measurements and diabetes rate (13% against 52%), and they are very stable (mean ARI 0.991, minimum 0.981 over ten random starts). The diabetes label was not used to build the groups, so the difference in diabetes rate is independent evidence that the groups carry clinical meaning.")
cur = paras(P[206], ["The groups are not sharply separated. The data behaves more like one continuous cloud of patients that K-Means cuts into three regions than like three distinct types of patient.",
 "DBSCAN found one dense group of 680 patients and 88 noise patients. The noise group has higher glucose (146), much higher insulin (266) and a higher pedigree function (0.81) than the main group, and a diabetes rate of 55% against 32%. DBSCAN is therefore better used here to flag unusual high-risk patients. Only two settings in the whole grid produced two clusters, and in both the second cluster had 4 or 5 patients, which is a pocket of outliers and not a patient segment.",
 "The results describe patients with similar measurements. They are not diagnoses and must not be used for medical decisions."])
h = clone(H2, "7.5 Web Application Output", cur._p)
cur = clone(BODY, "A Streamlit web application was built so that the results can be explored interactively. Its pages are shown below.", h._p)
cur = picture(cur._p, "screenshots/app_1_dataset.png", 9.5, "Figure 7.8: Dataset page (patients, features, diabetes rate and the first rows of data)")
cur = picture(cur._p, "screenshots/app_2_kmeans.png", 9.5, "Figure 7.9: K-Means page with the k slider, quality scores and PCA scatter plot")
cur = picture(cur._p, "screenshots/app_3_dbscan.png", 9.5, "Figure 7.10: DBSCAN page with eps and min_samples sliders (shown here at eps = 2.9 and min_samples = 22)")
cur = picture(cur._p, "screenshots/app_4_lookup.png", 9.5, "Figure 7.11: Patient lookup page, which places a new patient in the most similar K-Means group")

# ------------------------------------------------ 8 conclusion
set_text(P[223], "Using K-Means with k = 3, the 768 patients fell into three stable and interpretable groups with very different diabetes rates (52%, 13% and 52%), although the groups overlap (silhouette score 0.195). DBSCAN found one main group and 88 unusual patients and did not give separate segments. All four objectives were met: the data was cleaned and scaled, both algorithms were applied, they were evaluated with several measures and compared, and the results were checked against the diabetes label and presented in a web application. For patient segmentation on this data K-Means is the better method, and DBSCAN is useful for spotting outliers.")
set_text(P[225], "The data covers only women aged 21 or older of Pima Indian heritage, so the groups may not hold for other patients. There are only 768 patients. Insulin and skin thickness are heavily filled with the median. Clusters describe similarity of measurements and are not diagnoses. The choice of k = 3 is a judgement. No doctor checked whether the groups are clinically useful.")
set_text(P[227], "Try Gaussian mixture models and hierarchical clustering, which can handle overlapping groups.")
set_text(P[228], "Handle missing insulin and skin thickness with better methods (for example model-based imputation) and compare the clusters.")
set_text(P[229], "Test the approach on a larger and more varied hospital dataset, and ask clinicians to judge whether the groups are useful.")

# ------------------------------------------------ 9 references
refs = ["[1] Smith, J.W., Everhart, J.E., Dickson, W.C., Knowler, W.C. and Johannes, R.S. Using the ADAP learning algorithm to forecast the onset of diabetes mellitus. Proceedings of the Symposium on Computer Applications in Medical Care, 1988.",
 "[2] MacQueen, J. Some methods for classification and analysis of multivariate observations. Proceedings of the 5th Berkeley Symposium on Mathematical Statistics and Probability, 1967.",
 "[3] Lloyd, S. Least squares quantization in PCM. IEEE Transactions on Information Theory, 28(2), 1982.",
 "[4] Ester, M., Kriegel, H.-P., Sander, J. and Xu, X. A density-based algorithm for discovering clusters in large spatial databases with noise. Proceedings of KDD, 1996.",
 "[5] Rousseeuw, P.J. Silhouettes: a graphical aid to the interpretation and validation of cluster analysis. Journal of Computational and Applied Mathematics, 20, 1987.",
 "[6] Davies, D.L. and Bouldin, D.W. A cluster separation measure. IEEE Transactions on Pattern Analysis and Machine Intelligence, PAMI-1(2), 1979.",
 "[7] Pedregosa, F. et al. Scikit-learn: Machine learning in Python. Journal of Machine Learning Research, 12, 2011.",
 "[8] UCI Machine Learning. Pima Indians Diabetes Database. Kaggle. https://www.kaggle.com/datasets/uciml/pima-indians-diabetes-database",
 "[9] Streamlit Inc. Streamlit documentation. https://docs.streamlit.io"]
for p, t in zip(P[258:263], refs[:5]): set_text(p, t)
paras(P[262], refs[5:])

for p in d.paragraphs:
    if p.text.startswith('Use a consistent referencing'): p._p.getparent().remove(p._p)
# ------------------------------------------------ 10 appendices
set_text(P[281], "Dataset URL: https://www.kaggle.com/datasets/uciml/pima-indians-diabetes-database\nFirst five records of the data used:")
sample = raw.head(5)
tb = new_table(P[281]._p, list(sample.columns), [list(r) for r in sample.values.tolist()], [1.5, 1.6, 2.0, 2.0, 1.6, 1.4, 2.4, 1.3, 1.6], size=8); 
set_text(P[283], "Repository URL: https://github.com/TharunS2006/CleanEnergy/tree/claude/new-session-uqjqaj/ml_mini_project")
set_text(P[285], "K-Means results for k = 2 to 8:")
rows = [(int(r.k), f"{r.inertia:.1f}", f"{r.silhouette:.3f}", f"{r.davies_bouldin:.3f}", f"{r.calinski_harabasz:.1f}") for r in ksel.itertuples()]
tb = new_table(P[285]._p, ["k", "Inertia", "Silhouette", "Davies-Bouldin", "Calinski-Harabasz"], rows, [1.5, 3, 3, 3.5, 4]); cur = tb._tbl
cur = paras(type("X", (), {"_p": cur})(), ["DBSCAN grid (selected rows). Smallest cluster is the size of the smallest cluster as a share of all patients:"])
sel = dgrid[((dgrid.eps == 1.0) & (dgrid.min_samples == 5)) | ((dgrid.eps == 1.5) & (dgrid.min_samples == 8)) | ((dgrid.eps == 2.0) & (dgrid.min_samples.isin([5, 16]))) | ((dgrid.eps == 2.1) & (dgrid.min_samples == 5)) | ((dgrid.eps == 2.5) & (dgrid.min_samples == 16))]
rows = [(f"{r.eps:.1f}", int(r.min_samples), int(r.clusters), f"{r.noise_pct:.1f}%", f"{r.smallest_cluster_pct:.1f}%") for r in sel.itertuples()]
tb = new_table(cur._p, ["eps", "min_samples", "Clusters", "Noise", "Smallest cluster"], rows, [2.5, 3, 3, 3, 4]); cur = tb._tbl
cur = picture(cur, "figures/05_dbscan_kdistance.png", 10, "Figure C.1: k-distance plot (distance to the 16th nearest neighbour)")
fill_table(T[8], [(f"{STUDENTS[0][0]} / {STUDENTS[0][1]}", "Data cleaning, exploratory analysis and K-Means", "Zero-value handling, imputation, scaling, EDA plots, choice of k", ""),
 (f"{STUDENTS[1][0]} / {STUDENTS[1][1]}", "DBSCAN, evaluation and comparison", "k-distance plot, grid search, metrics, stability test", ""),
 (f"{STUDENTS[2][0]} / {STUDENTS[2][1]}", "Web application, visualisation and report", "Streamlit app, PCA plots, report writing", "")])

# ------------------------------------------------ layout: remove blank spacer paragraphs, page breaks, black text
def is_blank(p):
    x = p._p.xml
    return p.text.strip() == "" and "<w:br" not in x and "w:drawing" not in x and "w:sectPr" not in x
for p in list(d.paragraphs):
    if is_blank(p): p._p.getparent().remove(p._p)
for p in d.paragraphs:
    t = p.text.strip()
    if p.style.name == "Heading 1" and (t.startswith("ABSTRACT") or t.startswith("TABLE OF CONTENTS") or re.match(r"^(1|10)\. ", t) or t.startswith("FACULTY EVALUATION")):
        p.paragraph_format.page_break_before = True
for p in d.paragraphs:   # the R.M.K header before ACKNOWLEDGEMENT also starts a page
    if p.text.strip().startswith("R.M.K College") and p.style.name == "Heading 1":
        nxt = p._p.getnext()
        # page break only if not already following an explicit page-break paragraph
        prev = p._p.getprevious()
        if prev is not None and "w:type=\"page\"" not in prev.xml and 'w:type="page"' not in prev.xml: p.paragraph_format.page_break_before = True
# black font everywhere
black = RGBColor(0, 0, 0)
for st in d.styles:
    try:
        if st.font is not None: st.font.color.rgb = black
    except Exception: pass
def blacken(par):
    for r in par.runs: r.font.color.rgb = black
for p in d.paragraphs: blacken(p)
for t in d.tables:
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs: blacken(p)
for shd in d.element.body.iter(qn("w:shd")):
    f = shd.get(qn("w:fill"))
    if f and f.lower() not in ("auto", "ffffff"):
        try:
            rgb = [int(f[i:i+2], 16) for i in (0, 2, 4)]
            if sum(rgb) / 3 < 200: shd.set(qn("w:fill"), "D9D9D9")
        except Exception: pass

# ---- justify, keep-with-next, page borders
from docx.oxml import OxmlElement
for p in d.paragraphs:
    sn = p.style.name
    has_pic = "w:drawing" in p._p.xml
    if has_pic:
        p.paragraph_format.keep_with_next = True; continue
    if sn.startswith("Heading"):
        p.paragraph_format.keep_with_next = True; continue
    if p.runs and p.runs[0].font.name == "Courier New":
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT; continue
    if p.alignment == CENTER or p.runs and p.runs[0].italic and p.text.startswith(("Figure","Table")):
        continue
    if len(p.text) > 60: p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
for sec in d.sections:
    sp = sec._sectPr
    for b in sp.findall(qn("w:pgBorders")): sp.remove(b)
    pb = OxmlElement("w:pgBorders"); pb.set(qn("w:offsetFrom"), "page")
    for side in ("top","left","bottom","right"):
        e = OxmlElement("w:"+side); e.set(qn("w:val"),"single"); e.set(qn("w:sz"),"12"); e.set(qn("w:space"),"24"); e.set(qn("w:color"),"000000"); pb.append(e)
    pgm = sp.find(qn("w:pgMar")); (pgm.addnext(pb) if pgm is not None else sp.append(pb))
for t in d.tables:
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr(); e = OxmlElement("w:cantSplit"); trPr.append(e)
d.save("ML_Mini_Project_Report.docx"); print("saved")
