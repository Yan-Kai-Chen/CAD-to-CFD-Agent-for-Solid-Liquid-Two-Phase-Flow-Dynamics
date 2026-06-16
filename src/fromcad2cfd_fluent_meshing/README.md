# Fluent Meshing Module

The current module implements the first bounded handoff step before automated
Fluent Meshing work: a preflight gate that reads FastCFD/FastFluent pilot
evidence and decides whether Fluent Meshing preparation should proceed.

The public command writes evidence and planning reports. Future local adapters
can use the same decision contract to launch Fluent Meshing, import geometry,
generate meshes, check mesh quality, and write private case/data files inside a
configured local workspace.
