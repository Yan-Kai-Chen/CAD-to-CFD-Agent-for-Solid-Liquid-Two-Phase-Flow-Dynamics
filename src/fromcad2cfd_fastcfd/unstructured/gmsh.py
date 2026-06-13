"""Small Gmsh v4 ASCII reader for controlled FastFluent mesh inspection."""

from __future__ import annotations

from pathlib import Path
import shlex

from .mesh import MeshElement, Node, SUPPORTED_BOUNDARY_ELEMENT_TYPES, SUPPORTED_VOLUME_ELEMENT_TYPES, UnstructuredMesh


class GmshReadError(ValueError):
    """Raised when a Gmsh file cannot be parsed as the supported ASCII subset."""


def read_gmsh_v4_ascii(path: str | Path) -> UnstructuredMesh:
    mesh_path = Path(path)
    if mesh_path.suffix.lower() != ".msh":
        raise GmshReadError("FastFluent unstructured import currently accepts Gmsh .msh files only.")
    lines = mesh_path.read_text(encoding="utf-8").splitlines()
    sections = _sections(lines)
    if "MeshFormat" not in sections:
        raise GmshReadError("Missing $MeshFormat section.")
    _validate_mesh_format(sections["MeshFormat"])
    physical_names = _parse_physical_names(sections.get("PhysicalNames", []))
    entity_physical_tags = _parse_entities(sections.get("Entities", []))
    nodes = _parse_nodes(sections.get("Nodes", []))
    cells, boundary_elements, warnings = _parse_elements(
        sections.get("Elements", []),
        physical_names=physical_names,
        entity_physical_tags=entity_physical_tags,
    )
    if not nodes:
        raise GmshReadError("No nodes were found in the Gmsh file.")
    if not cells:
        raise GmshReadError("No supported volume/area cells were found in the Gmsh file.")
    return UnstructuredMesh(
        source_path=str(mesh_path),
        mesh_format="gmsh_msh_v4_ascii",
        nodes=nodes,
        cells=cells,
        boundary_elements=boundary_elements,
        physical_names=physical_names,
        entity_physical_tags=entity_physical_tags,
        warnings=warnings,
    )


def _sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line.startswith("$") or line.startswith("$End"):
            index += 1
            continue
        name = line[1:]
        end = f"$End{name}"
        index += 1
        body: list[str] = []
        while index < len(lines) and lines[index].strip() != end:
            stripped = lines[index].strip()
            if stripped:
                body.append(stripped)
            index += 1
        if index >= len(lines):
            raise GmshReadError(f"Missing {end} marker.")
        sections[name] = body
        index += 1
    return sections


def _validate_mesh_format(lines: list[str]) -> None:
    if not lines:
        raise GmshReadError("Empty $MeshFormat section.")
    parts = lines[0].split()
    if len(parts) < 3:
        raise GmshReadError("Invalid $MeshFormat line.")
    version = parts[0]
    file_type = parts[1]
    if not version.startswith("4."):
        raise GmshReadError(f"Unsupported Gmsh version: {version}. Expected v4 ASCII.")
    if file_type != "0":
        raise GmshReadError("Binary Gmsh files are not accepted by this agent-safe importer.")


def _parse_physical_names(lines: list[str]) -> dict[tuple[int, int], str]:
    if not lines:
        return {}
    count = int(lines[0])
    physical_names: dict[tuple[int, int], str] = {}
    for line in lines[1 : count + 1]:
        parts = shlex.split(line)
        if len(parts) < 3:
            raise GmshReadError(f"Invalid physical name line: {line}")
        dim = int(parts[0])
        tag = int(parts[1])
        name = parts[2]
        physical_names[(dim, tag)] = name
    return physical_names


def _parse_entities(lines: list[str]) -> dict[tuple[int, int], tuple[int, ...]]:
    if not lines:
        return {}
    counts = [int(value) for value in lines[0].split()]
    if len(counts) != 4:
        raise GmshReadError("Invalid $Entities header.")
    point_count, curve_count, surface_count, volume_count = counts
    entity_physical_tags: dict[tuple[int, int], tuple[int, ...]] = {}
    cursor = 1
    for _ in range(point_count):
        values = lines[cursor].split()
        tag = int(values[0])
        physical_count = int(values[4]) if len(values) > 4 else 0
        tags = tuple(int(value) for value in values[5 : 5 + physical_count])
        entity_physical_tags[(0, tag)] = tags
        cursor += 1
    for dim, count in ((1, curve_count), (2, surface_count), (3, volume_count)):
        for _ in range(count):
            values = lines[cursor].split()
            tag = int(values[0])
            physical_count_index = 7
            physical_count = int(values[physical_count_index]) if len(values) > physical_count_index else 0
            tags = tuple(int(value) for value in values[physical_count_index + 1 : physical_count_index + 1 + physical_count])
            entity_physical_tags[(dim, tag)] = tags
            cursor += 1
    return entity_physical_tags


