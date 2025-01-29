import argparse
import asyncio
import chess
import websockets
import requests
import json
import sys
from enum import Enum

API_TOKEN = "your_token_here"
COMMANDS = {
    'challenge': 'Challenge a player: challenge USERNAME [TIME] [COLOR] [RATED]',
    'matchmaking': 'Start automated matchmaking',
    'quit': 'Exit the bot',
    'help': 'Show command list',
    'rechallenge': 'Rematch last opponent',
    'stop': 'Stop matchmaking'
}

class ChallengeColor(Enum):
    WHITE = "white"
    BLACK = "black"
    RANDOM = "random"

class BotInterface:
    def __init__(self):
        self.matchmaking_active = False
        self.last_challenge = None

    async def command_loop(self):
        while True:
            cmd = await asyncio.to_thread(input, "bot> ")
            await self.handle_command(cmd.split())

    async def handle_command(self, parts):
        match parts[0].lower():
            case 'challenge':
                self.handle_challenge(parts[1:])
            case 'matchmaking':
                self.start_matchmaking()
            case 'rechallenge':
                self.handle_rechallenge()
            case 'stop':
                self.stop_matchmaking()
            case 'help':
                self.show_help()
            case 'quit':
                sys.exit(0)
            case _:
                print("Unknown command")

    def handle_challenge(self, args):
        try:
            username = args[0]
            time_control = args[1] if len(args)>1 else "3+2"
            color = ChallengeColor(args[2].lower()) if len(args)>2 else ChallengeColor.RANDOM
            rated = args[3].lower() == "rated" if len(args)>3 else True
            
            print(f"Challenging {username} ({time_control}, {color.value})")
            # Add challenge logic here
            
        except Exception as e:
            print(f"Invalid command: {e}")

    def start_matchmaking(self):
        self.matchmaking_active = True
        print("Matchmaking started...")

    def stop_matchmaking(self):
        self.matchmaking_active = False
        print("Matchmaking stopped")

    def handle_rechallenge(self):
        if self.last_challenge:
            print(f"Rechallenging {self.last_challenge}")
        else:
            print("No previous challenge")

    def show_help(self):
        print("Available commands:")
        for cmd, desc in COMMANDS.items():
            print(f"{cmd:12} {desc}")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--matchmaking', '-m', action='store_true', help='Start in matchmaking mode')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug output')
    args = parser.parse_args()

    interface = BotInterface()
    asyncio.create_task(interface.command_loop())

    async with websockets.connect("wss://lichess.org/api/v2/bot") as ws:
        await ws.send(f"Bearer {API_TOKEN}")
        print("Bot connected to Lichess")
        if args.matchmaking:
            interface.start_matchmaking()

        while True:
            msg = json.loads(await ws.recv())
            if msg.get("type") == "gameState":
                # Add game handling logic
                pass
            elif msg.get("type") == "challenge":
                requests.post(f"https://lichess.org/api/challenge/{msg['challenge']['id']}/accept", 
                            headers={"Authorization": f"Bearer {API_TOKEN}"})

if __name__ == "__main__":
    asyncio.run(main())
