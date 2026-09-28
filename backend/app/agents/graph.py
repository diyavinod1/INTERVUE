"""
The LangGraph orchestration graph (PRD Sec. 16).

Because Intervue is a request/response web app (not a long-running
process), "WAIT FOR ANSWER" in the PRD's conceptual diagram is realized as
the natural request boundary: the graph runs from START to a question being
generated, returns, and the HTTP layer persists state and waits for the
next API call. When the candidate answers, a fresh invocation resumes the
SAME graph from its "answer_submitted" entry point using the state
rehydrated from the database. This avoids relying on framework-specific
interrupt/checkpoint machinery that would obscure what's actually happening
(PRD Sec. 48 - no unexplained framework tricks) while still using
LangGraph's StateGraph and conditional edges as the real decision engine.

    START
      |
      v
   route_entry  (conditional on state["phase"])
      |
      +--- "start" -----------------> create_plan -> generate_question -> END
      |
      +--- "answer_submitted" -----> evaluate_answer -> decide_next_action
                                                              |
                                                    (conditional on next_action)
                                                              |
                                        +-------- FINISH_INTERVIEW ---------+
                                        |                                   |
                                        v                                   v
                                 generate_question                  generate_final_report
                                        |                                   |
                                        v                                   v
                                       END                                 END
"""
from langgraph.graph import END, START, StateGraph

from app.agents.nodes.decision import decide_next_action_node, should_finish
from app.agents.nodes.evaluation import evaluate_answer_node
from app.agents.nodes.final_report import generate_final_report_node
from app.agents.nodes.planning import create_plan_node
from app.agents.nodes.question_generation import generate_question_node
from app.agents.state import InterviewState


def _route_entry(state: InterviewState) -> str:
    return "start" if state.get("phase") == "start" else "answer_submitted"


def _route_after_decision(state: InterviewState) -> str:
    return "finish" if should_finish(state) else "continue"


def build_interview_graph():
    graph = StateGraph(InterviewState)

    graph.add_node("create_plan", create_plan_node)
    graph.add_node("evaluate_answer", evaluate_answer_node)
    graph.add_node("decide_next_action", decide_next_action_node)
    graph.add_node("generate_question", generate_question_node)
    graph.add_node("generate_final_report", generate_final_report_node)

    graph.add_conditional_edges(
        START,
        _route_entry,
        {"start": "create_plan", "answer_submitted": "evaluate_answer"},
    )

    graph.add_edge("create_plan", "generate_question")
    graph.add_edge("generate_question", END)

    graph.add_edge("evaluate_answer", "decide_next_action")
    graph.add_conditional_edges(
        "decide_next_action",
        _route_after_decision,
        {"continue": "generate_question", "finish": "generate_final_report"},
    )
    graph.add_edge("generate_final_report", END)

    return graph.compile()


# Compiled once per process - StateGraph.compile() is not cheap and the
# graph structure never changes at runtime.
interview_graph = build_interview_graph()
