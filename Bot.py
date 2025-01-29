import chess
import asyncio
import websockets
import requests
import json

API_TOKEN = "your_lichess_api_token_here"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

async def bot_handler():
    async with websockets.connect("wss://lichess.org/api/v2/bot") as ws:
        await ws.send(f"Bearer {API_TOKEN}")
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("type") == "challenge":
                requests.post(f"https://lichess.org/api/challenge/{msg['challenge']['id']}/accept", headers=HEADERS)
            elif msg.get("type") == "gameState":
                await handle_move(ws, msg)

async def handle_move(ws, state):
    board = chess.Board()
    for move in state["moves"].split():
        board.push_uci(move)
    
    if board.turn == chess.WHITE == ("white" in state["gameId"]):
        cloud = requests.get("https://lichess.org/api/cloud-eval", params={"fen": board.fen()}).json()
        best_move = cloud["pvs"][0]["moves"].split()[0]
        await ws.send(json.dumps({"type": "move", "gameId": state["gameId"], "move": best_move}))

def verify_token():
    resp = requests.get("https://lichess.org/api/account", headers=HEADERS)
    if "bot:play" not in resp.json().get("scopes", []):
        print("Error: Token needs bot:play scope! Create bot account at:")
        print("https://lichess.org/login?referrer=/account/oauth/token/create")
        sys.exit(1)
    print("Bot account verified!")

if __name__ == "__main__":
    verify_token()
    print("Bot started. Ctrl+C to stop.")
    asyncio.get_event_loop().run_until_complete(bot_handler())
