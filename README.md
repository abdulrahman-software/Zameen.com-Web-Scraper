# Islamabad House Price Predictor
**AIC354 — Machine Learning Fundamentals Lab | CUI Islamabad | Spring 2026**
Abdul Rahman · SP24-BCS-003

An end-to-end machine learning system that scrapes Islamabad property listings from Zameen.com, trains six regression models, and serves a browser-based price estimator — no backend required.

---

## Project Structure

```
.
├── scraper.py               # Stage 1 — collect listings from Zameen.com
├── data_preprocessing.py    # Stage 2 — clean and encode the dataset (standalone)
├── model_training.py        # Stage 3 — train all models, export best to JSON
├── inference.py             # Stage 4 — PyScript inference module (runs in browser)
├── index.html               # Web application (loads inference.py via PyScript)
├── islamabad_properties.csv # Collected dataset (350 listings, 13 attributes)
├── model_data.json          # Serialised Gradient Boosting model (browser-ready)
├── model_results.csv        # Model comparison table (MAE, MSE, RMSE, R²)
└── README.md
```

---

## Requirements

```bash
pip install pandas numpy scikit-learn xgboost catboost playwright requests
playwright install chromium
```

Python 3.9 or higher recommended.

---

## Running the Pipeline

### Step 1 — Collect Data (optional — dataset already included)

Scrapes 350 residential property listings from Zameen.com and saves them to `islamabad_properties.csv`.

```bash
python scraper.py
```

**Note:** The scraper opens a visible browser window for the first run to allow manual CAPTCHA solving if Cloudflare blocks the session. After solving, press **Enter** in the terminal to resume. Collected URLs are cached in `urls.txt` — delete this file to re-scrape from scratch.

---

### Step 2 — Preprocess Data (optional — for inspection only)

Standalone script that cleans the dataset and prints shape statistics. Not required to run the web app.

```bash
python data_preprocessing.py
```

---

### Step 3 — Train Models (optional — model_data.json already included)

Trains all six models, prints a comparison table, saves `model_results.csv`, and exports the best model (Gradient Boosting, R² = 0.886) to `model_data.json`.

```bash
python model_training.py
```

Expected terminal output:

```
Model                  MAE              MSE          RMSE       R2
----------------------------------------------------------------------------------
Gradient Boosting   36,724,048  5,970,312,749,162,496   77,278,200   0.8860
Random Forest       36,849,074  6,213,484,251,234,816   78,789,580   0.8815
XGBoost             36,891,280  7,459,703,831,543,808   86,351,060   0.8577
...

Best model: Gradient Boosting (R2 = 0.886)
Exported model_data.json — use with index.html, no pkl needed
```

---

### Step 4 — Run the Web Application

> ⚠️ **The app must be served over HTTP.** Opening `index.html` directly as a `file://` URL will not work — PyScript blocks local file access for security reasons.

Start a local server from the project directory:

```bash
python -m http.server 8000
```

Then open your browser and go to:

```
http://localhost:8000
```

The app loads a Python runtime (Pyodide/WebAssembly) in the browser — this takes **5–15 seconds** on first load depending on your connection. Once the status indicator turns green and the button reads **"Estimate Price"**, the app is ready.

---

## Using the Web App

1. Select a **Location** from the dropdown (populated from the dataset)
2. Select a **Property Type** (House, Flat, etc.)
3. Enter **Area** in Marla
4. Enter **Bedrooms** and **Bathrooms**
5. Click **Estimate Price** or press **Enter**

The result panel displays the estimated price in Pakistani denomination (Lakh / Crore / Arab) and the exact PKR value.

---

## Model Performance Summary

| Model | MAE (PKR) | RMSE (PKR) | R² |
|---|---|---|---|
| **Gradient Boosting** | **36,724,048** | **77,278,200** | **0.8860** |
| Random Forest | 36,849,074 | 78,789,580 | 0.8815 |
| XGBoost | 36,891,280 | 86,351,060 | 0.8577 |
| CatBoost | 37,224,940 | 86,779,610 | 0.8563 |
| Decision Tree | 43,293,718 | 101,369,400 | 0.8039 |
| Linear Regression | 77,217,194 | 124,540,000 | 0.7039 |

The Gradient Boosting Regressor was selected as the best model and serialised to `model_data.json` for browser-native inference via PyScript.

---

## Key Design Decisions

- **No pickle files.** The model is exported as plain JSON, making it portable, human-readable, and safe to load in a browser without any Python dependency.
- **No backend server.** The entire inference pipeline runs client-side using PyScript (Pyodide/WebAssembly). The app can be hosted as a static site on GitHub Pages or any file host.
- **Parallel scraping.** Detail extraction is parallelised across 10 worker threads using `ThreadPoolExecutor`, significantly reducing total collection time.
- **Currency normalisation.** Pakistani denomination strings (Lakh, Crore, Arab) are parsed to raw PKR integers before training and re-formatted for display after inference.

---

## Dataset

- **Source:** Zameen.com — Islamabad residential listings
- **Collection date:** May 2026
- **Raw records:** 350
- **After cleaning:** 337
- **Attributes:** 13 (Price, Area, City, Bedrooms, Bathrooms, Location, Property\_Type, Built\_in\_year, Parking\_space, Servant\_Quarters, Store\_rooms, Kitchens, Drawing\_Rooms)
- **Train / Test split:** 80 / 20 (random\_state = 42)

---

*BS Computer Science — V Semester | Course: AIC354 | Instructor: Mr. Anayat Ullah*