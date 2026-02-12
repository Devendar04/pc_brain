import asyncio
import json
import logging
import websockets
from websockets.exceptions import ConnectionClosed

from server_logic import handle_text      # ASYNC
from common import tts_to_file             # ASYNC
from pc_event_queue import pop             # blocking

HOST = "0.0.0.0"
PORT = 8765
SECRET = "SARA_SECRET_123"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pc_ws")

clients = set()
async def tts_background(ws, reply):
    try:
        audio = await tts_to_file(reply)
        if audio:
            await safe_send(ws, {
                "type": "audio",
                "audio": f"/audio/{audio}"
            })
    except Exception:
        logger.exception("TTS failed")

# ---------- SAFE SEND ----------
async def safe_send(ws, payload):
    try:
        await ws.send(json.dumps(payload, ensure_ascii=False))
        return True
    except ConnectionClosed:
        clients.discard(ws)
        return False
    except Exception:
        logger.exception("safe_send failed")
        clients.discard(ws)
        return False

# ---------- HEARTBEAT ----------
async def heartbeat(ws):
    try:
        while True:
            await safe_send(ws, {"type": "ping"})
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        pass

# ---------- PROCESS COMMAND ----------
async def process_command(ws, text):
    try:
        logger.info("DEBUG: calling handle_text for text=%s", text)

        try:
            result = await handle_text(text)
            logger.info("DEBUG: handle_text returned: %s", repr(result)[:400])
        except Exception:
            logger.exception("handle_text failed")
            await safe_send(ws, {
                "reply": "Server processing error.",
                "intent": {"name": "error", "state": "HANDLE_FAIL"}
            })
            return

        if not isinstance(result, dict):
            result = {"reply": str(result)}

        ok = await safe_send(ws, result)
        asyncio.create_task(tts_background(ws, result["reply"]))
        logger.info("DEBUG: response sent ok=%s", ok)

    except Exception:
        logger.exception("process_command crashed")
        await safe_send(ws, {
            "reply": "Server crashed.",
            "intent": {"name": "error", "state": "CRASH"}
        })

# ---------- WS HANDLER ----------
async def ws_handler(ws):
    logger.info("Client connected: %s", ws.remote_address)
    clients.add(ws)

    hb = asyncio.create_task(heartbeat(ws))
    tasks = set()

    try:
        async for msg in ws:
            try:
                try:
                    data = json.loads(msg)
                except Exception:
                    print("[VOICE_WS] bad json", msg, flush=True)
                    continue
            
                if data.get("auth") != SECRET:
                     try:
                         await ws.send(json.dumps({"type":"error","reason":"unauthorized"}))
                     except Exception as e:
                         print("[VOICE_WS] send error while notifying unauthorized:", e, flush=True)
                     continue

                text = (data.get("text") or "").strip()
                if not text:
                    continue

                try:
                    await ws.send(json.dumps({"type":"ack","received": text}))
                except Exception as e:
                    print("[VOICE_WS] failed to send ack:", e, flush=True)
                    # do not reraise — log and continue to avoid killing the handler
                    continue

                task = asyncio.create_task(process_command(ws, text))
                tasks.add(task)
                task.add_done_callback(tasks.discard)

            except Exception:
                logger.exception("Message handling error")

    except ConnectionClosed:
        pass
    finally:
        hb.cancel()
        for t in tasks:
            t.cancel()
        clients.discard(ws)
        logger.info("Client disconnected")

# ---------- FACE EVENT DISPATCH ----------
async def face_dispatch_loop():
    while True:
        try:
            event = await asyncio.to_thread(pop)
            if not event:
                await asyncio.sleep(0.05)
                continue

            payload = json.dumps(event, ensure_ascii=False)
            for ws in list(clients):
                try:
                    await ws.send(payload)
                except Exception:
                    clients.discard(ws)

        except Exception:
            logger.exception("face dispatch error")
            await asyncio.sleep(0.2)

# ---------- MAIN ----------
async def main():
    logger.info("PC Brain WS running on %s:%d", HOST, PORT)

    async with websockets.serve(
        ws_handler,
        HOST,
        PORT,
        ping_interval=None,
        ping_timeout=None,
        max_size=2**20
    ):
        asyncio.create_task(face_dispatch_loop())
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
