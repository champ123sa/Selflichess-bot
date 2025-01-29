import requests
import json
import time
from datetime import datetime
import chess
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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
    logging.debug(f"Fetching best move for FEN: {fen}")
    response = requests.get(
        f"{LICHESS_API_URL}/analysis/standard",
        headers=get_headers(),
        params={'fen': fen}
    )
    if response.status_code == 200:
        analysis = response.json()
        if 'pvs' in analysis and len(analysis['pvs']) > 0:
            best_move = analysis['pvs'][0]['moves'].split()[0]
            logging.debug(f"Best move received: {best_move}")
            return best_move
        else:
            logging.error("No PVs found in analysis response")
            return None
    else:
        logging.error("Error fetching best move: %s %s", response.status_code, response.text)
        return None

def play_game(game_id, opponent):
    logging.info(f"Starting game {game_id} against {opponent}")
    url = f"{LICHESS_API_URL}/bot/game/stream/{game_id}"
    stream = requests.get(url, headers=get_headers(), stream=True)
    
    board = chess.Board()
    last_processed_move = ""
    
    try:
        for line in stream.iter_lines(decode_unicode=True):
            if line:
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    logging.error("Failed to decode JSON from line: %s", line)
                    continue
                
                logging.debug(f"Received data: {data}")
                
                if data.get('type') == 'gameFull':
                    moves = data['state']['moves'].split() if 'moves' in data['state'] else []
                    for move in moves:
                        try:
                            board.push_uci(move) if move else None
                        except ValueError:
                            try:
                                board.push_san(move)
                            except ValueError:
                                logging.error(f"Invalid move {move} ignored")
                    
                    # Ensure we don't process the same move twice
                    if moves:
                        last_processed_move = moves[-1]
                
                elif data.get('type') == 'gameState':
                    moves = data['moves'].split() if 'moves' in data else []
                    new_moves = moves[len(board.move_stack):]
                    for move in new_moves:
                        try:
                            board.push_uci(move) if move else None
                        except ValueError:
                            try:
                                board.push_san(move)
                            except ValueError:
                                logging.error(f"Invalid move {move} ignored")
                    
                    # Ensure we don't process the same move twice
                    if new_moves:
                        last_processed_move = new_moves[-1]
                
                elif data.get('type') == 'chatLine':
                    logging.info(f"Chat message: {data}")
                    continue
                
                elif data.get('type') == 'gameEnd':
                    logging.info(f"Game ended: {data}")
                    break
                
                if data.get('isMyTurn') and board.turn == (board.fen().split()[1] == 'w'):
                    fen = board.fen()
                    best_move = get_best_move(fen)
                    if best_move:
                        if chess.Move.from_uci(best_move) in board.legal_moves:
                            move_url = f"{LICHESS_API_URL}/bot/game/{game_id}/move/{best_move}"
                            response = requests.post(move_url, headers=get_headers())
                            if response.status_code == 200:
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
                            else:
                                logging.error("Error making move: %s %s", response.status_code, response.text)
                        else:
                            logging.error("Illegal move: %s", best_move)
                    else:
                        logging.error("No best move found for FEN: %s", fen)
    except Exception as e:
        logging.error("Error in play_game loop: %s", e)

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
        logging.info(f"Game challenged successfully: {game_id}")
    else:
        logging.error("Error challenging opponent: %s %s", response.status_code, response.text)

def analyze_games():
    for opponent, games in game_memory.items():
        for game in games:
            fen = game['fen']
            best_move = get_best_move(fen)
            if best_move and best_move != game['move']:
                logging.info(f"Learning from {opponent}: Correcting move from {game['move']} to {best_move}")

def main():
    while True:
        try:
            ongoing_games_response = requests.get(f"{LICHESS_API_URL}/account/playing", headers=get_headers())
            if ongoing_games_response.status_code == 200:
                ongoing_games = ongoing_games_response.json()
                logging.info(f"Ongoing games: {ongoing_games}")
                for game in ongoing_games.get('nowPlaying', []):
                    play_game(game['gameId'], game['opponent']['username'])
            
            analyze_games()

            # Uncomment and customize as needed
            # challenge_opponent('random_username', 60, 1)  # Example: 60 sec limit, 1 sec increment
            time.sleep(10)
        except Exception as e:
            logging.error("Error in main loop: %s", e)
            time.sleep(10)

if __name__ == "__main__":
    main()
