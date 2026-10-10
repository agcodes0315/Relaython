# Relay HomeOps — Integration Steps

1. Copy `relay/home_assets.py` into `C:\Users\Lenovo\Desktop\Relay\relay\home_assets.py`.
2. Open your current `server.py`.
3. Copy the import block from `server-homeops-additions.py` beside the existing Relay imports.
4. Copy the tool/resource/prompt block after the existing MCP definitions.
5. Copy `test_homeops.py` to the Relay repository root.

Run:

```powershell
cd C:\Users\Lenovo\Desktop\Relay
.\.venv\Scripts\Activate.ps1

python -m py_compile .\relay\home_assets.py
python -m py_compile .\server.py

pytest .\test_homeops.py -v
pytest .\test_preflight.py -v
pytest .\test_relay_safety.py -v
```

Expected MCP surface after integration:

```text
17 tools
2 resources
1 prompt
```

Deploy with a NEW immutable image tag:

```text
homeops-v1
```

Then rerun the existing public end-to-end, recovery and durable-resume tests.

Finally merge `README-HOMEOPS-SECTION.md` into the main README.

Do not add CartSync, Wardrobe, Party Planner, Move Planner and Kitchen Cabinet as separate product features now. Put them under **What's Next** as future domains powered by the same Relay durable-execution architecture.
