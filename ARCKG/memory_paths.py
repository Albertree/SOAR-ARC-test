"""
Path helpers — compute semantic_memory file paths from node IDs and comparison pairs.

Node ID format: T{hex}.P{p}.G{g}.O{o}.X{x}  (only as deep as needed)
  e.g.) "T0a1b2c3.P0"          -> PAIR node
        "T0a1b2c3.P0.G0"       -> GRID node
        "T0a1b2c3.P0.G0.O2"    -> OBJECT node
        "T0a1b2c3.P0.G0.O2.X5" -> PIXEL node (under Object)

Folder structure: N_{part}/ hierarchy
  semantic_memory_root/N_T{hex}/N_P{p}/N_G{g}/N_O{o}/N_X{x}/
Property file: E_{last_part}.json
  e.g.) N_G0/E_G0.json
"""


def node_id_to_folder_path(node_id: str, semantic_memory_root: str) -> str:
    """
    Node ID -> absolute path to the node folder (with N_ prefix).
    Does not actually create files — path computation only.
    e.g.) "T0a.P0.G0", "semantic_memory" -> "semantic_memory/N_T0a/N_P0/N_G0/"
    """
    root = semantic_memory_root.rstrip("/") + "/"
    parts = node_id.split(".")
    folder = root
    for part in parts:
        folder += f"N_{part}/"
    return folder


def id_to_json_path(node_id: str, semantic_memory_root: str) -> str:
    """
    Node ID -> property JSON file path (E_{last_part}.json).
    Does not actually create files — path computation only.
    e.g.) "T0a.P0.G0" -> "semantic_memory/N_T0a/N_P0/N_G0/E_G0.json"
    """
    folder = node_id_to_folder_path(node_id, semantic_memory_root)
    last_part = node_id.split(".")[-1]
    return folder + f"E_{last_part}.json"


def _lca_node_id(id_a: str, id_b: str):
    """Return the LCA (Lowest Common Ancestor) node ID of two node IDs."""
    parts_a = id_a.split(".")
    parts_b = id_b.split(".")
    if parts_a[0] != parts_b[0]:
        return None
    common = []
    for a, b in zip(parts_a, parts_b):
        if a == b:
            common.append(a)
        else:
            break
    return ".".join(common) if common else None


def _short_name(node_id: str, lca_id: str) -> str:
    """Return a short name by concatenating path segments after the LCA.
    e.g.) LCA="T0a.P0", node_id="T0a.P0.G0.O2" -> "G0O2"
    """
    lca_prefix = lca_id + "."
    if node_id.startswith(lca_prefix):
        suffix = node_id[len(lca_prefix):]
        return suffix.replace(".", "")
    # If the node is the same as the LCA, return only the last segment
    return node_id.split(".")[-1]


def id_pair_to_comparison_path(id_a: str, id_b: str,
                                semantic_memory_root: str) -> str:
    """
    Return the comparison edge file path from two node IDs.
    - 1st-order comparison (node IDs): E_{short_a}-{short_b}.json under the LCA folder
    - Higher-order comparison (id already in 'E_...' format): create E_(E_...)-(E_...).json at root
    Only computes the path; does not actually create the file.
    """
    # Higher-order comparison: format wrapping two edge IDs in parentheses
    if id_a.startswith("E_") and id_b.startswith("E_"):
        edge_name = f"E_({id_a})-({id_b}).json"
        root = semantic_memory_root.rstrip("/") + "/"
        return root + edge_name

    lca_id = _lca_node_id(id_a, id_b)
    if lca_id is None:
        raise ValueError(f"No LCA found for '{id_a}' and '{id_b}' — different task roots")

    short_a = _short_name(id_a, lca_id)
    short_b = _short_name(id_b, lca_id)
    edge_name = f"E_{short_a}-{short_b}.json"
    lca_folder = node_id_to_folder_path(lca_id, semantic_memory_root)
    return lca_folder + edge_name
