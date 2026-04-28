# IFC to Brick IoT Interoperability Project

## Overview
This repository explores interoperability between IFC based building models
and Brick Schema for IoT enabled building systems.

The work focuses on entity classification consistency,
BDNS aligned tagging, and rule based transformation concepts.

At the current stage, the project represents an ongoing research prototype.
Processing order and execution flow are not yet fully formalized.

## Scope and Intent
- Analysis of IFC entity classification issues
- Examination of BDNS applicability and limitations
- Exploration of IFC to Brick mapping strategies
- Identification of model level constraints affecting interoperability

This repository is intended for technical review and discussion
rather than direct or automated execution.


## Execution (experimental)
A preliminary execution entry point is provided.

```text
python run.py
```text

## Repository Structure
IFC_ToBrick_IoT_Interoperability_Project
├─ README.md
├─ .gitignore
├─ src
│  └─ app
│     ├─ pipeline.py
│     ├─ contracts.py
│     └─ __init__.py
├─ data
│
│
├─ notebook
│  └─ *.ipynb
├─ report
│  └─ *

## Directory Descriptions

### src
Contains Python modules representing the conceptual structure of the approach.

- `pipeline.py`  
  Defines the conceptual organization of the transformation process.
  Processing steps are described abstractly and may change.

- `contracts.py`  
  Defines assumptions, constraints, and classification or mapping rules
  used during analysis.

### data
Stores experimental and reference data generated or used during analysis.

- `data/notebook`  
  Contains notebooks used for validation, inspection, and case study specific experiments.

### notebook
Contains exploratory notebooks developed during early investigation stages.
These notebooks may reflect trial-and-error analysis and are not part of the final structure.

### report
Contains analysis notes, summary documents, or draft reports generated during the study.

### named
Contains naming related resources, such as naming rules, classification tables,
or intermediate artifacts related to BDNS or similar conventions.

## Development Status
- Processing order is under investigation.
- Some implementation decisions are provisional.
- Further refactoring and consolidation are expected.

## Notes
- This repository reflects an intermediate research state.
- Not all components are intended to be complete or directly executable.