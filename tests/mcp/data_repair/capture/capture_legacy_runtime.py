"""Capture the hash-pinned pre-report validation tool using real FastMCP Clients."""
import asyncio
import hashlib
import json
import platform
import sys
import types
from importlib.metadata import version
from pathlib import Path

import fastmcp

from dartwork_mpl.mcp.artifacts import configure_store, register_artifacts
from dartwork_mpl.mcp.prompts import register_prompts
from dartwork_mpl.mcp.resources import register_resources

REPO = Path(sys.argv[1])
OUT = Path(__file__).parent
DEST = Path(sys.argv[2])
SOURCE = OUT / 'legacy-tools.py'
SOURCE_SHA = '897292d9211069fd42272f125db0b16f898efc3a901843a190fc0a8fa1ad171c'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
fixture_path = REPO / 'tests/mcp/data_repair/fixtures/legacy_calls.json'
fixture = json.loads(fixture_path.read_text())
requests_bytes = json.dumps(fixture['requests'], ensure_ascii=False, sort_keys=True).encode()
assets_source = OUT / 'legacy-assets.py'
assets_module = types.ModuleType('dartwork_mpl.mcp._assets')
assets_module.__package__ = 'dartwork_mpl.mcp'
assets_module.__file__ = str(assets_source)
sys.modules[assets_module.__name__] = assets_module
exec(compile(assets_source.read_bytes(), str(assets_source), 'exec'), assets_module.__dict__)
module = types.ModuleType('dartwork_mpl.mcp._security_legacy_tools')
module.__package__ = 'dartwork_mpl.mcp'
module.__file__ = str(SOURCE)
sys.modules[module.__name__] = module
exec(compile(SOURCE.read_bytes(), str(SOURCE), 'exec'), module.__dict__)
server = fastmcp.FastMCP('dartwork-mpl-legacy-security-capture')
register_resources(server)
module.register_tools(server)
register_prompts(server)
import tempfile; _STORE = tempfile.mkdtemp(prefix='dmpl-legacy-store-'); register_artifacts(server, configure_store(_STORE))
# The historical server had the two artifact tools but no later input-delete
# tool. Reconstruct only that additive registration difference; no old tool
# source or request is edited. This uses the framework's public removal API.
server.remove_tool('delete_plot_inputs')

async def capture():
    """Read discovery and every original request through the protocol boundary."""
    async with fastmcp.Client(server) as client:
        tools = await client.list_tools()
        result = {
            'baseline_sha': '226cddc5170ec21c514983264384ec1c65258ba3',
            'tools_sha256': SOURCE_SHA,
            'python': platform.python_version(),
            'fastmcp': fastmcp.__version__,
            'pydantic': version('pydantic'),
            'mcp': version('mcp'),
            'validate_schema': next(tool.model_dump(mode='json') for tool in tools if tool.name == 'validate_plot_data'),
            'discovery': {
                'tool_names': [tool.name for tool in tools],
                'resource_uris': [str(item.uri) for item in await client.list_resources()],
                'resource_template_uris': [item.uriTemplate for item in await client.list_resource_templates()],
                'prompt_names': [item.name for item in await client.list_prompts()],
            },
            'calls': [],
            'capture_provenance': {
                'source_url': 'https://api.github.com/repos/dartworklabs/dartwork-mpl/contents/src/dartwork_mpl/mcp/tools.py?ref=226cddc5170ec21c514983264384ec1c65258ba3',
                'requests_sha256': hashlib.sha256(requests_bytes).hexdigest(),
                'legacy_assets_sha256': hashlib.sha256(assets_source.read_bytes()).hexdigest(),
                'registrations': 'Exact historical tools.py; current resource/prompt/artifact registrations with later delete_plot_inputs removed through public FastMCP API; no resource payloads/artifact tools invoked.',
                'capture_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            },
        }
        for request in fixture['requests']:
            reply = await client.call_tool('validate_plot_data', request['arguments'], raise_on_error=False)
            result['calls'].append({'id': request['id'], 'response': {
                'raw_text': [item.text for item in reply.content if item.type == 'text'],
                'content': [item.model_dump(mode='json') for item in reply.content],
                'structured_content': reply.structured_content,
                'is_error': reply.is_error,
                'data': reply.data,
            }})
        return result

result = asyncio.run(capture())
original = fixture['runtimes']['3.4.2']
comparison = {field: result[field] == original[field] for field in ('calls','validate_schema','discovery')}
DEST.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
pass
print(json.dumps({'runtime':fastmcp.__version__, 'mcp':version('mcp'), 'calls':len(result['calls']), 'comparison_with_existing_342':comparison}, indent=2))
import shutil; shutil.rmtree(_STORE)
