import asyncio
from services.agent.tools.tools_manager import handle_define_syllabus, handle_evaluate_activity, handle_filter_oers, handle_generate_activity, handle_generate_material, handle_refine, handle_get_oers_collections, handle_plan_course, handle_plan_lesson, define_syllabus_tool, plan_course_tool, plan_lesson_tool, generate_material_tool, generate_activity_tool, evaluate_activity_tool, refine_tool, get_oers_collections_tool, filter_oers_tool
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from services.agent.utils.common_enums import EducationLevel, TextStyle, LearningOutcome, TypeOfActivity, TypeOfAssessment, ActionType, sanitize_enums

# Create server instance
server = Server("fastapi-mcp-server")

tools = [
        define_syllabus_tool,
        plan_course_tool,
        plan_lesson_tool,
        generate_material_tool,
        generate_activity_tool,
        evaluate_activity_tool,
        refine_tool,
        get_oers_collections_tool,
        filter_oers_tool        
    ]


def get_tool_overviews()-> list[dict]:
    return [{"name": t.name, "description": t.description} for t in tools]

def format_tool_overviews(tools: list[dict]) -> str:
    return "\n".join([f"- {tool['name']}: {tool['description']}" for tool in tools])

def format_full_tools(tools: list[Tool]) -> str:
    def format_schema(properties: dict, required: list, indent: int = 2) -> str:
        lines = []
        for key, prop in properties.items():
            line = " " * indent + f"- `{key}` ({prop.get('type', 'unknown')})"
            if 'enum' in prop:
                enum_vals = ", ".join(prop['enum'])
                line += f" - Enum: [{enum_vals}]"
            if key not in required:
                line += " *(optional)*"
            desc = prop.get("description", "")
            if desc:
                line += f": {desc}"
            lines.append(line)

            # handle nested object
            if prop.get("type") == "object" and "properties" in prop:
                nested = format_schema(prop["properties"], prop.get("required", []), indent + 4)
                lines.append(nested)
            elif prop.get("type") == "array" and "items" in prop and isinstance(prop["items"], dict) and prop["items"].get("type") == "object":
                lines.append(" " * (indent + 2) + "Each item in the list is an object with:")
                nested = format_schema(prop["items"]["properties"], prop["items"].get("required", []), indent + 6)
                lines.append(nested)
        return "\n".join(lines)

    formatted_tools = []
    for tool in tools:
        header = f"### Tool: `{tool.name}`\n**Description:** {tool.description}\n**Parameters:**"
        param_block = format_schema(
            tool.inputSchema.get("properties", {}),
            tool.inputSchema.get("required", [])
        )
        formatted_tools.append(f"{header}\n{param_block}\n")

    return "\n".join(formatted_tools)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Define the tools available to LLMs"""
    return tools

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls from LLMs"""
    #if there are some enums, match the arg with the key of the enum and replace with the value
    sanitize_enums(arguments, {"education_level": EducationLevel, "text_style": TextStyle, "learning_outcome": LearningOutcome, "type": TypeOfActivity, "assessment": TypeOfAssessment, "action_type": ActionType})
        
    if name == "define_syllabus":
        return await handle_define_syllabus(arguments)
    elif name == "plan_course":
        return await handle_plan_course(arguments)
    elif name == "plan_lesson":
        return await handle_plan_lesson(arguments)
    elif name == "generate_material":
        return await handle_generate_material(arguments)
    elif name == "generate_activity":
        return await handle_generate_activity(arguments)
    elif name == "evaluate_activity":
        return await handle_evaluate_activity(arguments)
    elif name == "refine":
        return await handle_refine(arguments)
    elif name == "get_oers_collections":
        return await handle_get_oers_collections(arguments)
    elif name == "filter_oers":
        return await handle_filter_oers(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")

async def run_mcp_server():
    """Run the MCP server (used in main.py)"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(run_mcp_server())