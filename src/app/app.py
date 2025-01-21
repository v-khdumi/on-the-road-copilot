import logging
import os
from pathlib import Path
import time
import json
from aiohttp import web
from azure.core.credentials import AzureKeyCredential
from azure.identity import AzureDeveloperCliCredential, DefaultAzureCredential
from dotenv import load_dotenv

from backend.tools import _generate_report_tool, _generate_report_tool_schema, _get_report_fields_tool_schema
from backend.rtmt import RTMiddleTier, Tool

from acs.caller import OutboundCall
from reportstore.cosmosdb import CosmosDBStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voicerag")

async def create_app():
    if not os.environ.get("RUNNING_IN_PRODUCTION"):
        logger.info("Running in development mode, loading from .env file")
        load_dotenv()
    llm_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    llm_deployment = os.environ.get("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME")
    llm_key = os.environ.get("AZURE_OPENAI_API_KEY")

    credential = None

    cosmos: CosmosDBStore = None
    caller: OutboundCall = None
    
    if not llm_key:
        if tenant_id := os.environ.get("AZURE_TENANT_ID"):
            logger.info(
                "Using AzureDeveloperCliCredential with tenant_id %s", tenant_id)
            credential = AzureDeveloperCliCredential(
                tenant_id=tenant_id, process_timeout=60)
        else:
            logger.info("Using DefaultAzureCredential")
            credential = DefaultAzureCredential()
    llm_credential = AzureKeyCredential(llm_key) if llm_key else credential

    if (os.environ.get("COSMOSDB_ACCOUNT_ENDPOINT") is not None and
            os.environ.get("COSMOSDB_DATABASE_NAME") is not None and
            os.environ.get("COSMOSDB_CONTAINER_NAME") is not None):
        
        cosmos = CosmosDBStore(
            os.environ.get("COSMOSDB_ACCOUNT_ENDPOINT"),
            os.environ.get("COSMOSDB_DATABASE_NAME"),
            os.environ.get("COSMOSDB_CONTAINER_NAME"),
        )    

    app = web.Application()

    rtmt = RTMiddleTier(llm_endpoint, llm_deployment, llm_credential)

    if (os.environ.get("ACS_CONNECTION_STRING") is not None and 
        os.environ.get("ACS_SOURCE_NUMBER") is not None):
        
        callback_path = os.environ.get("ACS_CALLBACK_PATH")

        if (os.environ.get("ACS_CALLBACK_PATH") is None):
            callback_path = os.environ.get("CONTAINER_APP_HOSTNAME")

        caller = OutboundCall(
            os.environ.get("ACS_CONNECTION_STRING"),
            os.environ.get("ACS_SOURCE_NUMBER"),
            callback_path
        )
        caller.attach_to_app(app, "/acs")

    if cosmos is not None:
        rtmt.system_message = (
            "Ești un asistent util care menține o conversație cu utilizatorul, punând întrebări conform unui set specific de câmpuri.\n"
            "Utilizatorul este un client al băncii care încearcă să comunice detalii despre nevoile sale financiare.\n"
            "TREBUIE să începi conversația întrebând utilizatorul următoarele întrebări:\n"
            "1. Care este motivul principal pentru care ai contactat banca?\n"
            "După aceea, ar trebui să folosești instrumentul 'get_report_fields' pentru a prelua câmpurile necesare din baza de date pentru întrebări suplimentare.\n"
            "Răspunsul de la instrumentul 'get_report_fields' îți va oferi un set de câmpuri pe care trebuie să le completezi adresând utilizatorului întrebări.\n"
            "După ce ai parcurs toate întrebările din schemă, generează un fișier JSON valid pentru utilizator, apelând funcția 'generate_report',\n "
            "cu schema definită ca fiind detalii despre nevoile și cerințele utilizatorului în relația cu banca.\n "
            "Trebuie să menții o conversație clară și relevantă cu utilizatorul, punând întrebările din script. Utilizatorul îți va oferi răspunsurile la întrebări."
        )
        rtmt.tools["generate_report"] = Tool(
            schema=_generate_report_tool_schema,
            target=lambda args: cosmos.write_report(args),
        )
        rtmt.tools["get_questions"] = Tool(
            schema=_get_report_fields_tool_schema,
            target=lambda args: cosmos.get_report_fields(args),
        )
    else:
        rtmt.system_message = (
            "Ești un asistent util care menține o conversație cu utilizatorul, punând întrebări conform unui script specific.\n"
            "Utilizatorul este un client al băncii care încearcă să comunice detalii despre nevoile sale financiare.\n "
            "TREBUIE să începi conversația întrebând utilizatorul următoarele întrebări:\n"
            "1. Care este motivul principal pentru care ai contactat banca?\n"
            "2. Care sunt serviciile financiare de care ai nevoie în prezent?\n"
            "3. Ce obiective financiare ai dori să atingi cu ajutorul băncii?\n"
            "4. Ai întâmpinat probleme specifice pe care banca ar putea să le rezolve?\n"
            "După ce ai colectat aceste informații, creează un fișier JSON valid pentru utilizator, apelând funcția 'generate_report',\n "
            "cu schema definită ca fiind detalii despre nevoile și cerințele utilizatorului în relația cu banca.\n "
            "Trebuie să menții o conversație clară și relevantă cu utilizatorul, punând întrebările necesare pentru a finaliza procesul."
        )
        rtmt.tools["generate_report"] = Tool(
            target=_generate_report_tool,
            schema=_generate_report_tool_schema
        )
    rtmt.attach_to_app(app, "/realtime")

    # Serve static files and index.html
    current_directory = Path(__file__).parent  # Points to 'app' directory
    static_directory = current_directory / 'static'

    # Ensure static directory exists
    if not static_directory.exists():
        raise FileNotFoundError("Static directory not found at expected path: {}".format(static_directory))

    # Serve index.html at root
    async def index(request):
        return web.FileResponse(static_directory / 'index.html')

    async def call(request):
        body = await request.json()

        if (caller is not None):
            body = await request.json()
            print(body)
            target_number = body['target_number']
            return await caller.call(target_number)
        else:
            return web.Response(text="Outbound calling is not configured")

    async def acs_status(request):

        acs_status = {
            'status' : 'ACS is not configured',
            'outbound_calling_enabled': False,
            'inbound_calling_enabled': False
        }

        if (caller is not None):
            source_number = await caller._get_source_number()
            if (source_number != ''):
                acs_status['status'] = "ACS enabled with number " + source_number    
                acs_status['outbound_calling_enabled'] = True
                acs_status['inbound_calling_enabled'] = False
                acs_status['source_number'] = source_number        
        
        return web.json_response(acs_status)

    async def update_system_message(request):
        data = await request.json()
        new_message = data.get('message')
        if new_message:
            rtmt.system_message = new_message
            return web.json_response({'status': 'success', 'message': 'System message updated'})
        return web.json_response({'status': 'error', 'message': 'Invalid system message'}, status=400)

    app.router.add_get('/', index)
    app.router.add_static('/static/', path=str(static_directory), name='static')
    app.router.add_post('/call', call)
    app.router.add_get('/status', acs_status)
    app.router.add_post('/update_system_message', update_system_message)

    return app

if __name__ == "__main__":
    host = os.environ.get("HOST", "localhost")
    port = int(os.environ.get("PORT", 8760))
    web.run_app(create_app(), host=host, port=port)