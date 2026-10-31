# Hospital Patient Segmentation (K-Means and DBSCAN)

ML Mini Project, topic 19 (Clustering). Team: Tamilmani B (111624102217), Yuvraj U (111624102247), Vishnu Vardhan A (111624102241).

## Files
- `patient_segmentation.py`: full analysis (cleaning, K-Means, DBSCAN, PCA plots, cluster profiles).
- `build_report.py`: builds `Patient_Segmentation_Report.docx` from the results.
- `data/diabetes.csv`: Pima Indians Diabetes data (768 rows). Download the Kaggle copy and confirm it matches.
- `figures/`, `results/`: outputs. `results/run_log.txt` is the printed output of the last run.

## Web app (for demo)
```
pip install -r requirements.txt
python -m streamlit run app.py
```
On Windows you can also double-click `run_app.bat`. The browser opens at http://localhost:8501 with 5 pages: Dataset, K-Means (k slider), DBSCAN (eps and min_samples sliders), Find a patient's group, Summary and limits. Screenshots are in `screenshots/`.

## Run the analysis script
```
pip install -r requirements.txt
python3 patient_segmentation.py
python3 build_report.py
```

## Main results (from the actual run)
- K-Means k=3: groups of 248, 335 and 185 patients; diabetes rate 52%, 13%, 52% (label NOT used for clustering).
- Silhouette 0.195 (weak separation); stability across 10 seeds: ARI 0.991.
- DBSCAN (eps 2.0, min_samples 16): 1 cluster + 88 noise patients; works as an outlier detector here.

## Be ready to explain (viva questions)
1. **Why treat zeros as missing?** A glucose, BMI or blood pressure of 0 is impossible. Leaving zeros in would create fake low-value groups.
2. **Why median imputation?** Robust to outliers such as insulin up to 846. Limitation: insulin is about half imputed.
3. **Why standardise?** K-Means and DBSCAN use distances. Without scaling, insulin would dominate.
4. **Why not use Outcome?** Clustering is unsupervised. We used Outcome only afterwards to check if clusters mean something.
5. **How did you choose k?** Elbow had no sharp bend; silhouette tied for k=2 and 3; Davies-Bouldin was better at 3; k=3 gave balanced, interpretable groups. It is a judgement.
6. **Why is the silhouette low (0.195)?** The data forms one continuous cloud, so clusters overlap. We say this openly.
7. **How did you choose DBSCAN parameters?** min_samples about 2 x features; eps from the k-distance plot, then a grid. Only configs with tiny clusters (4 to 5 patients) found 2+ clusters, so we kept one cluster plus noise.
8. **K-Means vs DBSCAN?** K-Means needs k and finds round clusters; DBSCAN needs eps and handles noise and odd shapes. Here K-Means segments better; DBSCAN flags outliers.
9. **What are the limits?** Only Pima women aged 21+; 768 patients; heavy imputation; clusters are not diagnoses.
10. **What would you do next?** Gaussian mixture models, hierarchical clustering, better handling of missing insulin.

## Honest note
Read the code and the report, run the script yourselves, and be able to explain every step. The numbers above come from running this code on the dataset copy in `data/`.
