# 🏎️ F1 Parts Traceability & Integrity Analytics Platform

A graph-based **Formula 1 parts traceability and integrity analytics platform** built using **Neo4j, Python, Cypher, NetworkX, and a locally hosted Qwen 2.5 LLM**.

The system simulates an F1 season with teams, cars, drivers, races, and replaceable components, tracks the complete lifecycle of each component, detects traceability and integrity violations, visualizes component lineage, and enables users to query the graph using natural language.

---

## 📌 Overview

Modern motorsport operations require reliable tracking of critical components across vehicles, races, replacements, and maintenance events.

This project demonstrates how a **graph database** can be used to model and analyze component relationships that are difficult to represent efficiently using traditional relational structures.

The platform maintains:

* Team and car relationships
* Driver assignments
* Component inventories
* Component installation and removal history
* Race-level component usage
* Component replacement lineage
* Integrity and traceability violations
* Team-level risk information

A local **Qwen 2.5** LLM is integrated to translate natural-language questions into **read-only Cypher queries**, execute them against Neo4j, and convert the results into human-readable answers.

---

## 🎯 Key Objectives

The project was designed to demonstrate:

1. **Graph-based traceability**
2. **Component lifecycle management**
3. **Historical event tracking**
4. **Replacement lineage analysis**
5. **Automated integrity checking**
6. **Graph-based anomaly detection**
7. **Natural-language database querying using an LLM**
8. **Operational risk reporting**
9. **Data visualization**

---

# 🏗️ System Architecture

```text
                         ┌──────────────────────┐
                         │   Synthetic F1 Data  │
                         │   generate_data.py   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │        Neo4j         │
                         │    Graph Database    │
                         └───────┬──────┬───────┘
                                 │      │
                  ┌──────────────┘      └───────────────┐
                  ▼                                     ▼
       ┌─────────────────────┐               ┌────────────────────┐
       │ Integrity Checking  │               │   Visualization    │
       │                     │               │                    │
       │ Cypher + Python     │               │ NetworkX + Matplotlib│
       └──────────┬──────────┘               └────────────────────┘
                  │
                  ▼
          ┌───────────────┐
          │ Flag Nodes    │
          │               │
          │ Violations    │
          └───────┬───────┘
                  │
                  ▼
       ┌──────────────────────┐
       │      Qwen 2.5        │
       │    Local LLM         │
       └──────────┬───────────┘
                  │
         Natural Language
                  │
                  ▼
       ┌──────────────────────┐
       │  Cypher Generation   │
       │       ↓              │
       │  Neo4j Query         │
       │       ↓              │
       │  Result Explanation  │
       └──────────────────────┘
```

---

# 🧩 Core Features

## 1. F1 Season Simulation

The project generates a synthetic F1 season containing:

* 5 teams
* 2 cars per team
* 10 cars
* Drivers
* 22 races
* Multiple component types
* Installation events
* Removal events
* Replacement events
* Crash-triggered replacements
* Scheduled replacements

### Supported components

| Component  | Example Usage Limit |
| ---------- | ------------------: |
| Engine     |                   4 |
| Gearbox    |                   6 |
| Turbo      |                   4 |
| ERS        |                   2 |
| Chassis    |                  22 |
| Front Wing |                   3 |
| Rear Wing  |                   3 |

> These limits are simulation parameters and are not intended to represent actual FIA regulations.

---

# 🕸️ Graph Data Model

The system uses Neo4j to represent the F1 ecosystem as a graph.

## Nodes

```text
Team
Car
Driver
Part
Race
Event
Flag
```

## Relationships

```text
Team ──OWNS──────> Car

Car ──DRIVEN_BY──> Driver

Part ──INSTALLED_ON──> Car

Part ──HAD_EVENT──> Event

Event ──AT_RACE──> Race

Event ──ON_CAR──> Car

Part ──REPLACED_BY──> Part

Flag ──ABOUT_PART──> Part

Flag ──ABOUT_CAR──> Car
```

---

# 🔍 Component Traceability

Each component is assigned a unique serial number.

Example:

```text
ENG-T1-001
ENG-T1-002
ENG-T1-003
```

A component can have a complete lifecycle:

```text
ENG-T1-001
      │
      ├── INSTALL → Race 1 → Car 1
      │
      ├── REMOVE  → Race 5 → Car 1
      │
      └── REPLACED_BY
              │
              ▼
          ENG-T1-002
              │
              ├── INSTALL → Race 5
              │
              └── REMOVE  → Race 9
```

This allows the system to answer:

* Where is a component currently installed?
* When was it installed?
* When was it removed?
* Which car used it?
* At which race was it used?
* Which component replaced it?
* What is the complete replacement lineage?

---

# 🚨 Integrity & Data Quality Checks

The system intentionally introduces synthetic violations so that the integrity-checking framework can be demonstrated.

