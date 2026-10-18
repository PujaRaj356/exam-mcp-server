
import hashlib
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI()

EMAIL = "24f2005849@ds.study.iitm.ac.in"
PROTOCOL_VERSION = "2025-03-26"


def rpc_result(request_id, result):
    return JSONResponse({
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    })


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"error": "Invalid JSON"}, status_code=400
        )

    method = body.get("method")
    request_id = body.get("id")
    params = body.get("params") or {}

    # MCP initialization handshake
    if method == "initialize":
        return rpc_result(request_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "exam-challenge-server",
                "version": "1.0.0",
            },
        })

    # Notifications do not require a JSON-RPC response
    if method == "notifications/initialized":
        return Response(status_code=202)

    # Advertise exactly one tool
    if method == "tools/list":
        return rpc_result(request_id, {
            "tools": [{
                "name": "solve_challenge",
                "description": (
                    "Compute the challenge hash using the "
                    "X-Exam-Challenge HTTP request header."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            }]
        })

    # Execute the tool using this call's HTTP headers
    if method == "tools/call":
        tool_name = params.get("name")

        if tool_name != "solve_challenge":
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": "Unknown tool",
                },
            })

        challenge = request.headers.get("X-Exam-Challenge")
        if challenge is None:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": "Missing X-Exam-Challenge header",
                },
            })

        normalized_email = EMAIL.strip().lower()
        digest = hashlib.sha256(
            f"{challenge}:{normalized_email}".encode("utf-8")
        ).hexdigest()[:16]

        return rpc_result(request_id, {
            "content": [{
                "type": "text",
                "text": digest,
            }],
            "isError": False,
        })

    if method and method.startswith("notifications/"):
        return Response(status_code=202)

    return JSONResponse({
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32601,
            "message": "Method not found",
        },
    })
