# Definition of Use Cases

## Introduction(need to be modified)
The primary purpose of this section is to define the use cases through which the proposed IFC‑to‑Brick mapping method will be applied, thereby demonstrating how interoperability between IFC and Brick can be improved in practical scenarios. In addition, this section provides a structured framework for interoperability by incorporating international and regional standards such as the Building Topology Ontology (BOT), the Building Data Name Standard (bDNS), and the buildingSMART Data Dictionary (bSDD). While these integrated models are expected to serve as a foundation for future digital‑twin applications, the present focus is limited to establishing technical consistency in spatial semantics and operational metadata. With regard to the specific building models to be used in this study, the selection remains pending, as project team member Alex is currently coordinating the acquisition of  building data and associated operational metadata from industry partners.

## 2.2 Selection of buildings/models suitable for use cases

To be suitable, models must integrate Architectural and MEP (Mechanical, Electrical, and Plumbing) disciplines to allow the automated inference of logical relationships, such as equipment-to-zone associations

### Constraints and Assumptions
• Actual Operation: The building must feature an active Building Management System (BMS) or IoT network capable of providing real-time telemetry data.
• Schema Alignment: The model must support spatial hierarchies consistent with BOT to ensure standardized topology.

## 2.3 Required Inputs and Expected Outputs

### Required Inputs

The construction of a functional interoperability framework requires a structured set of heterogeneous data inputs to bridge the gap between static design intent and dynamic building operations. The workflow is designed to transform these inputs into a machine-readable semantic model.

• Architectural IFC (Spatial Foundation): High-fidelity BIM data identifying the building's spatial hierarchy, including sites, floors, and rooms. This project leverages the Building Topology Ontology (BOT) to ensure that these spatial relationships are standardized and consistent across different software platforms.
• MEP IFC (Asset Definition): Detailed layouts of mechanical, electrical, and plumbing systems, including equipment such as VAV boxes, fan coil units (FCUs), and various sensor types(although sensor data is rarely integrated into BIM). Each asset must possess a unique identifier (GlobalId or UniqueID) to maintain bidirectional traceability between the ifc model and the semantic graph.


• Relationship Information (Logical Connectivity): Data defining the functional links between entities. This includes spatial containment (e.g., IfcRelContainedInSpatialStructure mapped to hasLocation) and system-level control logic (e.g., which thermostat regulates which VAV box).

• BMS Metadata (Optional): Operational metadata including point naming conventions, control logic sequences, and time-series identifiers. This data is essential for linking the "static" BIM components to "dynamic" live telemetry streams.

• Standardized Labeling and Interfaces(Optional): Integration of naming and communication standards to ensure cross-system parsability:
    ◦ bDNS (Building Data Name Standard): Used for standardized asset nomenclature and labeling, providing a consistent vocabulary tailored to the Japanese context.
    ◦ UDMI (Universal Device Management Interface): Utilized for the automated generation of telemetry payloads, mapping IFC data (such as object placement and names) directly to cloud-based monitoring structures.

### Expected Outputs
• Brick-compliant RDF Graph: A standardized semantic representation of the building in Turtle (.ttl) or JSON-LD format. 

• Visualized Semantic Network: A graphical representation of the building's digital twin, accessible via tools like BrickStudio. This output allows for human-in-the-loop validation, enabling managers to visually audit and edit nodes or relationships to ensure operational accuracy.

## 2.4 Considering verification steps in representative use case (case study)

### Rule‑Based Validation(to be modified)
Rule‑Based validation provides the first line of assurance by mechanically checking whether both the IFC‑derived data and the generated Brick graph satisfy formal requirements.

#### IDS‑based IFC Compliance Checking
#### SHACL Validation for Brick Graphs

### Human‑in‑the‑Loop Visual Audit
#### Visual Interaction in BrickStudio
The knowledge graph is visually inspected to identify, for example; 

• Unexpected predicates (e.g., brick:feeds linking incompatible classes)
• Duplicate nodes
• Missing relationships that should exist based on domain knowledge

## 2.5 Alternative Plan (added later)