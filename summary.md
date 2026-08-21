# Repository Summary: LineesPare (Warehouse Forecaster)

## Overview
This repository contains a **Streamlit-based web application** named "Warehouse Forecaster" (or "Inventory Forecaster"). The application is designed to analyze warehouse inventory data, calculate daily burn rates, and predict future stockout dates based on historical demand trends. The interface provides both a bulk alert dashboard for action-required items and an individual item deep-dive view with interactive charts.

## Technologies Used
* **Python 3.12**: Core programming language.
* **Streamlit**: Web framework for building the user interface.
* **Pandas**: Data manipulation and time-series analysis.
* **Plotly**: Interactive data visualization.
* **Docker**: Containerization for easy deployment (configured for services like Google Cloud Run).

## Key Files and Components

### Core Application
* **[`app.py`](file:///c:/Users/carlo/OneDrive/LineesPare/app.py)**: The main entry point of the Streamlit application. It handles the UI layout, loads the data, and contains the core logic (`predict_stockout_for_item`) to forecast when inventory will be depleted.
* **[`requirements.txt`](file:///c:/Users/carlo/OneDrive/LineesPare/requirements.txt)**: Lists the Python dependencies required to run the application (`streamlit`, `pandas`, `plotly`).

### Data Handling
* **[`data.py`](file:///c:/Users/carlo/OneDrive/LineesPare/data.py)**: A script used to generate realistic synthetic warehouse data (`synthetic_inventory.csv`) over a two-year timeline. It simulates demand and restocking events for thousands of items, including a slight growing trend.
* **[`synthetic_inventory.csv`](file:///c:/Users/carlo/OneDrive/LineesPare/synthetic_inventory.csv)**: The generated CSV dataset used by the application to demonstrate its forecasting capabilities.
* **[`ensaladilla.xls`](file:///c:/Users/carlo/OneDrive/LineesPare/ensaladilla.xls)**: Likely an original dataset, sample data, or supplementary file related to the project's domain.

### Deployment & Exploration
* **[`Dockerfile`](file:///c:/Users/carlo/OneDrive/LineesPare/Dockerfile)**: Defines the environment for running the Streamlit app inside a Docker container. It's configured to expose port 8080 and run on `0.0.0.0`, which is standard for cloud platforms like Google Cloud Run.
* **[`Linees_Pare.ipynb`](file:///c:/Users/carlo/OneDrive/LineesPare/Linees_Pare.ipynb)**: A Jupyter Notebook presumably used for initial exploratory data analysis (EDA), prototyping the forecasting algorithms, or model testing before moving the logic into the main app.
