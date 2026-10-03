from server import mcp

app = mcp.streamable_http_app(
    host="0.0.0.0"
)
