# Survey of Existing Tools for IFC to Brick Conversion

## Introduction
The integration of heterogeneous data sources such as Building Information Modeling (BIM), Building Management Systems (BMS), and IoT sensors is essential for creating functional digital twins. To overcome the "information silos" caused by manual and time-consuming data mapping, several tools have been developed to automate the conversion of BIM/IFC data into the Brick schema, a standardized semantic metadata environment.
The primary purpose of this survey is to identify and compare tools that facilitate data interoperability between IFC data and Brick schema representing Building Management Systems (BMS), and IoT networks. 


## 1.1 Survey of existing tools
This section provides an overview of the major software platforms or API functionalities available for handling IFC models and the Brick ontology.The goal is to summarize the technical foundations required for reading, writing, converting, visualizing, and applying semantic reasoning to building information. The survey focuses on key aspects essential for IFC‑to‑Brick workflows, namely the API foundations needed to implement IFC‑to‑Brick converters, and the schema versions supported by each tool. Tools designed specifically for IFC‑to‑Brick conversion are also examined within the same framework.

### Overview of IFC/Brick Handling Tools
• IfcOpenShell
IfcOpenShell is an open‑source IFC toolkit providing full parsing support for IFC2X3, IFC4, and IFC4X3, and it can read and write IFC‑SPF, IFCJSON, IFCXML, IFCHDF5, and IFCSQL formats. It offers both C++ and Python APIs, robust geometry processing, an IFC authoring API, and an ecosystem of tools such as IfcConvert and Bonsai.

• IfcConvert
IfcConvert is a command‑line utility included in the IfcOpenShell ecosystem. It converts IFC files into multiple geometry formats, including OBJ and others, and supports the same IFC schemas as IfcOpenShell, leveraging its geometry engine.
It is widely used for model interoperability workflows where IFC needs to be translated into mesh‑based formats.

• xBIM Toolkit
xBIM Toolkit is a .NET‑based open‑source framework for reading, writing, creating, and analyzing IFC models. It provides geometry engines, model checking tools, visualization components, and support for multiple IFC schema versions.

• IFC Toolbox(need to be modified)
IFC Toolbox generally refers to lightweight IFC parsers or utility toolsets enabling model reading, schema navigation, and property extraction.

• BlenderBIM
BlenderBIM is built on top of IfcOpenShell, providing a graphical IFC authoring and editing environment inside Blender. It allows IFC model inspection, editing, drawing generation, and semantic annotation. The project enables linking IFC elements with Brick metadata, and through Bonsai (the new Blender IFC authoring platform), it integrates natively with IfcOpenShell's APIs. 

• Brick Studio(need to be modified)
BrickStudio is a web-based application designed to parse and generate visual representations of RDF resources, supporting formats such as Turtle, TriG, N-Triples, N-Quads, and Notation3 (N3). It provides an interactive interface for editing graphs, allowing users to create, update, or delete nodes and links directly on the canvas. Users can search for specific nodes by identifier or type, and once the model is refined, the modified file can be downloaded as a Turtle document. The tool also includes an analysis export feature that provides a JSON summary of unique subjects, predicates, and triples within the document. To manage complex graphs, it offers configuration settings to exclude specific predicates (like "type") or instances, which helps simplify the visual representation and improves performance.


### Overview of IFC‑to‑Brick Conversion Tools

• BIM-to-BRICK: A Revit-based plugin utilizing Dynamo and Python for automated conversion and bidirectional linking.

This tool is an add-in for Autodesk Revit that uses the Dynamo visual programming environment and the CPython engine to automate the creation of Brick RDF graphs. It eliminates manual mapping by programmatically extracting spatial and system data, such as BMS points and HVAC equipment, and achieves high efficiency by converting hundreds of instances in seconds. A key feature is its bidirectional linking, which preserves unique Revit element IDs within the Brick model, allowing users to trace data back to the original BIM source.

Vittori, F., Tan, C. F., Pisello, A. L., Chong, A., Piselli, C., & Miller, C. (2025). BIM-to-BRICK: Using graph modeling for IoT/BMS and spatial semantic data interoperability within digital data models of buildings.Energy and Buildings, 348, 116368.https://doi.org/10.1016/j.enbuild.2025.116368


• brick-ifc-convert (gtfierro): A Python-based script for converting IFC structures into Brick Turtle files.

This open-source script utilizes the IfcOpenShell library to parse IFC files and translate them into the Turtle (.ttl) format. It specifically maps IFC architectural entities to Brick classes, such as converting IfcBuildingStorey to brick:Floor and IfcSpace to brick:Room. By leveraging IfcRelAggregates, the tool ensures that the spatial relationships and hierarchies of the building are accurately preserved during the semantic conversion process.

https://github.com/gtfierro/brick-ifc-convert


• IFC-to-Brick (ucl-sbde): A repository containing mapping definitions, including specific mappings for IFC4.

