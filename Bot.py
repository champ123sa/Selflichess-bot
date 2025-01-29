import requests
import json
import time
from datetime import datetime
import chess
import chess.engine
import chess.pgn

# Configuration
LICHESS_API_URL = "https://lichess.org/api"
API_TOKEN = 'your_lichess_api_token'
BOT_USERNAME = 'your_bot_username'
MEMORY_FILE = 'game_memory.json'

# Initialize memory storage
try:
    with open(MEMORY_FILE, 'r') as f:
        game_memory = json.load(f)
except FileNotFoundError:
    game_memory = {}

def get_headers():
    return {
        'Authorization': f'Bearer {API_TOKEN}'
    }

def get_best_move(fen):
    response = requests.post(
        f"{LICHESS_API_URL}/eval",
        headers=get_headers(),
        data=json.dumps({'fen': fen})
    )
    if response.status_code == 200:
        return response.json().get('move')
    else:
        print("Error fetching best move:", response.text)
        return None

def play_game(game_id, opponent):
    url = f"{LICHESS_API_URL}/bot/game/stream/{game_id}"
    stream = requests.get(url, headers=get_headers(), stream=True)
    board = chess.Board()
    
    for line in stream.iter_lines():
        if line:
            data = json.loads(line.decode('utf-8'))
            if data['type'] == 'gameFull':
                moves = data['state']['moves'].split()
            elif data['type'] == 'gameState':
                moves = data['moves'].split()
            
            for move in moves:
                board.push_san(move) if move else None
            
            if data['type'] == 'gameState' and not data['isMyTurn']:
                fen = board.fen()
                best_move = get_best_move(fen)
                if best_move:
                    move_url = f"{LICHESS_API_URL}/bot/game/{game_id}/move/{best_move}"
                    requests.post(move_url, headers=get_headers())
                    board.push_uci(best_move)
                    
                    # Store game state in memory
                    if opponent not in game_memory:
                        game_memory[opponent] = []
                    game_memory[opponent].append({
                        'fen': fen,
                        'move': best_move,
                        'timestamp': datetime.now().isoformat()
                    })
                    with open(MEMORY_FILE, 'w') as f:
                        json.dump(game_memory, f)

def challenge_opponent(username, clock_limit, increment):
    url = f"{LICHESS_API_URL}/challenge/{username}"
    payload = {
        'clock.limit': clock_limit,
        'clock.increment': increment,
        'rated': 'true',
        'color': 'random'
    }
    response = requests.post(url, headers=get_headers(), data=payload)
    if response.status_code == 200:
        game_id = response.json()['challenge']['id']
        play_game(game_id, username)
    else:
        print("Error challenging opponent:", response.text)

def analyze_games():
    for opponent, games in game_memory.items():
        for game in games:
            fen = game['fen']
            best_move = get_best_move(fen)
            if best_move and best_move != game['move']:
                print(f"Learning from {opponent}: Correcting move from {game['move']} to {best_move}")

def main():
    while True:
        try:
            # Fetch ongoing games
            ongoing_games = requests.get(f"{LICHESS_API_URL}/account/playing", headers=get_headers()).json()
            for game in ongoing_games.get('nowPlaying', []):
                play_game(game['gameId'], game['opponent']['username'])
            
            # Analyze stored games periodically
            analyze_games()

            # Example: Challenge random players every 10 seconds (for demonstration purposes)
            # Uncomment and customize as needed
            # challenge_opponent('random_username', 60, 1)  # Example: 60 sec limit, 1 sec increment
            time.sleep(10)
        except Exception as e:
            print("Error in main loop:", e)
            time.sleep(10)

if __name__ == "__main__":
    main()
