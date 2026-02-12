# test_pc_ws_client.py
import asyncio, websockets, json, sys, time

async def run():
    uri = "ws://192.168.137.142:8765"   # change PC_IP
    async with websockets.connect(uri) as ws:
        # send auth + text
        await ws.send(json.dumps({"auth":"SARA_SECRET_123","text":"director of gits"}))
        # read messages for up to 15s
        t0 = time.time()
        while True:
            try:
                rem = max(0.5, 15 - (time.time()-t0))
                m = await asyncio.wait_for(ws.recv(), timeout=rem)
                print("RCV>", m)
            except asyncio.TimeoutError:
                break

asyncio.run(run())
