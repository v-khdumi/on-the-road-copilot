import re
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

from backend.rtmt import RTMiddleTier, Tool, ToolResult, ToolResultDirection

async def _generate_report_tool(args: Any) -> ToolResult:
    report = {
        "customer_name": args["customer_name"],
        "demo_product": args["demo_product"],
        "demo_date": args["demo_date"],
        "meeting_feedback": args["meeting_feedback"]
    }
    # Return the result to the client
    return ToolResult(report, ToolResultDirection.TO_CLIENT)

# Define the schema for the 'generate_report' tool
_generate_report_tool_schema = {
    "type": "function",
    "name": "generate_report",
    "description": "Generates a JSON report of the customer demo and product attributes derived from the conversation.",
    "parameters": {
        "type": "object",
        "properties": {
            "customer_name": {
                "type": "string",
                "description": "The name of the customer."
            },
            "demo_product": {
                "type": "string",
                "description": "The product that the demo is needed for."
            },
            "demo_date": {
                "type": "string",
                "description": "The date when the demo is needed."
            },
            "meeting_feedback": {
                "type": "string",
                "description": "Feedback from the meeting."
            }
        },
        "required": ["customer_name", "demo_product", "demo_date", "meeting_feedback"],
        "additionalProperties": False
    }
}

_get_report_fields_tool_schema = {
    "type": "function",
    "name": "get_questions",
    "description": "Search the report database for a set of questions that need to be answered by the user. The knowledge base is in English, translate to and from English if " + \
                   "needed. Results are returned in JSON format with a set of questions that need to be answered by the user.",
    "parameters": {
        "type": "object",
        "properties": {
            "department": {
                "type": "string",
                "description": "The name of the department."
            }
        },
        "required": ["department"],
        "additionalProperties": False
    }
}