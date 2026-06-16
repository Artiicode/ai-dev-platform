#!/usr/bin/env python3
"""mcp_probe — drive an MCP stdio server through one handshake to verify it boots,
lists tools, and (optionally) answers a real tool call. Newline-delimited JSON-RPC.

Usage: mcp_probe.py <call_tool|""> <json-args> -- <command> [args...]
"""
import json, subprocess, sys, threading, time

def main():
    sep = sys.argv.index("--")
    call_tool = sys.argv[1] or None
    call_args = json.loads(sys.argv[2]) if sys.argv[2] else {}
    cmd = sys.argv[sep+1:]

    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, bufsize=1)
    outbox = []
    def reader():
        for line in p.stdout:
            line = line.strip()
            if line:
                outbox.append(line)
    threading.Thread(target=reader, daemon=True).start()

    def send(obj):
        p.stdin.write(json.dumps(obj) + "\n"); p.stdin.flush()

    def wait_for(_id, timeout=90):
        t0 = time.time()
        while time.time() - t0 < timeout:
            for ln in list(outbox):
                try: m = json.loads(ln)
                except Exception: continue
                if m.get("id") == _id:
                    return m
            if p.poll() is not None and time.time()-t0 > 2:
                break
            time.sleep(0.2)
        return None

    send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{
        "protocolVersion":"2024-11-05","capabilities":{},
        "clientInfo":{"name":"mcp-probe","version":"0.1"}}})
    init = wait_for(1)
    if not init:
        print("INIT_FAIL"); print("STDERR:", p.stderr.read()[:1500]); p.kill(); return 1
    si = init.get("result",{}).get("serverInfo",{})
    print("INIT_OK server=%s v%s" % (si.get("name","?"), si.get("version","?")))

    send({"jsonrpc":"2.0","method":"notifications/initialized","params":{}})
    send({"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}})
    tl = wait_for(2)
    tools = [t["name"] for t in (tl or {}).get("result",{}).get("tools",[])]
    print("TOOLS(%d): %s" % (len(tools), ", ".join(tools[:25])))

    if call_tool:
        send({"jsonrpc":"2.0","id":3,"method":"tools/call",
              "params":{"name":call_tool,"arguments":call_args}})
        cr = wait_for(3)
        if not cr:
            print("CALL_NO_RESPONSE"); p.kill(); return 1
        if "error" in cr:
            print("CALL_ERROR:", json.dumps(cr["error"])[:800])
        else:
            content = cr.get("result",{}).get("content",[])
            txt = " ".join(c.get("text","") for c in content if c.get("type")=="text")
            print("CALL_OK isError=%s len=%d" % (cr.get("result",{}).get("isError"), len(txt)))
            print("CALL_PREVIEW:", txt[:600].replace("\n"," "))
    p.kill()
    return 0

sys.exit(main())
