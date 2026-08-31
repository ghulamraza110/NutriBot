from langgraph.graph import StateGraph, END
from models.state import RecipeState
from nodes.chef import chef_node
from nodes.inspector import inspector_node
from utils.routing import route_kitchen

workflow = StateGraph(RecipeState)
workflow.add_node("chef", chef_node)
workflow.add_node("inspector", inspector_node)
workflow.add_edge("chef", "inspector")
workflow.add_conditional_edges(
    "inspector", route_kitchen, {"serve": END, "recook": "chef", "stop": END}
)
workflow.set_entry_point("chef")
app = workflow.compile()

if __name__ == "__main__":
    state = {
        "ingredients": "chicken, rice, onion, tomato",
        "recipe_proposal": "",
        "is_safe": False,
        "critique": "",
        "iteration": 0,
    }
    result = app.invoke(state)

    print("\n--- FINAL RESULT ---")
    print(f"Safe: {result['is_safe']}")
    print(f"Iterations: {result['iteration']}")
    print(f"\nRecipe:\n{result['recipe_proposal']}")
    if result.get("critique"):
        print(f"\nLast critique:\n{result['critique']}")
