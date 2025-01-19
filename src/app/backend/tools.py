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

async def _fetch_conversation_history_tool(args: Any) -> ToolResult:
    # Placeholder for the actual implementation to fetch conversation history
    conversation_history = [
        {
            "call_connection_id": "12345",
            "event_type": "CallConnected",
            "timestamp": "2023-09-01T12:00:00Z"
        },
        {
            "call_connection_id": "67890",
            "event_type": "CallDisconnected",
            "timestamp": "2023-09-01T12:30:00Z"
        }
    ]
    return ToolResult(conversation_history, ToolResultDirection.TO_CLIENT)

_fetch_conversation_history_tool_schema = {
    "type": "function",
    "name": "fetch_conversation_history",
    "description": "Fetches the conversation history for both browser and phone interactions.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False
    }
}

async def _fetch_questionnaire_and_answers_tool(args: Any) -> ToolResult:
    # Placeholder for the actual implementation to fetch questionnaire and answers
    questionnaire_and_answers = {
        "questionnaire": [
            {
                "question": "What is your department name?",
                "answer": "Sales"
            },
            {
                "question": "How did your demo meeting with the customer go?",
                "answer": "It went well."
            }
        ]
    }
    return ToolResult(questionnaire_and_answers, ToolResultDirection.TO_CLIENT)

_fetch_questionnaire_and_answers_tool_schema = {
    "type": "function",
    "name": "fetch_questionnaire_and_answers",
    "description": "Fetches the questionnaire and answers from the get_report_fields tool.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False
    }
}
