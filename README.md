# IFC to Brick IoT Interoperability Project



Project title and short description
Purpose and scope
Input and output
How to use
Project status
License and acknowledgements



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

## Planned Architecture and Data Flow

The refactored architecture is intended to preserve the current research objective while separating data ingestion, semantic mapping, relationship reasoning, linking, RDF serialization, and validation into explicit processing stages.

The central data-flow principle is:

```text
File
  ↓
Domain Object
  ↓
Semantic Object
  ↓
Relation
  ↓
RDF Graph
```

This separation is intended to prevent individual modules from simultaneously handling file parsing, semantic interpretation, relationship inference, and RDF serialization.

### Primary Inputs

The pipeline is designed around two primary information sources.

1. **IFC models**
   - Spatial hierarchy, including Site, Building, Storey, and Space.
   - Building equipment and distribution elements.
   - IFC relationships, including aggregation, containment, and port connectivity.
   - Geometry when spatial relationships cannot be obtained directly from explicit IFC relationships.

2. **BMS / IoT point metadata**
   - Point identifiers and names.
   - Units.
   - Equipment references.
   - Space references.
   - BDNS abbreviations or other semantic identifiers when available.

### Target Processing Flow

```text
                         INPUT
                           |
          +----------------+----------------+
          |                                 |
        IFC                              BMS / IoT
      *.ifc                                *.csv
          |                                 |
          v                                 v
   ingest/ifc.py                     ingest/points.py
          |                                 |
       IfcBundle                         PointTable
          |                                 |
          v                                 v
   mapping/bdns.py                   mapping/points.py
          |                                 |
   BdnsTaggedAssets                   BrickPointsSet
          |
          v
 mapping/equipment.py
          |
   BrickEquipmentSet
          |
          +---------------------+
          |                     |
          v                     v
 reasoning/spatial.py     reasoning/connectivity.py
          |                     |
          |                     v
          |              reasoning/equipment.py
          |                     |
          +----------+----------+
                     |
                     v
             linking/spatial.py
                     |
                     v
        linking/equipment_points.py
                     |
                     v
                 RelationSet
                     |
                     v
          serialization/rdf.py
                     |
                     v
                BrickGraph
                     |
                     v
           validation/shacl.py
                     |
                     v
                  OUTPUT
```

### Module Input and Output Responsibilities

| Module | Main Input | Responsibility | Main Output |
| --- | --- | --- | --- |
| `models.py` | - | Defines shared domain and semantic data structures | `IfcBundle`, `SpatialElement`, `BrickEquipment`, `BrickPoint`, `Relation`, `BrickGraph` |
| `config.py` | Configuration file or CLI parameters | Centralizes namespaces, paths, and mapping settings | `ProjectConfig` |
| `ingest/ifc.py` | IFC file | Loads IFC, detects schema, and extracts basic source information | `IfcBundle` |
| `ingest/points.py` | BMS / IoT point CSV | Loads and normalizes point metadata | `PointTable` |
| `mapping/bdns.py` | `IfcBundle` | Extracts BDNS annotations from IFC entities | `BdnsTaggedAssets` |
| `mapping/equipment.py` | `BdnsTaggedAssets`, mapping resources | Maps tagged IFC assets to Brick equipment classes | `BrickEquipmentSet` |
| `mapping/points.py` | `PointTable` | Maps operational point metadata to Brick point classes | `BrickPointsSet` |
| `reasoning/spatial.py` | `IfcBundle` | Derives spatial hierarchy and spatial relationships | `SpatialElements`, `RelationSet` |
| `reasoning/connectivity.py` | `IfcBundle` | Extracts physical connectivity from IFC relationships and ports | `ConnectivityGraph` |
| `reasoning/equipment.py` | `ConnectivityGraph`, `BrickEquipmentSet` | Infers equipment-level semantic relationships such as `brick:feeds` | `RelationSet` |
| `linking/equipment_points.py` | `BrickEquipmentSet`, `BrickPointsSet` | Links BMS / IoT points to corresponding equipment | `RelationSet` |
| `linking/spatial.py` | IFC spatial information, equipment, and points | Links equipment and points to spaces | `RelationSet` |
| `serialization/rdf.py` | Semantic entities and relations | Constructs the RDF knowledge graph | `BrickGraph` |
| `validation/shacl.py` | `BrickGraph`, SHACL shapes | Validates semantic consistency and required graph patterns | `ValidationReport` |
| `pipeline.py` | Input paths and configuration | Coordinates the complete processing sequence | `PipelineResult` |

### Expected Outputs

The primary output is a Brick-compatible RDF knowledge graph.

```text
data/output/
├─ building_brick.ttl
├─ building_brick.jsonld
├─ provenance.csv
└─ validation_report.json
```

Intermediate representations may optionally be exported for debugging, research evaluation, and traceability.

```text
data/intermediate/
├─ extracted/
├─ mapped/
└─ relations/
```

Intermediate files are not intended to be mandatory dependencies between modules. Under the target architecture, modules should normally exchange typed Python objects in memory, while intermediate files are generated only when explicitly requested for inspection or reproducibility.

### Design Principle

The target implementation follows a one-directional dependency flow:

```text
Ingestion
   ↓
Mapping
   ↓
Reasoning / Linking
   ↓
Semantic Model
   ↓
Validation
   ↓
Serialization / Export
```

RDF generation should be centralized rather than performed independently within ingestion or mapping modules. This design allows alternative input adapters, such as other CSV formats, database sources, or building-operation platforms, to be introduced without rewriting the downstream semantic mapping and reasoning logic.


## How to run
A preliminary execution entry point is provided.

```text
python run.py
```

## Repository Structure
```bash
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
```

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
- The target data flow and module responsibilities are documented above and remain subject to implementation-level refinement.
- Some implementation decisions are provisional.
- Further refactoring and consolidation are expected.

## Notes
- This repository reflects an intermediate research state.
- Not all components are intended to be complete or directly executable.
