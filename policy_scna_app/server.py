from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any

from policy_scna_app.health_customer_arithmetic import ask_health_question_live_with_arithmetic
from policy_scna_app.health_customer_v0 import (
    HealthConversationContext,
    HealthCustomerPathError,
)

HOST = "127.0.0.1"
PORT = 8765

_PAGE = """<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>PolicyScna Health Customer v0</title>
<style>
body{font-family:system-ui,-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif;max-width:760px;margin:48px auto;padding:0 20px;line-height:1.5}
h1{font-size:28px;margin-bottom:8px}.muted{color:#666;margin-bottom:28px}
textarea{width:100%;min-height:92px;padding:12px;font:inherit;box-sizing:border-box}button{margin-top:10px;padding:10px 18px;font:inherit;cursor:pointer}
.answer{white-space:pre-wrap;border:1px solid #ddd;border-radius:8px;padding:18px;margin-top:24px;min-height:80px}.error{color:#8a1c1c}
details{margin-top:16px;color:#555}code{font-size:12px;white-space:pre-wrap}
</style>
</head>
<body>
<h1>PolicyScna</h1>
<div class=\"muted\">Health Customer Intelligence v0 — local product slice</div>
<textarea id=\"q\" placeholder=\"Ask a Health insurance question...\"></textarea>
<br><button id=\"ask\">Ask</button>
<div id=\"answer\" class=\"answer\">Your answer will appear here.</div>
<details><summary>Diagnostics</summary><code id=\"diag\"></code></details>
<script>
const q=document.getElementById('q'), a=document.getElementById('answer'), d=document.getElementById('diag');
let conversationContext={turns:[]};
document.getElementById('ask').onclick=async()=>{
  const question=q.value.trim(); if(!question)return;
  a.className='answer'; a.textContent='Thinking...'; d.textContent='';
  try{
    const r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,conversation_context:conversationContext})});
    const x=await r.json();
    if(!r.ok){a.className='answer error';a.textContent=x.error||'Request failed';return;}
    a.textContent=x.released_text;
    conversationContext=x.conversation_context||{turns:[]};
    d.textContent=JSON.stringify({...x.diagnostics,conversation_context:conversationContext},null,2);
    q.value=''; q.focus();
  }catch(e){a.className='answer error';a.textContent='Local request failed: '+e;}
};
</script>
</body></html>"""


class _Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/":
            self.send_error(404)
            return
        body = _PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/ask":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            question = payload.get("question") if isinstance(payload, dict) else None
            raw_context = payload.get("conversation_context") if isinstance(payload, dict) else None
            if not isinstance(question, str) or not question.strip():
                self._json(400, {"error": "question must be non-empty text"})
                return
            try:
                context = HealthConversationContext.from_mapping(raw_context)
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
                return
            result = ask_health_question_live_with_arithmetic(
                question,
                conversation_context=context,
            )
            interpretation = result.interpretation.validated_interpretation
            interpreted = interpretation.interpretation if interpretation is not None else None
            self._json(
                200,
                {
                    "released_text": result.released_text,
                    "conversation_context": result.next_context.to_dict(),
                    "diagnostics": {
                        "status": result.status,
                        "selected_concept_id": result.selected_concept_id,
                        "selected_topic": result.selected_topic,
                        "render_outcome": result.render_outcome,
                        "interpretation_status": (
                            interpreted.interpretation_status if interpreted is not None else None
                        ),
                        "confidence": interpreted.confidence if interpreted is not None else None,
                    },
                },
            )
        except HealthCustomerPathError as exc:
            self._json(503, {"error": str(exc)})
        except Exception as exc:  # local founder slice: keep failure visible, but never expose secrets
            self._json(500, {"error": f"local product path failed: {type(exc).__name__}"})

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), _Handler)
    print(f"PolicyScna Health Customer v0 running at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