This repository serves as a framework for defining the logic and rules for mapping Industry Foundation Classes (IFC) to the Brick schema. It includes specific configuration files for IFC4, such as mapping_IFC4.json, which provide standardized definitions for identifying one-to-one correspondences between IFC entities and their Brick equivalents, ensuring consistency across different versions of the IFC standard.

https://github.com/ucl-sbde/IFC-to-Brick


## 1.2 Comparison of existing tools and verification of IFC version compatibility

| Tool / Library | Supported IFC Versions | Supported Brick Versions | Input Formats | Output Formats | Implementation / Dependency | Key Features |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| IfcOpenShell | IFC2X3, IFC4, IFC4X3 | N/A | IFC-SPF, IFCJSON, IFCXML, IFCHDF5, IFCSQL | Same formats | C++, Python | ---- |
| BlenderBIM | IFC2X3 IFC4 IFC4X3 | N/A | IFC | IFC, Semantic Metadata | Blender, IfcOpenshell | GUI Authoring. Enables graphical IFC editing and semantic annotation to link physical elements with Brick metadata. |
| Brick Studio | - | v1.0.1, v1.0.2  | TTL, TriG, N-Triples, N3, N-Quads | Modified TTL, JSON Analysis | Web-based (Static Site) | Visual Authoring. Search, edit nodes/links, and export graph analysis. |
| brick-ifc-convert (gtfierro)| N/A | N/A | IFC | RDF (Turtle) | Python / IfcOpenShell | Script-based. Maps IfcSpace, IfcZone, etc., to Brick classes. |
| IFC-to-Brick (dimavrok) | IFC4, IFC2x3, IFC4.3 | v1.0.1, v1.0.2 | IFC | RDF (Turtle) | JSON Mapping Definitions | Mapping-focused. Includes mapping_IFC4.json for specific version support.  |
| BIM-to-BRICK | IFC2x3 | N/A | Revit (.rvt), External CSV/IoT | RDF (Turtle), Brick Graph | Revit / Dynamo / CPython | Fully Automated. Bidirectional linking using Unique IDs.   |



## Identified Limitations in Current IFC-to-Brick Conversion Approiaches

Current methodologies for IFC-to-Brick conversion face several critical bottlenecks that hinder seamless data interoperability. A primary limitation is platform dependency, as sophisticated tools such as BIM-to-BRICK are currently restricted to proprietary authoring environments like Autodesk Revit. Furthermore, significant manual intervention is still required to map inconsistent BMS point labels and establish cross-linking tables for disparate sensor data. Most crucially, there is a profound discrepancy in information granularity between the two schemas. While IFC is primarily designed to describe the physical geometry and static structural aspects of a building, Brick requires a much higher level of operational detail to represent sensors and monitoring points. This mismatch makes simple automated translation difficult, as many IFC elements lack the specific semantic depth required for functional Brick modeling. Finally, the inherent structural looseness of RDF-based models necessitates formal validation checks and human-in-the-loop auditing to ensure data consistency and accuracy.

## Implications for This Project

The identified limitations directly inform the strategic goals and technical direction of this project. To overcome proprietary constraints, a key objective is the development of a vendor-neutral, IFC-based conversion pipeline that operates independently of specific BIM authoring software. This project will prioritize the following strategic implementations:
• Integration of BOT (Building Topology Ontology): The project will leverage BOT to facilitate the standardization of building entities and spatial relationships, as it can be easily integrated with the Brick schema to promote consistency across domains.

• Adoption of bDNS (Building Data Name Standard): To enhance the semantic depth of the models, the project aims to use bDNS as a foundation for expanding vocabularies and establishing standardized naming conventions specifically tailored for the Japanese context.

• Standardization via bsDD and IDS: We will utilize the buildingSMART Data Dictionary (bsDD) for multilingual support and Information Delivery Specifications (IDS) to define and enforce robust data rules during the conversion process.

• Human-in-the-Loop Validation: Tools such as BrickStudio will be employed to provide a visual environment for verification, allowing users to manually audit and edit the generated knowledge graphs to ensure they meet operational requirements.

• Bidirectional Traceability: By establishing bidirectional links that preserve unique identifiers (such as Revit IDs) within the Brick model, the project ensures that digital twins remain dynamic, traceable, and accessible for both designers and facility managers.

• Variation of Version: To address schema heterogeneity and ensure robustness of the proposed IFC‑to‑Brick conversion pipeline, the project will explicitly incorporate multi‑version support as a core component of its technical strategy. While the initial implementation will target the latest IFC release, IFC4.3, together with the current stable release of the Brick schema(v1.4.0), subsequent development will extend the conversion framework to accommodate multiple IFC versions including IFC2X3 and IFC4, as well as successive Brick versions. This version‑aware methodology enables cross‑project comparability, backward compatibility, and reproducibility, which are essential for scalable deployment across heterogeneous building