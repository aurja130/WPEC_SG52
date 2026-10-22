#!/usr/bin/env python3
"""Check the DBC reference set in ``DBC/`` for drift.

Usage: ``python3 DBC/check_dbc.py`` (``--root`` overrides the repository root).
Exit 0: no drift. Exit 1: problems listed as ``DBC/<file>:<line>: <message>``.
Exit 2: a DBC file is missing or unreadable.

Files: ``DBC/CONCEPTS.md``, ``CODE.md``, ``DEFINITIONS.md``, ``EXERCISES.md`` and
``TESTS.md``. Each links to the other four with relative Markdown links, and
every relative link or image target exists.

CONCEPTS.md
- Exactly one L1 diagram, headed ``## L1 · SG52 adjustment``. L2 and L3
  diagrams are headed ``### L2 · <title> (`ParentID`)`` and
  ``#### L3 · <title> (`ParentID`)``. Every owned L1 node has exactly one L2
  diagram; an L2 node has at most one L3 diagram; an L3 parent is an L2 node.
- Each diagram has exactly one mermaid block starting ``flowchart LR`` or
  ``flowchart TD``. Allowed lines: node declarations ``ID["label"]`` (also
  ``("…")``, ``{"…"}``, ``(["…"])``, ``[("…")]``, ``{{"…"}}``); edges ``-->``,
  ``-.->``, ``==>``, ``---``, ``-.-`` with optional ``|label|`` and ``&``;
  ``subgraph ID["label"]`` … ``end``; ``classDef``; ``class ID[,ID] status``;
  ``style``, ``linkStyle``, ``direction``; ``%%`` comments.
- Each diagram has exactly one node table ``| Node | Meaning | Terms | Status |``
  with one row per mermaid node; the row's backticked ID is declared in that
  diagram's block.
- Node IDs are CamelCase (``[A-Za-z][A-Za-z0-9]*``) and owned by exactly one
  diagram. Status is ``implemented``, ``partial``, ``planned`` or ``external``
  (a node owned by another diagram, shown for context). Mermaid classes match
  the status: ``class X planned|partial|external``; implemented nodes carry no
  status class.
- Every owned node lists at least one term, and every term is defined in
  DEFINITIONS.md.
- Parent and child statuses agree: an implemented parent has no planned or
  partial child; a planned parent has only planned children; a partial parent
  has at least one implemented/partial and one planned/partial child.
- No exercise numbers ("Exercise 3", "Ex3"): concepts are exercise-independent.

CODE.md
- Tables headed ``| Node | Code | Notes |``, one backticked owned node per row,
  never an L1 node and never a planned node. The Code cell holds backticked
  repository-relative paths, each followed by backticked symbols that occur in
  that file. No line numbers. Every implemented or partial L2 node has a row.

DEFINITIONS.md
- The first column of every table is the term. ``", "`` and ``" / "`` separate
  alternative forms; a trailing ``(…)`` is optional when matching.

EXERCISES.md
- One ``## Exercise <N> · <title>`` section per exercise, with a unique N.
  Every ``Exercise_<N>/`` directory in the repository has a section.
- Each section has lines starting ``**Data:**``, ``**Assumptions:**``,
  ``**Acceptance:**``, ``**Result today:**``, ``**Concepts:**`` (backticked
  owned node IDs) and ``**Comments:**``.

TESTS.md
- Every table has a ``Concepts`` column of backticked owned node IDs.
- Backticked paths (optionally with a ``::`` test suffix) exist, and every test
  file (``Exercise_*/test_*.py`` and files under ``GLLS_code/tests/``) appears
  in a row.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast
from urllib.parse import unquote

DBC_DIR = Path("DBC")
PROJECT_TITLE = "SG52 adjustment"
FILES = ("CONCEPTS.md", "CODE.md", "DEFINITIONS.md", "TESTS.md", "EXERCISES.md")
EXERCISE_HEADING = re.compile(r"^Exercise ([0-9]+) · \S.*$")
EXERCISE_DIRECTORY = re.compile(r"^Exercise_([0-9]+)$")
EXERCISE_FIELDS = (
    "**Data:**",
    "**Assumptions:**",
    "**Acceptance:**",
    "**Result today:**",
    "**Concepts:**",
    "**Comments:**",
)
EXERCISE_NUMBER = re.compile(r"\b(?:Exercise|Ex)\s*_?[0-9]+\b")
STATUSES = {"implemented", "partial", "planned", "external"}
NODE_ID = r"[A-Za-z][A-Za-z0-9]*"
DIAGRAM_HEADING = re.compile(r"^(#{2,4})\s+L([1-3]) · (.+?)\s*$")
ANY_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
NODE_DECLARATION = re.compile(
    r"""
    ([A-Za-z][A-Za-z0-9]*)
    (?:
        \["[^"]*"\]
        | \("[^"]*"\)
        | \{"[^"]*"\}
        | \(\["[^"]*"\]\)
        | \[\("[^"]*"\)\]
        | \{\{"[^"]*"\}\}
    )
    """,
    re.VERBOSE,
)
TABLE_SEPARATOR = re.compile(r":?-{3,}:?")


class Arguments(argparse.Namespace):
    def __init__(self) -> None:
        super().__init__()
        self.root: Path | None = None


@dataclass(frozen=True)
class Problem:
    filename: str
    line: int
    message: str


@dataclass(frozen=True)
class Table:
    line: int
    header: list[str]
    rows: list[tuple[int, list[str]]]


@dataclass(frozen=True)
class Node:
    identifier: str
    status: str
    level: int
    diagram_index: int
    line: int


@dataclass
class Diagram:
    level: int
    title: str
    parent: str | None
    line: int
    start: int
    end: int
    declared: set[str] = field(default_factory=set)
    nodes: dict[str, Node] = field(default_factory=dict)
    classes: dict[str, set[str]] = field(default_factory=dict)


def cells(line: str) -> list[str]:
    value = line.strip().removeprefix("|").removesuffix("|")
    return [cell.strip() for cell in value.split("|")]


def is_table_separator(line: str) -> bool:
    parts = cells(line)
    return bool(parts) and all(TABLE_SEPARATOR.fullmatch(part) for part in parts)


def markdown_tables(lines: list[str]) -> list[Table]:
    tables: list[Table] = []
    index = 0
    while index + 1 < len(lines):
        if "|" not in lines[index] or not is_table_separator(lines[index + 1]):
            index += 1
            continue
        header = cells(lines[index])
        rows: list[tuple[int, list[str]]] = []
        row_index = index + 2
        while row_index < len(lines) and "|" in lines[row_index]:
            rows.append((row_index + 1, cells(lines[row_index])))
            row_index += 1
        tables.append(Table(index + 1, header, rows))
        index = row_index
    return tables


def add_problem(
    problems: list[Problem], filename: str, line: int, message: str
) -> None:
    problems.append(Problem(filename, max(1, line), message))


def term_forms(value: str) -> set[str]:
    without_ticks = value.replace("`", "").strip()
    pieces = re.split(r", | / ", without_ticks)
    forms: set[str] = set()
    for piece in pieces:
        clean = piece.strip()
        if not clean:
            continue
        forms.add(clean.casefold())
        trailing = re.sub(r"\s*\([^()]*\)\s*$", "", clean).strip()
        if trailing != clean:
            forms.add(trailing.casefold())
        if clean.startswith("(") and clean.endswith(")"):
            forms.add(clean[1:-1].strip().casefold())
    return forms


def definitions_terms(lines: list[str]) -> set[str]:
    terms: set[str] = set()
    for table in markdown_tables(lines):
        for _, row in table.rows:
            if row:
                terms.update(term_forms(row[0]))
    return terms


def headings(lines: list[str]) -> list[tuple[int, int, str]]:
    found: list[tuple[int, int, str]] = []
    fence_char: str | None = None
    fence_length = 0
    for index, line in enumerate(lines):
        fence = re.match(r"^\s*(`{3,}|~{3,})", line)
        if fence:
            marker = fence.group(1)
            if fence_char is None:
                fence_char = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_length:
                fence_char = None
            continue
        if fence_char is not None:
            continue
        match = ANY_HEADING.match(line)
        if match:
            found.append((index, len(match.group(1)), match.group(2).strip()))
    return found


def diagram_parent(level: int, title_text: str) -> tuple[str, str | None]:
    if level == 1:
        return title_text.strip(), None
    parent_match = re.fullmatch(r"(.+?)\s+\(`(" + NODE_ID + r")`\)", title_text)
    if not parent_match:
        return title_text.strip(), None
    return parent_match.group(1).strip(), parent_match.group(2)


def parse_mermaid(
    lines: list[str],
    start: int,
    filename: str,
    problems: list[Problem],
) -> tuple[set[str], dict[str, set[str]]]:
    declared: set[str] = set()
    classes: dict[str, set[str]] = {status: set() for status in STATUSES}
    subgraphs: set[str] = set()
    endpoints: list[tuple[str, int]] = []
    body: list[tuple[int, str]] = []
    close = start + 1
    while close < len(lines) and not re.fullmatch(r"\s*```\s*", lines[close]):
        body.append((close + 1, lines[close]))
        close += 1
    if close == len(lines):
        add_problem(problems, filename, start + 1, "unclosed ```mermaid fence")
    if not body or body[0][1].strip() not in {"flowchart LR", "flowchart TD"}:
        add_problem(
            problems,
            filename,
            body[0][0] if body else start + 1,
            "mermaid block must start with 'flowchart LR' or 'flowchart TD'",
        )

    subgraph_depth = 0
    arrows = ("-->", "-.->", "==>", "---", "-.-")
    arrow_pattern = "|".join(re.escape(arrow) for arrow in arrows)
    for line_number, raw in body[1:]:
        text = raw.strip()
        if not text or text.startswith("%%"):
            continue
        if re.match(r"^classDef\b", text):
            continue
        if re.match(r"^style\b|^linkStyle\b|^direction\b", text):
            continue
        subgraph = re.fullmatch(r"subgraph\s+(" + NODE_ID + r")\[\"[^\"]*\"\]", text)
        if subgraph:
            subgraphs.add(subgraph.group(1))
            subgraph_depth += 1
            continue
        if text == "end":
            if subgraph_depth == 0:
                add_problem(
                    problems,
                    filename,
                    line_number,
                    "unmatched mermaid subgraph 'end'",
                )
            else:
                subgraph_depth -= 1
            continue
        declaration = NODE_DECLARATION.fullmatch(text)
        if declaration:
            declared.add(declaration.group(1))
            continue
        class_match = re.fullmatch(
            r"class\s+([A-Za-z][A-Za-z0-9]*(?:\s*,\s*[A-Za-z][A-Za-z0-9]*)*)\s+([A-Za-z][A-Za-z0-9_]*)",
            text,
        )
        if class_match:
            class_name = class_match.group(2)
            identifiers = re.split(r"\s*,\s*", class_match.group(1))
            if class_name in classes:
                classes[class_name].update(identifiers)
            continue

        labelled = re.sub(r"(" + arrow_pattern + r")\|[^|]*\|", r"\1", text)
        tokens: list[str] = []
        position = 0
        token_pattern = re.compile(
            r"\s*(-->|-\.->|==>|---|-\.\-|&|[A-Za-z][A-Za-z0-9]*)"
        )
        token_error = False
        while position < len(labelled):
            match = token_pattern.match(labelled, position)
            if not match:
                token_error = True
                break
            tokens.append(match.group(1))
            position = match.end()
        if "|" in labelled:
            token_error = True
        if not token_error and tokens:
            token_index = 0
            valid = True
            if re.fullmatch(NODE_ID, tokens[0]) is None:
                valid = False
            while valid:
                endpoints.append((tokens[token_index], line_number))
                token_index += 1
                while token_index < len(tokens) and tokens[token_index] == "&":
                    token_index += 1
                    if (
                        token_index >= len(tokens)
                        or re.fullmatch(NODE_ID, tokens[token_index]) is None
                    ):
                        valid = False
                        break
                    endpoints.append((tokens[token_index], line_number))
                    token_index += 1
                if not valid or token_index >= len(tokens):
                    break
                if tokens[token_index] not in arrows:
                    valid = False
                    break
                token_index += 1
                if (
                    token_index >= len(tokens)
                    or re.fullmatch(NODE_ID, tokens[token_index]) is None
                ):
                    valid = False
                    break
            if (
                valid
                and token_index == len(tokens)
                and any(token in arrows for token in tokens)
            ):
                continue
        add_problem(
            problems,
            filename,
            line_number,
            f"unrecognised mermaid line: {text!r}",
        )

    if subgraph_depth:
        add_problem(problems, filename, start + 1, "mermaid subgraph is missing 'end'")
    for endpoint, line_number in endpoints:
        if endpoint not in declared and endpoint not in subgraphs:
            add_problem(
                problems,
                filename,
                line_number,
                f"mermaid edge references undeclared node or subgraph ID {endpoint}",
            )
    for status, identifiers in classes.items():
        for identifier in sorted(identifiers - declared):
            add_problem(
                problems,
                filename,
                start + 1,
                f"mermaid class {status} references undeclared node ID {identifier}",
            )
    return declared, classes


def parse_concepts(
    lines: list[str],
    definition_names: set[str],
    problems: list[Problem],
) -> tuple[list[Diagram], dict[str, Node]]:
    filename = "CONCEPTS.md"
    all_headings = headings(lines)
    diagram_starts: list[tuple[int, int, str, int]] = []
    for index, heading_level, text in all_headings:
        match = DIAGRAM_HEADING.match("#" * heading_level + " " + text)
        if match:
            diagram_starts.append((index, heading_level, text, int(match.group(2))))

    level_one = [item for item in diagram_starts if item[3] == 1]
    if len(level_one) != 1:
        add_problem(
            problems,
            filename,
            level_one[1][0] + 1 if len(level_one) > 1 else 1,
            f"CONCEPTS.md must contain exactly one L1 heading; found {len(level_one)}",
        )

    diagrams: list[Diagram] = []
    for index, (start, heading_level, text, level) in enumerate(diagram_starts):
        _, title_text = text.split(" · ", 1)
        title, parent = diagram_parent(level, title_text)
        line_number = start + 1
        if level == 1 and (heading_level != 2 or title != PROJECT_TITLE):
            add_problem(
                problems,
                filename,
                line_number,
                f"the L1 diagram heading must be exactly '## L1 · {PROJECT_TITLE}'",
            )
        if level in {2, 3} and parent is None:
            add_problem(
                problems,
                filename,
                line_number,
                f"L{level} diagram heading must end with its parent node ID in backticks",
            )
        end = len(lines)
        for next_index, next_level, next_text in all_headings:
            if next_index <= start:
                continue
            is_diagram = bool(DIAGRAM_HEADING.match("#" * next_level + " " + next_text))
            if is_diagram or next_level <= heading_level:
                end = next_index
                break
        diagrams.append(Diagram(level, title, parent, line_number, start, end))

    for diagram_index, diagram in enumerate(diagrams):
        section_lines = lines[diagram.start : diagram.end]
        mermaid_starts = [
            diagram.start + offset
            for offset, line in enumerate(section_lines)
            if re.fullmatch(r"\s*```mermaid\s*", line)
        ]
        if len(mermaid_starts) != 1:
            add_problem(
                problems,
                filename,
                diagram.line,
                f"L{diagram.level} diagram must contain exactly one ```mermaid block; found {len(mermaid_starts)}",
            )
        if mermaid_starts:
            declared, classes = parse_mermaid(
                lines,
                mermaid_starts[0],
                filename,
                problems,
            )
            diagram.declared = declared
            diagram.classes = classes

        section_tables = markdown_tables(section_lines)
        node_tables = [
            table
            for table in section_tables
            if table.header == ["Node", "Meaning", "Terms", "Status"]
        ]
        if len(node_tables) != 1:
            add_problem(
                problems,
                filename,
                diagram.line,
                f"L{diagram.level} diagram must contain exactly one node table headed '| Node | Meaning | Terms | Status |'; found {len(node_tables)}",
            )
        if node_tables:
            table = node_tables[0]
            for row_line, row in table.rows:
                row_line += diagram.start
                if len(row) != 4:
                    add_problem(
                        problems,
                        filename,
                        row_line,
                        "node table row must have Node, Meaning, Terms, and Status cells",
                    )
                    continue
                identifier_match = re.fullmatch(r"`(" + NODE_ID + r")`", row[0])
                if not identifier_match:
                    add_problem(
                        problems,
                        filename,
                        row_line,
                        f"node table ID must be one backticked ID, found {row[0]!r}",
                    )
                    continue
                identifier = identifier_match.group(1)
                status = row[3].strip()
                if status not in STATUSES:
                    add_problem(
                        problems,
                        filename,
                        row_line,
                        f"node {identifier} has invalid status {status!r}; use implemented, partial, planned, or external",
                    )
                if identifier not in diagram.declared:
                    add_problem(
                        problems,
                        filename,
                        row_line,
                        f"node table ID {identifier} is not declared in this diagram's mermaid block",
                    )
                if status != "external" and status in STATUSES:
                    terms = [part.strip() for part in row[2].split(",") if part.strip()]
                    if not terms:
                        add_problem(
                            problems,
                            filename,
                            row_line,
                            f"owned node {identifier} must list at least one term",
                        )
                    for term in terms:
                        if not (term_forms(term) & definition_names):
                            add_problem(
                                problems,
                                filename,
                                row_line,
                                f"node {identifier} uses unknown term {term.replace('`', '')!r} in its Terms cell",
                            )
                diagram.nodes[identifier] = Node(
                    identifier, status, diagram.level, diagram_index, row_line
                )
                actual_classes = {
                    class_status
                    for class_status, identifiers in diagram.classes.items()
                    if identifier in identifiers
                }
                expected_classes: set[str] = (
                    {status} if status in {"planned", "partial", "external"} else set()
                )
                if actual_classes != expected_classes:
                    expected = ", ".join(sorted(expected_classes)) or "no status class"
                    actual = ", ".join(sorted(actual_classes)) or "no status class"
                    add_problem(
                        problems,
                        filename,
                        row_line,
                        f"node {identifier} has status {status!r} but mermaid classes are {actual}; expected {expected}",
                    )
        for identifier in sorted(diagram.declared - set(diagram.nodes)):
            add_problem(
                problems,
                filename,
                diagram.line,
                f"mermaid node ID {identifier} has no row in this diagram's node table",
            )

    owners: dict[str, Node] = {}
    for diagram in diagrams:
        for identifier, node in diagram.nodes.items():
            if node.status == "external" or node.status not in STATUSES:
                continue
            existing = owners.get(identifier)
            if existing is not None and existing.diagram_index != node.diagram_index:
                add_problem(
                    problems,
                    filename,
                    node.line,
                    f"node ID {identifier} is owned by more than one diagram",
                )
            else:
                owners[identifier] = node

    for diagram in diagrams:
        for identifier, node in diagram.nodes.items():
            if node.status != "external":
                continue
            owner = owners.get(identifier)
            if owner is None or owner.diagram_index == node.diagram_index:
                add_problem(
                    problems,
                    filename,
                    node.line,
                    f"external node {identifier} must be owned by a different diagram with a non-external status",
                )

    l1_diagrams = [diagram for diagram in diagrams if diagram.level == 1]
    l1 = l1_diagrams[0] if l1_diagrams else None
    l2_sections: dict[str, list[Diagram]] = {}
    l3_sections: dict[str, list[Diagram]] = {}
    for diagram in diagrams:
        if diagram.level == 2:
            if diagram.parent is not None:
                l2_sections.setdefault(diagram.parent, []).append(diagram)
                parent_node = owners.get(diagram.parent)
                if (
                    parent_node is None
                    or parent_node.level != 1
                    or (
                        l1 is not None
                        and parent_node.diagram_index != diagrams.index(l1)
                    )
                ):
                    add_problem(
                        problems,
                        filename,
                        diagram.line,
                        f"L2 diagram parent {diagram.parent} must be an owned node in the L1 diagram",
                    )
        elif diagram.level == 3 and diagram.parent is not None:
            l3_sections.setdefault(diagram.parent, []).append(diagram)
            parent_node = owners.get(diagram.parent)
            if parent_node is None or parent_node.level != 2:
                add_problem(
                    problems,
                    filename,
                    diagram.line,
                    f"L3 diagram parent {diagram.parent} must be an owned node in an L2 diagram",
                )
    if l1 is not None:
        for identifier, node in l1.nodes.items():
            if node.status != "external" and node.status in STATUSES:
                count = len(l2_sections.get(identifier, []))
                if count != 1:
                    add_problem(
                        problems,
                        filename,
                        node.line,
                        f"L1 node {identifier} must have exactly one L2 section; found {count}",
                    )
    for node in owners.values():
        if node.level == 2:
            count = len(l3_sections.get(node.identifier, []))
            if count > 1:
                add_problem(
                    problems,
                    filename,
                    node.line,
                    f"L2 node {node.identifier} has {count} L3 sections; at most one is allowed",
                )

    for child in diagrams:
        if child.level not in {2, 3} or child.parent is None:
            continue
        parent = owners.get(child.parent)
        if (
            parent is None
            or (child.level == 2 and parent.level != 1)
            or (child.level == 3 and parent.level != 2)
        ):
            continue
        children = [node for node in child.nodes.values() if node.status != "external"]
        statuses = {node.status for node in children}
        if parent.status == "implemented" and statuses & {"planned", "partial"}:
            bad = sorted(
                node.identifier
                for node in children
                if node.status in {"planned", "partial"}
            )
            add_problem(
                problems,
                filename,
                child.line,
                f"implemented parent node {parent.identifier} has planned/partial child node(s): {', '.join(bad)}",
            )
        elif parent.status == "planned" and any(
            node.status != "planned" for node in children
        ):
            bad = sorted(
                f"{node.identifier} ({node.status})"
                for node in children
                if node.status != "planned"
            )
            add_problem(
                problems,
                filename,
                child.line,
                f"planned parent node {parent.identifier} has non-planned child node(s): {', '.join(bad)}",
            )
        elif parent.status == "partial":
            has_done = bool(statuses & {"implemented", "partial"})
            has_open = bool(statuses & {"planned", "partial"})
            if not has_done or not has_open:
                add_problem(
                    problems,
                    filename,
                    child.line,
                    f"partial parent node {parent.identifier} needs at least one implemented/partial and one planned/partial child",
                )
    return diagrams, owners


def node_ids_in_cell(
    cell: str,
    filename: str,
    line: int,
    problems: list[Problem],
    owners: dict[str, Node],
    context: str,
) -> None:
    identifiers = cast(list[str], re.findall(r"`([^`]+)`", cell))
    if not identifiers:
        add_problem(
            problems,
            filename,
            line,
            f"{context} must contain at least one backticked node ID",
        )
        return
    for identifier in identifiers:
        if re.fullmatch(NODE_ID, identifier) is None:
            add_problem(
                problems,
                filename,
                line,
                f"{context} contains invalid node ID {identifier!r}",
            )
        elif identifier not in owners:
            add_problem(
                problems,
                filename,
                line,
                f"{context} references unknown or non-owned node ID {identifier}",
            )


def check_code(
    lines: list[str],
    root: Path,
    owners: dict[str, Node],
    problems: list[Problem],
) -> int:
    filename = "CODE.md"
    code_tables = [
        table
        for table in markdown_tables(lines)
        if table.header == ["Node", "Code", "Notes"]
    ]
    row_count = sum(len(table.rows) for table in code_tables)
    covered: set[str] = set()
    for table in code_tables:
        for line_number, row in table.rows:
            if len(row) != 3:
                add_problem(
                    problems,
                    filename,
                    line_number,
                    "CODE table row must have Node, Code, and Notes cells",
                )
                continue
            node_match = re.fullmatch(r"`(" + NODE_ID + r")`", row[0])
            if not node_match:
                add_problem(
                    problems,
                    filename,
                    line_number,
                    f"CODE Node cell must contain one backticked ID, found {row[0]!r}",
                )
                continue
            identifier = node_match.group(1)
            node = owners.get(identifier)
            if node is None:
                add_problem(
                    problems,
                    filename,
                    line_number,
                    f"CODE row references unknown or non-owned node ID {identifier}",
                )
                continue
            if node.level == 1:
                add_problem(
                    problems,
                    filename,
                    line_number,
                    f"L1 node {identifier} must not have a CODE row",
                )
            if node.status == "planned":
                add_problem(
                    problems,
                    filename,
                    line_number,
                    f"planned node {identifier} has code; flip its status?",
                )
            covered.add(identifier)

            last_path: Path | None = None
            last_path_name: str | None = None
            last_is_directory = False
            tokens = cast(list[str], re.findall(r"`([^`]+)`", row[1]))
            for token in tokens:
                if re.search(r"#L\d+", token) or (
                    "/" in token and re.search(r":\d+$", token)
                ):
                    add_problem(
                        problems,
                        filename,
                        line_number,
                        f"CODE token {token!r} is a line-number reference; use a path or symbol without a line number",
                    )
                    continue
                if "/" in token:
                    path = Path(token)
                    if path.is_absolute():
                        add_problem(
                            problems,
                            filename,
                            line_number,
                            f"CODE path {token!r} must be relative to the repository root",
                        )
                    full_path = root / path
                    last_path = full_path
                    last_path_name = token
                    last_is_directory = token.endswith("/") or full_path.is_dir()
                    if not full_path.exists():
                        add_problem(
                            problems,
                            filename,
                            line_number,
                            f"CODE path {token!r} does not exist relative to the repository root",
                        )
                    continue
                if last_path is None:
                    add_problem(
                        problems,
                        filename,
                        line_number,
                        f"CODE symbol {token!r} appears before any path in the same cell",
                    )
                    continue
                if last_is_directory:
                    add_problem(
                        problems,
                        filename,
                        line_number,
                        f"CODE symbol {token!r} follows directory path {last_path_name!r}",
                    )
                    continue
                symbol = token.removesuffix("()").split("::")[-1]
                try:
                    source = last_path.read_text(encoding="utf-8")
                except (OSError, UnicodeError):
                    continue
                if re.search(r"\b" + re.escape(symbol) + r"\b", source) is None:
                    add_problem(
                        problems,
                        filename,
                        line_number,
                        f"CODE symbol {token!r} is not present in path {last_path_name!r}",
                    )

    for identifier, node in owners.items():
        if (
            node.level == 2
            and node.status in {"implemented", "partial"}
            and identifier not in covered
        ):
            add_problem(
                problems,
                filename,
                node.line,
                f"implemented/partial L2 node {identifier} has no CODE row",
            )
    return row_count


def find_test_files(root: Path) -> list[str]:
    found = [
        path.relative_to(root).as_posix()
        for path in sorted(root.glob("Exercise_*/test_*.py"))
    ]
    tests_directory = root / "GLLS_code" / "tests"
    if tests_directory.is_dir():
        found.extend(
            path.relative_to(root).as_posix()
            for path in sorted(tests_directory.rglob("*"))
            if path.is_file()
        )
    return found


def check_tests(
    lines: list[str], root: Path, owners: dict[str, Node], problems: list[Problem]
) -> int:
    filename = "TESTS.md"
    tables = markdown_tables(lines)
    row_count = sum(len(table.rows) for table in tables)
    cited: set[str] = set()
    for table in tables:
        for line_number, row in table.rows:
            for token in cast(list[str], re.findall(r"`([^`]+)`", " | ".join(row))):
                path = token.split("::", 1)[0]
                if "/" not in path:
                    continue
                cited.add(path)
                if not (root / path).exists():
                    add_problem(
                        problems,
                        filename,
                        line_number,
                        f"TESTS path {path!r} does not exist relative to the repository root",
                    )
    for table in tables:
        if "Concepts" not in table.header:
            add_problem(
                problems,
                filename,
                table.line,
                "TESTS table must have a 'Concepts' column",
            )
            continue
        concepts_index = table.header.index("Concepts")
        for line_number, row in table.rows:
            if concepts_index >= len(row):
                add_problem(
                    problems,
                    filename,
                    line_number,
                    "TESTS row is missing its Concepts cell",
                )
                continue
            node_ids_in_cell(
                row[concepts_index],
                filename,
                line_number,
                problems,
                owners,
                "TESTS Concepts cell",
            )
    for path in find_test_files(root):
        if path not in cited:
            add_problem(
                problems,
                filename,
                1,
                f"test file {path!r} has no TESTS row",
            )
    return row_count


def check_exercises(
    lines: list[str], root: Path, owners: dict[str, Node], problems: list[Problem]
) -> int:
    filename = "EXERCISES.md"
    all_headings = headings(lines)
    sections = [heading for heading in all_headings if heading[1] == 2]
    numbers: dict[int, int] = {}
    for start, _, text in sections:
        heading_match = EXERCISE_HEADING.fullmatch(text)
        if heading_match is None:
            add_problem(
                problems,
                filename,
                start + 1,
                f"EXERCISES section heading must be 'Exercise <N> · <title>', found {text!r}",
            )
        else:
            number = int(heading_match.group(1))
            if number in numbers:
                add_problem(
                    problems,
                    filename,
                    start + 1,
                    f"Exercise {number} already has a section at line {numbers[number]}",
                )
            else:
                numbers[number] = start + 1
        end = len(lines)
        for next_start, next_level, _ in all_headings:
            if next_start > start and next_level <= 2:
                end = next_start
                break
        for field_label in EXERCISE_FIELDS:
            if not any(
                lines[index].startswith(field_label) for index in range(start + 1, end)
            ):
                add_problem(
                    problems,
                    filename,
                    start + 1,
                    f"EXERCISES section must contain a line starting '{field_label}'",
                )
        for index in range(start + 1, end):
            if not lines[index].startswith("**Concepts:**"):
                continue
            content = lines[index].split("**Concepts:**", 1)[1]
            node_ids_in_cell(
                content,
                filename,
                index + 1,
                problems,
                owners,
                "EXERCISES Concepts line",
            )
    for directory in sorted(root.iterdir()):
        directory_match = EXERCISE_DIRECTORY.fullmatch(directory.name)
        if directory.is_dir() and directory_match is not None:
            number = int(directory_match.group(1))
            if number not in numbers:
                add_problem(
                    problems,
                    filename,
                    1,
                    f"directory {directory.name}/ has no 'Exercise {number} · …' section",
                )
    return len(sections)


def check_links(
    documents: dict[str, str],
    root: Path,
    problems: list[Problem],
) -> None:
    for filename, contents in documents.items():
        links: list[tuple[str, int, bool]] = []
        for match in re.finditer(r"(!?)\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)", contents):
            links.append(
                (
                    match.group(2).strip("<>"),
                    contents.count("\n", 0, match.start()) + 1,
                    not match.group(1),
                )
            )
        for match in re.finditer(
            r"<img\b[^>]*\bsrc\s*=\s*(['\"])(.*?)\1",
            contents,
            re.IGNORECASE | re.DOTALL,
        ):
            links.append(
                (
                    match.group(2).strip(),
                    contents.count("\n", 0, match.start()) + 1,
                    False,
                )
            )

        linked_files: set[str] = set()
        document_path = Path(filename)
        for target, line_number, is_markdown_link in links:
            path_without_fragment = target.split("#", 1)[0]
            if re.match(
                r"^(?:https?:|mailto:|//)", path_without_fragment, re.IGNORECASE
            ):
                continue
            decoded = unquote(path_without_fragment)
            if decoded:
                if is_markdown_link:
                    linked_files.add(Path(decoded).name)
                resolved = root / DBC_DIR / decoded
                if not resolved.exists():
                    add_problem(
                        problems,
                        filename,
                        line_number,
                        f"relative link or image target {target!r} does not exist",
                    )
        for other in FILES:
            if other != document_path.name and other not in linked_files:
                add_problem(
                    problems,
                    filename,
                    1,
                    f"missing relative link to {other}",
                )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="check DBC Markdown and code references"
    )
    _ = parser.add_argument(
        "--root",
        type=Path,
        help="repository root (defaults to this script's repository)",
    )
    arguments = parser.parse_args(argv, namespace=Arguments())
    root = (arguments.root or Path(__file__).resolve().parent.parent).resolve()

    paths = {name: root / DBC_DIR / name for name in FILES}
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        for name in missing:
            print(f"check_dbc: missing required file {DBC_DIR / name}", file=sys.stderr)
        return 2

    documents: dict[str, str] = {}
    for name, path in paths.items():
        try:
            documents[name] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            print(f"check_dbc: cannot read {DBC_DIR / name}: {error}", file=sys.stderr)
            return 2

    problems: list[Problem] = []
    concept_lines = documents["CONCEPTS.md"].splitlines()
    code_lines = documents["CODE.md"].splitlines()
    definition_lines = documents["DEFINITIONS.md"].splitlines()
    definition_names = definitions_terms(definition_lines)
    _, owners = parse_concepts(concept_lines, definition_names, problems)

    for line_number, line in enumerate(concept_lines, 1):
        match = EXERCISE_NUMBER.search(line)
        if match:
            add_problem(
                problems,
                "CONCEPTS.md",
                line_number,
                f"exercise number {match.group(0)!r} is not allowed; concepts are exercise-independent",
            )

    code_count = check_code(code_lines, root, owners, problems)
    test_count = check_tests(documents["TESTS.md"].splitlines(), root, owners, problems)
    exercise_count = check_exercises(
        documents["EXERCISES.md"].splitlines(), root, owners, problems
    )
    check_links(documents, root, problems)

    if problems:
        for problem in sorted(
            problems, key=lambda item: (item.filename, item.line, item.message)
        ):
            print(f"{DBC_DIR / problem.filename}:{problem.line}: {problem.message}")
        print(f"check_dbc: {len(problems)} problem(s)")
        return 1

    counts = {
        level: sum(1 for node in owners.values() if node.level == level)
        for level in (1, 2, 3)
    }
    total = sum(counts.values())
    summary = (
        f"check_dbc: ok — {total} nodes (L1 {counts[1]}, L2 {counts[2]}, L3 {counts[3]}), "
        + f"{code_count} code rows, {test_count} test rows, {exercise_count} exercise sections"
    )
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
