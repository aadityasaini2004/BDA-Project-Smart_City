# 🌆 SmartCity – Air Quality & Pollution Intelligence Platform

**Transforming real-world environmental data into actionable smart city intelligence through Big Data Engineering.**

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![Apache Spark](https://img.shields.io/badge/Apache%20Spark-PySpark-orange?logo=apachespark&logoColor=white)
![Databricks](https://img.shields.io/badge/Platform-Databricks-red?logo=databricks&logoColor=white)
![Delta Lake](https://img.shields.io/badge/Storage-Delta%20Lake-00A1E0)
![Power BI](https://img.shields.io/badge/Visualization-Power%20BI-yellow?logo=powerbi&logoColor=black)
![License](https://img.shields.io/badge/License-Academic%20Project-lightgrey)

---

## 📌 Project Overview

SmartCity – Air Quality & Pollution Intelligence Platform is a Big Data Engineering project designed to collect, process, analyze, and visualize real-world environmental data across six major Indian cities.

The project integrates air quality measurements, official AQI information, and historical weather data from multiple public data sources using API-based data extraction.

Using **Apache Spark, PySpark, Databricks, and Delta Lake**, the collected data will be processed through an end-to-end ETL pipeline based on the Medallion Architecture (Bronze, Silver, and Gold).

The processed data will then be used to develop interactive dashboards using Microsoft Power BI, helping users understand pollution trends, compare cities, identify pollution hotspots, and explore relationships between weather conditions and air quality.

**This project uses independently collected real-world data through APIs and approved public sources. Kaggle datasets are not used.**

---

## 🎯 Project Objectives

The primary objectives of this project are:

- Collect real-world environmental data from multiple public APIs.
- Analyze air pollution levels across six Indian metropolitan cities.
- Retrieve historical weather information for environmental analysis.
- Build a scalable data ingestion and processing pipeline using Apache Spark.
- Implement the Bronze, Silver, and Gold Medallion Architecture.
- Store processed data using Delta Lake.
- Perform city-wise, monthly, and historical pollution analysis.
- Identify pollution hotspots and environmental trends.
- Explore correlations between weather conditions and air pollution.
- Develop interactive dashboards using Power BI.
- Demonstrate practical applications of Big Data technologies.

---

## 🌍 Cities Covered

The project initially focuses on six major Indian cities.

| No. | City | State |
|---|---|---|
| 1 | Delhi | Delhi |
| 2 | Mumbai | Maharashtra |
| 3 | Bengaluru | Karnataka |
| 4 | Kolkata | West Bengal |
| 5 | Chennai | Tamil Nadu |
| 6 | Hyderabad | Telangana |

### 📅 Historical Data Period

**Start Date:** November 1, 2025  
**End Date:** October 31, 2026

The project aims to analyze 12 months of historical environmental data.

Actual coverage will depend on the availability of historical measurements from each source and monitoring station. Missing observations will be documented rather than artificially generated.

---

## 📊 Data Sources

The project uses multiple independent public data sources to build a comprehensive environmental dataset.

### 1. OpenAQ – Air Quality Data

**Website:** https://openaq.org/  
**API Documentation:** https://docs.openaq.org/

OpenAQ provides access to global air quality measurements collected from monitoring stations.

Data fields to be collected:

- PM2.5 – Fine particulate matter
- PM10 – Coarse particulate matter
- NO2 – Nitrogen dioxide
- SO2 – Sulfur dioxide
- CO – Carbon monoxide
- O3 – Ozone
- Monitoring station name and ID
- Measurement timestamp
- Latitude and longitude
- Measurement units

**Purpose:** Analyze pollutant concentrations and compare air quality across different cities and monitoring stations.

Note: OpenAQ measurements represent pollutant concentrations, not necessarily official AQI readings.

### 2. Open-Meteo – Historical Weather Data

**Website:** https://open-meteo.com/  
**API Documentation:** https://open-meteo.com/en/docs/historical-weather-api

Open-Meteo provides historical weather information through its public API.

Data fields to be collected:

- Temperature
- Relative humidity
- Wind speed
- Wind direction
- Precipitation
- Atmospheric pressure
- Date and hourly timestamps

**Purpose:** Explore how weather conditions relate to changes in pollution levels.

Weather records are model-based historical estimates and should not automatically be interpreted as direct monitoring-station observations.

### 3. CPCB / data.gov.in – Official Indian AQI Data

**Website:** https://www.data.gov.in/  
**AQI Resource:** https://www.data.gov.in/catalog/real-time-air-quality-index

The Central Pollution Control Board (CPCB) and India's Open Government Data platform provide official environmental and air quality information.

Data fields to be collected, wherever accessible:

- Official AQI readings
- AQI category
- Monitoring station details
- City and state
- Pollutant information
- Observation timestamps

**Purpose:** Compare official Indian AQI information with pollutant measurements and support city-level air quality analysis.

Historical availability, API access, and licensing will be verified before integration.

---

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Data extraction and automation |
| REST APIs | Real-world data acquisition |
| Apache Spark | Distributed data processing |
| PySpark | Data transformation and analysis |
| Databricks | Big Data development and execution |
| Delta Lake | Reliable data storage |
| Spark SQL | Analytical queries |
| Power BI | Interactive dashboards |
| Git | Version control |
| GitHub | Team collaboration and source code management |
| VS Code | Local development environment |

---

## 🏗️ System Architecture

The project follows an end-to-end Big Data processing architecture.

```text
             REAL-WORLD DATA SOURCES
                       |
          +------------+------------+
          |            |            |
        OpenAQ     Open-Meteo      CPCB
          |            |            |
          +------------+------------+
                       |
                       v
              DATA EXTRACTION
             Python / REST APIs
                       |
                       v
               RAW DATA STORAGE
                 JSON / CSV
                       |
                       v
             APACHE SPARK / PYSPARK
                       |
                       v
              BRONZE DATA LAYER
                Raw Delta Tables
                       |
                       v
              SILVER DATA LAYER
          Cleaning and Transformation
                       |
                       v
               GOLD DATA LAYER
             Analytical Delta Tables
                       |
                       v
                  POWER BI
                       |
                       v
             INTERACTIVE DASHBOARD
```

### Medallion Architecture

The project implements three data processing layers.

#### 🥉 Bronze Layer – Raw Data

The Bronze layer stores the original extracted data from different sources.

Responsibilities:

- Ingest raw API responses.
- Preserve source-specific information.
- Store ingestion timestamps.
- Maintain source metadata.
- Preserve original measurements and units.

Proposed tables:

- `bronze_openaq`
- `bronze_weather`
- `bronze_cpcb`

#### 🥈 Silver Layer – Cleaned Data

The Silver layer contains validated and standardized datasets.

Responsibilities:

- Handle missing values.
- Remove duplicate records.
- Standardize column names.
- Normalize timestamps.
- Validate data types.
- Standardize measurement units.
- Handle invalid observations.
- Integrate compatible weather and pollution records.

Proposed tables:

- `silver_air_quality`
- `silver_weather`
- `silver_aqi`

#### 🥇 Gold Layer – Analytical Data

The Gold layer contains aggregated and analysis-ready datasets.

Responsibilities:

- City-wise pollution analysis.
- Daily and monthly aggregations.
- Historical trend analysis.
- Pollution hotspot identification.
- Weather and pollution correlation analysis.
- Dashboard-ready data preparation.

Proposed tables:

- `gold_city_daily`
- `gold_city_monthly`
- `gold_pollution_hotspots`
- `gold_weather_correlation`

---

## 📈 Planned Analytics & Dashboard

The final Power BI dashboard will provide interactive environmental insights.

### Dashboard Modules

**1. Air Quality Overview**

- Average pollutant concentrations.
- Official AQI overview where available.
- City-wise comparison.
- Total monitoring stations.
- Data coverage indicators.

**2. City-wise Pollution Analysis**

- PM2.5 comparison.
- PM10 comparison.
- NO2, SO2, CO, and O3 analysis.
- City-level pollutant distribution.

**3. Pollution Hotspot Analysis**

- Monitoring station locations.
- Geographic pollution distribution.
- Identification of high-concentration areas.

**4. Historical Trend Analysis**

- Daily pollution trends.
- Monthly pollutant averages.
- Seasonal patterns.
- City-wise historical comparisons.

**5. Weather & Pollution Analysis**

- Temperature versus pollution.
- Humidity versus pollution.
- Wind speed versus pollution.
- Rainfall and pollution patterns.
- Statistical correlation analysis.

### Planned KPIs

- Average PM2.5 concentration.
- Average PM10 concentration.
- Average official AQI where available.
- Maximum recorded AQI.
- Most polluted city for the selected period.
- Total monitoring stations.
- Number of valid observations.
- Data completeness percentage.

All dashboard metrics will be generated from validated source records. Illustrative or incomplete data will not be presented as actual findings.

---

## 📁 Repository Structure

```text
SmartCity-Air-Quality-Intelligence/
│
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
│
├── config/
│   ├── cities.json
│   ├── settings.py
│   └── logging_config.py
│
├── extraction/
│   ├── openaq/
│   │   ├── locations.py
│   │   ├── sensors.py
│   │   └── measurements.py
│   │
│   ├── weather/
│   │   └── historical_weather.py
│   │
│   └── cpcb/
│       └── cpcb_extractor.py
│
├── data/
│   ├── raw/
│   │   ├── openaq/
│   │   ├── weather/
│   │   └── cpcb/
│   │
│   ├── processed/
│   └── sample/
│
├── databricks/
│   ├── notebooks/
│   │   ├── 01_bronze_ingestion.py
│   │   ├── 02_silver_cleaning.py
│   │   ├── 03_gold_analytics.py
│   │   └── 04_data_validation.py
│   │
│   └── sql/
│       ├── bronze_tables.sql
│       ├── silver_tables.sql
│       └── gold_tables.sql
│
├── analytics/
│   ├── analytical_queries.sql
│   └── data_dictionary.md
│
├── dashboard/
│   ├── README.md
│   └── SmartCity_Dashboard.pbix
│
├── tests/
│   ├── test_extraction.py
│   └── test_transformations.py
│
├── docs/
│   ├── project_proposal.md
│   ├── architecture.md
│   ├── data_sources.md
│   ├── etl_documentation.md
│   ├── team_contributions.md
│   └── screenshots/
│
└── reports/
    ├── final_report.md
    └── presentation/
```

---

## ⚙️ Development Environment Setup

### Prerequisites

Install the following tools:

- Python 3.11 or later
- Visual Studio Code
- Git
- Databricks Free Edition or another approved Databricks workspace
- Power BI Desktop (Windows)

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/SmartCity-Air-Quality-Intelligence.git

cd SmartCity-Air-Quality-Intelligence
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate on Windows:

```bash
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory.

Example:

```env
OPENAQ_API_KEY=your_openaq_api_key
CPCB_API_KEY=your_cpcb_api_key

START_DATE=2025-11-01
END_DATE=2026-10-31

ENVIRONMENT=development
```

Only configure credentials for APIs that actually require them.

**Important:** Never commit `.env` or API keys to GitHub.

### 5. Run Data Extraction

Example:

```bash
python extraction/weather/historical_weather.py
```

Other extraction scripts will be executed once their implementations are completed.

### 6. Databricks Execution

The main Spark ETL pipeline will run inside Databricks.

General workflow:

1. Connect the GitHub repository to Databricks using Git Folders.
2. Configure an appropriate data storage location.
3. Import or synchronize the project notebooks.
4. Execute Bronze ingestion.
5. Execute Silver transformations.
6. Execute Gold aggregations.
7. Validate the generated Delta tables.

### 7. Power BI Integration

Once the Gold tables are available:

1. Open Power BI Desktop.
2. Connect to Databricks SQL Warehouse if supported.
3. Authenticate using the configured credentials.
4. Import the required Gold tables.
5. Develop the interactive dashboard.

CSV exports from the Gold layer may be used as an alternative if direct connectivity is unavailable.

---

## 👥 Team Members & Responsibilities

This project is developed collaboratively by a four-member team.

| Member | Role | Responsibilities |
|---|---|---|
| Aaditya Saini | Team Lead | Architecture, GitHub management, integration, coordination, testing and documentation |
| Rudransh | Data Acquisition Lead | API integration, real-world data collection, extraction scripts and source documentation |
| Sparsh | Data Engineering Lead | Apache Spark, PySpark, Databricks, Delta Lake and ETL implementation |
| Kartik | Analytics & Visualization Lead | SQL analytics, Power BI dashboards, KPIs and environmental insights |

### Contribution Areas

**Aaditya Saini**
- Overall project architecture.
- Repository management.
- Cross-module integration.
- Technical coordination.
- Documentation and final submission.

**Rudransh**
- OpenAQ integration.
- Open-Meteo integration.
- CPCB / government data research.
- Historical data collection.
- API extraction and error handling.

**Sparsh**
- Databricks environment.
- Bronze, Silver and Gold layers.
- PySpark transformations.
- Delta Lake implementation.
- Data quality validation.

**Kartik**
- Analytical SQL.
- City-wise comparisons.
- Pollution hotspot analysis.
- Power BI dashboard.
- Data visualization and insights.

All team members are expected to understand the complete project pipeline.

---

## 🌿 GitHub Collaboration Workflow

We follow a feature-branch workflow to maintain code quality and collaboration.

### Branch Strategy

| Branch | Purpose |
|---|---|
| `main` | Stable and integrated code |
| `integration` | Cross-module integration |
| `feature/data-extraction` | API extraction |
| `feature/spark-etl` | Spark and Databricks ETL |
| `feature/powerbi-dashboard` | Dashboard development |

### Contribution Process

1. Clone the repository.
2. Switch to your assigned feature branch.
3. Implement your assigned functionality.
4. Test your changes locally or in Databricks.
5. Commit changes with meaningful messages.
6. Push changes to GitHub.
7. Create a Pull Request.
8. Get the changes reviewed.
9. Merge approved changes into the integration branch.

Example:

```bash
git checkout feature/data-extraction

git add .

git commit -m "feat: implement OpenAQ data extraction"

git push origin feature/data-extraction
```

### Contribution Guidelines

- Write readable and maintainable code.
- Use meaningful variable and function names.
- Avoid committing credentials.
- Document new functionality.
- Test changes before submitting Pull Requests.
- Avoid pushing large raw datasets.
- Coordinate schema changes with the team.

---

## 🔍 Data Quality & Validation

Data reliability is a critical part of this project.

We will implement validation checks for:

- Missing values.
- Duplicate observations.
- Invalid timestamps.
- Incorrect measurement units.
- Invalid geographical coordinates.
- Missing city or station identifiers.
- Unexpected pollutant values.
- Source-specific data inconsistencies.
- Record counts across ETL stages.

We will preserve source information and record the transformations applied to the data.

---

## 🗓️ Project Timeline

| Date | Milestone |
|---|---|
| November 10, 2026 | Repository and project initialization |
| November 11–12, 2026 | API integration and historical data extraction |
| November 13, 2026 | Bronze layer implementation |
| November 14, 2026 | Silver layer implementation |
| November 15, 2026 | Gold layer implementation |
| November 16, 2026 | Analytics and validation |
| November 17, 2026 | Power BI development |
| November 18, 2026 | Integration and testing |
| November 19, 2026 | Documentation and final preparation |
| November 20, 2026 | Final submission |

---

## 🚀 Expected Project Outcomes

By the end of this project, we aim to deliver:

- A multi-source real-world environmental data collection system.
- Historical datasets covering six Indian cities, subject to source availability.
- A Python-based API ingestion pipeline.
- A complete Apache Spark / PySpark ETL workflow.
- Bronze, Silver, and Gold Delta tables.
- A validated and documented data processing architecture.
- City-wise pollution and weather analytics.
- An interactive Power BI dashboard.
- Technical documentation and a final project report.

---

## 📚 Learning Outcomes

Through this project, we aim to gain practical experience in:

- Big Data concepts and architecture.
- REST API integration.
- Python-based data engineering.
- Distributed processing using Apache Spark.
- PySpark DataFrame operations.
- Databricks workspace and notebook management.
- Delta Lake storage.
- Medallion Architecture.
- Data cleaning and transformation.
- SQL-based analytics.
- Power BI visualization.
- Git and collaborative software development.

---

## ⚠️ Important Notes

- Kaggle datasets are not used in this project.
- Data will be collected from publicly accessible APIs and approved public resources.
- Actual historical data availability may vary across cities, stations, and pollutants.
- Official AQI and pollutant concentrations will be treated as different metrics.
- Missing data will not be artificially generated.
- API usage will follow source-specific access restrictions and licensing terms.
- Large raw datasets and secret credentials will not be committed to GitHub.

---

## 📄 Academic Project Information

**Project Title:** SmartCity – Air Quality & Pollution Intelligence Platform

**Subject:** Big Data

**Academic Program:** B.Tech – Computer Science and Engineering (AI & ML)

**Team Size:** 4 Members

**Project Deadline:** November 20, 2026

**Project Repository:** SmartCity-Air-Quality-Intelligence

---

## 🤝 Acknowledgements

We acknowledge the public data providers and open-source communities whose resources and technologies make this project possible.

- OpenAQ
- Open-Meteo
- Central Pollution Control Board (CPCB)
- India Open Government Data Platform
- Apache Spark
- Databricks
- Delta Lake
- Microsoft Power BI

---

**Built with curiosity, collaboration, and Big Data Engineering.** 🚀

*SmartCity – Turning Environmental Data into Meaningful Insights.*
