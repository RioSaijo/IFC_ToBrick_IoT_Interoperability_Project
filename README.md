# IFC to Brick IoT Interoperability Project

## Overview
This repository explores interoperability between IFC-based building models and Brick Schema for IoT-enabled building systems.

The project focuses on:
- IFC entity and spatial information extraction
- BDNS-aligned classification and mapping
- Integration of BMS / IoT point metadata
- Rule-based inference of spatial and equipment relationships
- Generation and validation of Brick-compatible RDF graphs

The repository is currently an ongoing research prototype. The implementation is being reorganized to make the processing flow easier to understand, review, and reuse.

## Scope and Intent
- Analysis of IFC entity classification issues
- Examination of BDNS applicability and limitations
- Exploration of IFC-to-Brick mapping strategies
- Integration of static BIM information with operational point metadata
- Identification of model-level constraints affecting interoperability

The repository is intended for technical review, research discussion, and reproducible experimentation.

## Planned Architecture and Data Flow

The refactoring keeps the project structure intentionally simple. Each module has one primary responsibility, while the overall workflow remains visible from the repository root.

### Processing Flow

```text
IFC ----------------------+
                          |
                          v
                       ifc.py
                          |
                          v
                      mapping.py
                          |
                          +----------- points.py <--- BMS / IoT CSV
                          |
                          v
                     reasoning.py
                          |
                          v
                        rdf.py
                          |
                          v
                    validation.py
                          |
                          v
                    Brick RDF / TTL
```

The central design principle is:

```text
Input File
   ↓
Structured Python Objects
   ↓
Semantic Mapping
   ↓
Relationship Reasoning
   ↓
RDF Graph
   ↓
Validation
```

### Module Responsibilities

| Module | Main Input | Responsibility | Main Output |
| --- | --- | --- | --- |
| `pipeline.py` | Input paths and settings | Coordinates the overall workflow | Pipeline result |
| `models.py` | - | Defines shared data structures used between modules | IFC, equipment, point, relation, and graph objects |
| `ifc.py` | IFC file | Loads IFC and extracts required spatial, equipment, and relationship information | Structured IFC data |
| `mapping.py` | IFC data and mapping resources | Maps IFC / BDNS information to Brick concepts, prioritizing authoritative external mappings where available | Brick equipment and mapped entities |
| `points.py` | BMS / IoT CSV | Loads, normalizes, and maps operational point metadata | Brick point objects |
| `reasoning.py` | IFC and mapped entities | Infers spatial and equipment relationships such as location and feeds | Semantic relations |
| `rdf.py` | Mapped entities and relations | Builds and exports the RDF graph | Brick-compatible RDF / TTL |
| `validation.py` | RDF graph | Performs semantic validation, including SHACL where applicable | Validation result |

### Mapping Reference Policy

The current BDNS-to-Brick crosswalks included in this repository are primarily used as a research prototype and may contain manually curated or simulated correspondences.

Where authoritative mapping information is available, the implementation should preferentially reference public and machine-readable sources, such as the buildingSMART Data Dictionary (bSDD), official Brick Schema definitions and alignments, and other recognized standards or ontology mappings.

Project-specific mapping tables should therefore be treated as fallback, supplementary, or experimentally validated resources rather than as authoritative semantic definitions.

When no authoritative mapping can be identified, the mapping should be recorded explicitly as project-defined and should remain traceable for later review and validation.

### Main Inputs

```text
data/
├─ sample/
│  ├─ *.ifc
│  └─ *.csv
└─ output/
```

The two primary input sources are:

1. **IFC models**
   - Site, Building, Storey, and Space
   - HVAC and other building equipment
   - IFC containment and connectivity relationships
   - Geometry where explicit relationships are insufficient

2. **BMS / IoT point metadata**
   - Point IDs and names
   - Units
   - Equipment references
   - Space references
   - BDNS abbreviations or other semantic identifiers

### Expected Outputs

```text
data/output/
├─ building_brick.ttl
├─ provenance.csv
└─ validation_report.json
```

The main deliverable is a Brick-compatible RDF graph. Intermediate results may be exported for debugging or research evaluation, but they are not intended to become mandatory dependencies between modules.

## Planned Repository Structure

```text
IFC_ToBrick_IoT_Interoperability_Project/
├─ README.md
├─ requirements.txt
│
├─ src/
│  ├─ pipeline.py
│  ├─ models.py
│  ├─ ifc.py
│  ├─ mapping.py
│  ├─ points.py
│  ├─ reasoning.py
│  ├─ rdf.py
│  └─ validation.py
│
├─ resources/
│  ├─ bdns/
│  └─ mappings/
│
├─ data/
│  ├─ sample/
│  └─ output/
│
├─ notebooks/
│  ├─ experiments/
│  └─ archive/
│
├─ tests/
└─ docs/
```

The project will remain in this compact structure unless a module becomes sufficiently large or independent to justify further subdivision.

## Current Repository Contents

The current repository still contains the earlier prototype structure under `src/`, `notebook/`, `data/`, and `report/`. These files are being migrated gradually into the simplified architecture above.

Exploratory notebooks are retained as research records and are not treated as the primary implementation.

## Development Status
- The project is under active refactoring.
- Existing research logic will be retained while module responsibilities are simplified.
- The planned structure above represents the target organization for the next implementation stage.
- Some implementation details remain provisional.

## Notes
- This repository represents an intermediate research state.
- Not all components are currently intended to be directly executable.
- The project structure is intentionally kept compact to improve readability for public review.
