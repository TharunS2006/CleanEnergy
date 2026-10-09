# CloudPulse mini-project report

`output/CloudPulse_Mini_Project_Report.docx` (editable) and `.pdf` (43-page layout of the RMKCET template).

Fill in before submitting: register number, student name, year/semester and guide on the cover and Bonafide pages
(marked with brackets or blanks), then re-save the PDF from Word.

Rebuild after editing the text in `content_*.py`:

```bash
pip install python-docx          # LibreOffice (soffice) and poppler-utils must be installed
python3 build_report.py          # writes output/*.docx and *.pdf with real page numbers
```

`diagrams/` holds the hand-drawn SVG sources (`fig_*.py`) of the architecture, credential-flow, pipeline and
lifecycle figures; render with `node render.js in.svg out.png width height`.
