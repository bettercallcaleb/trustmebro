import contextlib
import io
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import measurement
import trustmebro

class CLITests(unittest.TestCase):
    def test_http_roundtrip(self):
        manifest=measurement.generate(211,1,"all",1)
        prompts={}
        for t in manifest["tasks"]:
            value=trustmebro.canonical(t["answer"]) if t["format"]=="json" else str(t["answer"])
            for mode in ("strict","relaxed"):
                prompts[measurement.prompt_for(t,mode)]=value if mode=="strict" else "Calculation.\nFINAL: "+value
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                data=json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                reply={"choices":[{"message":{"content":prompts[data["messages"][0]["content"]]},"finish_reason":"stop"}],"usage":{"completion_tokens":5}}
                body=json.dumps(reply).encode()
                self.send_response(200)
                self.send_header("Content-Type","application/json")
                self.send_header("Content-Length",str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        with ThreadingHTTPServer(("127.0.0.1",0),Handler) as server, tempfile.TemporaryDirectory() as tmp:
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                root=Path(tmp)
                trustmebro.save(root/"tasks.json",manifest)
                (root/"model.fixture").write_bytes(b"synthetic fixture")
                cmd=[sys.executable,"trustmebro.py","run","--tasks",str(root/"tasks.json"),"--url",f"http://127.0.0.1:{server.server_port}/v1","--model","fixture","--runtime","mock HTTP","--hardware","none","--artifact",str(root/"model.fixture"),"--budgets","64","--modes","strict,relaxed","--out",str(root/"run.json")]
                profiles=json.loads(subprocess.check_output(cmd,text=True))
                self.assertEqual(len(profiles),4)
                self.assertTrue(all(p["strict_accuracy"]==1 and p["tokens_per_success"]==5 for p in profiles))
                replay=json.loads(subprocess.check_output([sys.executable,"trustmebro.py","score",str(root/"run.json")],text=True))
                self.assertEqual(replay,profiles)
            finally:server.shutdown();thread.join()
if __name__=="__main__":unittest.main()