## 1. Double Installation

Detects a component installed on multiple cars simultaneously.

```text
             ┌──> Car 1
ENG-T1-001 ──┤
             └──> Car 3
```

This is flagged as a `double_install` violation.

---

## 2. Orphan Removal

Detects a removal event for which there is no corresponding previous installation event on the same car.

```text
Part
 │
 └── REMOVE
       │
       └── No previous INSTALL
```

This is flagged as an `orphan_remove`.

---

## 3. Usage Limit Violation

Calculates component usage and identifies parts whose simulated usage exceeds their configured limit.

Example:

```text
Engine usage limit = 4 races

Installed: Race 1
Removed:   Race 7

Simulated usage = 6 races

6 > 4
```

The component is flagged as `over_limit`.

---

## 4. Replacement Lineage

Neo4j graph traversal is used to follow replacement chains.

```text
ENG-T1-001
     │
     ▼
ENG-T1-002
     │
     ▼
ENG-T1-003
     │
     ▼
ENG-T1-004
```

This provides a complete component lineage.

---

# 🤖 Natural Language Graph Querying

The project integrates a locally hosted **Qwen 2.5** model through Ollama.

Instead of requiring users to write Cypher manually:

```cypher
MATCH (f:Flag)-[:ABOUT_PART]->(p:Part)
RETURN p.serial_number, p.part_type
```

users can ask:

```text
Which parts are currently over their usage limit?
```

The system performs:

```text
Natural Language
       │
       ▼
     Qwen 2.5
       │
       ▼
  Cypher Generation
       │
       ▼
      Neo4j
       │
       ▼
    Query Result
       │
       ▼
     Qwen 2.5
       │
       ▼
Human-readable Answer
```

---

# 🔐 Read-Only LLM Querying

The LLM is intended to perform read-only graph queries.

Write operations such as:

```text
CREATE
MERGE
DELETE
SET
REMOVE
```

are blocked by the application-level query validation layer.

This prevents natural-language requests from directly modifying the Neo4j graph.

> For production deployment, a stronger Cypher parser/allowlist-based security layer should be used instead of relying only on keyword filtering.

---

# 📊 Visual Analytics

The project includes graph and statistical visualizations.

## Component Lineage Graph

The replacement relationships are represented using NetworkX:

```text
Part A
  │
  ▼
Part B
  │
  ▼
Part C
```

Output:

```text
lineage_graph.png
```

---

## Violations by Team

The system aggregates integrity violations by team and generates a bar chart.

Output:

```text
violations_by_team.png
```

This provides a high-level view of where simulated traceability issues are concentrated.

---

# 📑 Automated Season Risk Report

`season_report.py` collects relevant information from Neo4j and uses Qwen 2.5 to generate an executive-style report.

The report includes:

* Teams/cars associated with violations
* Component risks
* Replacement patterns
* Operational observations
* Recommended areas for investigation

Output:

```text
season_risk_report.md
```

---

# 📁 Project Structure

```text
f1-traceability-neo4j/
│
├── README.md
├── requirements.txt
│
├── constraints.cypher
│
├── generate_data.py
│
├── integrity_checks.cypher
├── integrity_checks.py
│
├── llm_agent.py
│
├── season_report.py
│
├── visualization.py
│
├── lineage_graph.png
├── violations_by_team.png
│
└── season_risk_report.md
```

---

# ⚙️ Technology Stack

| Technology | Purpose                                                 |
| ---------- | ------------------------------------------------------- |
| Python     | Application and data generation                         |
| Neo4j      | Graph database                                          |
| Cypher     | Graph querying                                          |
| Qwen 2.5   | Natural-language query generation and report generation |
| Ollama     | Local LLM inference                                     |
| NetworkX   | Graph visualization                                     |
| Matplotlib | Data visualization                                      |

---

# 💻 Requirements

Before running the project, install:

* Python 3.10+
* Neo4j Desktop or Neo4j Server
* Ollama
* Qwen 2.5 model
* Required Python packages

---

# 🚀 Installation

## 1. Clone the repository

```bash
git clone https://github.com/<YOUR_USERNAME>/f1-traceability-neo4j.git

cd f1-traceability-neo4j
```

---

## 2. Create a virtual environment

### Windows

```powershell
python -m venv .venv

.venv\Scripts\activate
```

### Linux/macOS

