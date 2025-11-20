from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from typing import TypedDict, Annotated, List
from operator import add
from tool_agent import tools  # Import tools here

# For in-memory checkpointing (RAM-based, lost on restart)
from langgraph.checkpoint.memory import MemorySaver

# For persistent checkpointing across restarts, uncomment the lines below and run:
# pip install langgraph-checkpoint-sqlite
# from langgraph.checkpoint.sqlite import SqliteSaver
# checkpointer = SqliteSaver.from_conn_string("sr_agent_checkpoints.db")

load_dotenv()
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_with_tools = llm.bind_tools(tools)


class SrState(TypedDict):
    messages: Annotated[List, add]


def tool_node_with_logs(state: SrState):
    """Wraps tool execution to show visible API call status."""
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None

    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return state

    new_messages = []
    for call in last_message.tool_calls:
        tool_name = call["name"]
        tool_args = call.get("args", {})

        print(f"🚀 Calling API tool: {tool_name} with args: {tool_args}")

        tool_instance = next((t for t in tools if t.name == tool_name), None)
        if not tool_instance:
            print(f"❌ Tool not found: {tool_name}")
            new_messages.append(ToolMessage(content=f"Tool '{tool_name}' not found.", tool_call_id=call["id"]))
            continue

        try:
            tool_result = tool_instance.invoke(tool_args)
            print(f"✅ API hit successful! Response: {tool_result}\n")
            new_messages.append(
                ToolMessage(
                    content=str(tool_result),
                    name=tool_name,
                    tool_call_id=call["id"],
                )
            )
        except Exception as e:
            print(f"❌ API call failed for {tool_name}: {e}\n")
            new_messages.append(
                ToolMessage(
                    content=f"Error calling {tool_name}: {e}",
                    name=tool_name,
                    tool_call_id=call["id"],
                )
            )

    return {"messages": new_messages}


def llm_node(state: SrState):
    """LLM thinking step that can trigger tool calls."""
    messages = state.get("messages", [])
    system_prompt = SystemMessage(
        content=(
            "You are an ERP IT Service Request assistant.\n"
            "You have access to tools to get or create Service Requests.\n"
            "If the user asks for SR details, status, summary, or a specific ticket → use the 'get_sr' tool.\n"
            "If the user asks to open a new SR → gather all required fields (ask if missing) and then use the 'create_service_request' tool.\n"
            "Required fields for create: type, application_name, priority_level, requested_completion_date (DD-MM-YYYY), description, created_by.\n"
            "ALWAYS use EXACT argument names from the tool schemas (e.g., 'priority_level' NOT 'pariority_level' or 'parority_level').\n"
            "Never hallucinate field names. Never say you lack access. Always use the tools when needed.\n"
            "After tool results, summarize or answer clearly based on the data."
        )
    )
    ai_response = llm_with_tools.invoke([system_prompt] + messages)
    return {"messages": [ai_response]}


def decide_next_step(state: SrState):
    """Route to tools if tool calls exist, else end."""
    messages = state.get("messages", [])
    if not messages:
        return END
    last_msg = messages[-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    return END


# Build graph
graph = StateGraph(SrState)
graph.add_node("llm", llm_node)
graph.add_node("tools", tool_node_with_logs)

graph.add_edge(START, "llm")
graph.add_conditional_edges("llm", decide_next_step, {"tools": "tools", END: END})
graph.add_edge("tools", "llm")

# Checkpointing (in-memory RAM for now)
checkpointer = MemorySaver()
graph = graph.compile(checkpointer=checkpointer)


if __name__ == "__main__":
    print("🤖 SR Agent is online. Type 'exit' to quit.\n")

    CONFIG = {"configurable": {"thread_id": "sr_conversation_001"}, "recursion_limit": 50}  # Change ID for new sessions

    while True:
        user_input = input("👤 You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("👋 Session ended.")
            break

        print("🧠 Assistant: ", end="", flush=True)
        for chunk in graph.stream(
            {"messages": [HumanMessage(content=user_input)]},
            config=CONFIG,
            stream_mode="updates"
        ):
            if "llm" in chunk:
                msg = chunk["llm"]["messages"][-1]
                if isinstance(msg, AIMessage) and not msg.tool_calls and msg.content:
                    print(msg.content, end="", flush=True)

        print("\n")