from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


class SmartCompositionGraphState(TypedDict, total=False):
    run: dict[str, Any]


SmartCompositionGraphNode = Callable[
    [SmartCompositionGraphState],
    SmartCompositionGraphState,
]


@dataclass(frozen=True)
class SmartCompositionGraphNodes:
    prepare: SmartCompositionGraphNode
    retrieve_materials: SmartCompositionGraphNode
    confirm_materials: SmartCompositionGraphNode
    generate_composition: SmartCompositionGraphNode
    confirm_composition: SmartCompositionGraphNode
    save_initial_draft: SmartCompositionGraphNode
    diagnose: SmartCompositionGraphNode
    confirm_rewrite: SmartCompositionGraphNode
    save_final_draft: SmartCompositionGraphNode


def build_smart_composition_graph(nodes: SmartCompositionGraphNodes):
    graph = StateGraph(SmartCompositionGraphState)
    graph.add_node("prepare", nodes.prepare)
    graph.add_node("retrieve_materials", nodes.retrieve_materials)
    graph.add_node("confirm_materials", nodes.confirm_materials)
    graph.add_node("generate_composition", nodes.generate_composition)
    graph.add_node("confirm_composition", nodes.confirm_composition)
    graph.add_node("save_initial_draft", nodes.save_initial_draft)
    graph.add_node("diagnose", nodes.diagnose)
    graph.add_node("confirm_rewrite", nodes.confirm_rewrite)
    graph.add_node("save_final_draft", nodes.save_final_draft)

    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "retrieve_materials")
    graph.add_edge("retrieve_materials", "confirm_materials")
    graph.add_edge("confirm_materials", "generate_composition")
    graph.add_edge("generate_composition", "confirm_composition")
    graph.add_edge("confirm_composition", "save_initial_draft")
    graph.add_edge("save_initial_draft", "diagnose")
    graph.add_edge("diagnose", "confirm_rewrite")
    graph.add_edge("confirm_rewrite", "save_final_draft")
    graph.add_edge("save_final_draft", END)
    return graph