```bash
python3 -m venv .venv

source .venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

# 🗄️ Neo4j Setup

Start your Neo4j database.

The application expects Neo4j to be available at:

```text
bolt://localhost:7687
```

Default configuration:

```text
Username: neo4j
Password: <your_password>
```

If your Neo4j credentials are different, update the connection configuration in the Python files.

---

# 🧱 Create Database Constraints

Open Neo4j Browser and execute:

```text
constraints.cypher
```

This creates the required constraints and indexes.

---

# 📦 Generate the F1 Dataset

Run:

```bash
python generate_data.py
```

This creates the synthetic F1 season graph.

The generated graph contains:

```text
Teams
Cars
Drivers
Races
Parts
Events
Replacement Relationships
Synthetic Violations
```

---

# 🔎 Run Integrity Checks

Execute:

```bash
python integrity_checks.py
```

The system checks for:

```text
✓ Double installation
✓ Orphan removal
✓ Usage-limit violations
```

Detected problems are stored as `Flag` nodes in Neo4j.

---

# 📈 Generate Visualizations

For example:

```bash
python visualization.py engine
```

This generates:

```text
lineage_graph.png
violations_by_team.png
```

You can replace `engine` with another component type supported by the dataset.

---

# 🤖 Run the LLM Agent

First make sure Ollama is installed and running.

Pull the Qwen model configured by the project.

Then run:

```bash
python llm_agent.py "Which parts are over their usage limit?"
```

Other example queries:

```bash
python llm_agent.py "Which cars currently have flagged components?"
```

```bash
python llm_agent.py "Show me the replacement history of engine ENG-T1-001."
```

```bash
python llm_agent.py "Which teams have the most integrity violations?"
```

```bash
python llm_agent.py "Which parts were replaced after a crash?"
```

---

# 📋 Generate the Season Risk Report

Run:

```bash
python season_report.py
```

The generated report will be saved as:

```text
season_risk_report.md
```

---

# 🔄 End-to-End Workflow

```text
                START
                  │
                  ▼
       Generate Synthetic Season
                  │
                  ▼
             Create Parts
                  │
                  ▼
        Generate Race Events
                  │
                  ▼
          Store in Neo4j
                  │
                  ▼
       Inject Test Violations
                  │
                  ▼
        Run Integrity Checks
                  │
                  ▼
           Create Flags
                  │
          ┌───────┴────────┐
          ▼                ▼
     Visualization      LLM Agent
          │                │
          ▼                ▼
    Graph Analytics    Cypher Query
                           │
                           ▼
                         Neo4j
                           │
                           ▼
                     Query Results
                           │
                           ▼
                    Natural Language
                         Answer
```

---

# 🧠 Example Use Cases

The platform can be extended for:

### Component Lifecycle Management

Track every component from introduction to retirement.

### Traceability

Determine which vehicle and race were associated with a component.

### Root-Cause Analysis

Trace component replacements and related events.

### Data Quality Monitoring

Identify inconsistent or impossible component states.

### Operational Analytics

Analyze component replacement patterns across teams and races.

### Natural Language Analytics

Allow non-technical users to query graph data without knowing Cypher.

### Digital Twin / Simulation

Extend the synthetic season simulator into a larger motorsport operations simulation.

---

# 🔬 Data Science & Analytics Concepts Demonstrated

This project combines several data and AI concepts:

* Graph databases
* Graph traversal
* Entity and relationship modeling
* Synthetic data generation
* Data quality validation
* Anomaly detection
* Temporal event analysis
* Component lineage analysis
* Natural-language-to-query generation
* Local LLM inference
* Automated reporting
* Graph visualization
* Operational analytics

---

# ⚠️ Important Note

This project uses **synthetically generated F1 data**.

The teams, drivers, races, component usage limits, crash probabilities, and replacement rules are simulation parameters and should not be interpreted as actual Formula 1 operational data or FIA regulatory rules.

The project is intended as a technical demonstration of:

> **Graph-based traceability + integrity analytics + LLM-powered natural-language querying.**

---

# 🔮 Future Improvements

Potential extensions include:

* Real-time event ingestion using Kafka
* PostgreSQL + Neo4j hybrid architecture
* Stream-based integrity monitoring
* Graph-based anomaly detection
* Temporal graph analytics
* Neo4j Graph Data Science algorithms
* Interactive Streamlit dashboard
* Grafana monitoring
* Role-based access control
* Cypher query parser/allowlist
* Docker Compose deployment
* REST API
* Real-world publicly available motorsport datasets
* Predictive component failure models
* Component reliability scoring
* Automated alerting
* Historical season comparison

---

# 📌 Project Highlights

```text
✓ Graph-based F1 component traceability
✓ Component lifecycle tracking
✓ Replacement lineage analysis
✓ Automated integrity validation
✓ Synthetic anomaly injection
✓ Neo4j graph analytics
✓ Natural-language → Cypher querying
✓ Local Qwen 2.5 LLM
✓ Automated operational reporting
✓ NetworkX graph visualization
```

---

# 👨‍💻 Author

**Lohith Subramani**

M.Tech Data Analytics
National Institute of Technology, Tiruchirappalli

---

## ⭐ If you find this project useful

Feel free to star the repository and explore the implementation.