def _parse_nodes(lines: list[str]) -> dict[int, Node]:
    if not lines:
        raise GmshReadError("Missing $Nodes section.")
    header = [int(value) for value in lines[0].split()]
    if len(header) != 4:
        raise GmshReadError("Invalid $Nodes header.")
    block_count, node_count = header[0], header[1]
    nodes: dict[int, Node] = {}
    cursor = 1
    for _ in range(block_count):
        block_header = lines[cursor].split()
        if len(block_header) != 4:
            raise GmshReadError("Invalid node block header.")
        nodes_in_block = int(block_header[3])
        cursor += 1
        tags = [int(lines[cursor + offset]) for offset in range(nodes_in_block)]
        cursor += nodes_in_block
        for tag in tags:
            coords = [float(value) for value in lines[cursor].split()]
            if len(coords) != 3:
                raise GmshReadError(f"Invalid coordinate row for node {tag}.")
            nodes[tag] = Node(tag=tag, x=coords[0], y=coords[1], z=coords[2])
            cursor += 1
    if len(nodes) != node_count:
        raise GmshReadError(f"Node count mismatch: expected {node_count}, parsed {len(nodes)}.")
    return nodes


def _parse_elements(
    lines: list[str],
    *,
    physical_names: dict[tuple[int, int], str],
    entity_physical_tags: dict[tuple[int, int], tuple[int, ...]],
) -> tuple[list[MeshElement], list[MeshElement], list[str]]:
    if not lines:
        raise GmshReadError("Missing $Elements section.")
    header = [int(value) for value in lines[0].split()]
    if len(header) != 4:
        raise GmshReadError("Invalid $Elements header.")
    block_count, element_count = header[0], header[1]
    parsed_count = 0
    parsed_elements: list[MeshElement] = []
    warnings: list[str] = []
    cursor = 1
    for _ in range(block_count):
        block_header = lines[cursor].split()
        if len(block_header) != 4:
            raise GmshReadError("Invalid element block header.")
        entity_dim = int(block_header[0])
        entity_tag = int(block_header[1])
        element_type = int(block_header[2])
        elements_in_block = int(block_header[3])
        cursor += 1
        physical_tags = entity_physical_tags.get((entity_dim, entity_tag), ())
        names = tuple(name for tag in physical_tags if (name := physical_names.get((entity_dim, tag))))
        for _element in range(elements_in_block):
            values = [int(value) for value in lines[cursor].split()]
            cursor += 1
            element = MeshElement(
                tag=values[0],
                entity_dim=entity_dim,
                entity_tag=entity_tag,
                element_type=element_type,
                node_tags=tuple(values[1:]),
                physical_tags=physical_tags,
                physical_names=names,
            )
            parsed_count += 1
            parsed_elements.append(element)
            if not (
                (entity_dim in {2, 3} and element_type in SUPPORTED_VOLUME_ELEMENT_TYPES)
                or (entity_dim in {1, 2} and element_type in SUPPORTED_BOUNDARY_ELEMENT_TYPES)
            ):
                warnings.append(
                    f"Skipped unsupported element tag {element.tag} with entity_dim={entity_dim}, element_type={element_type}."
                )
    if parsed_count != element_count:
        raise GmshReadError(f"Element count mismatch: expected {element_count}, parsed {parsed_count}.")
    has_volume_cells = any(element.entity_dim == 3 and element.element_type in SUPPORTED_VOLUME_ELEMENT_TYPES for element in parsed_elements)
    cells: list[MeshElement] = []
    boundary_elements: list[MeshElement] = []
    for element in parsed_elements:
        if element.entity_dim == 3 and element.element_type in SUPPORTED_VOLUME_ELEMENT_TYPES:
            cells.append(element)
        elif element.entity_dim == 2 and element.element_type in {2, 3}:
            if has_volume_cells:
                boundary_elements.append(element)
            else:
                cells.append(element)
        elif element.entity_dim == 1 and element.element_type == 1:
            boundary_elements.append(element)
    return cells, boundary_elements, warnings
