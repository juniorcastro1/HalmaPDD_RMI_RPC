# servidor.py

import socket
import threading
from tabuleiro import HalmaGame
import argparse  # <-- NOVO IMPORT
import time

# HOST e PORT foram removidos daqui

jogadores = []
player_map = {}
jogo = HalmaGame()
game_lock = threading.Lock()

def reset_game():
    global jogo, jogadores, player_map
    print("\n[INFO] Fim de jogo. Reiniciando o servidor...")
    time.sleep(5)
    for conn in jogadores:
        conn.close()
    jogadores.clear()
    player_map.clear()
    jogo = HalmaGame()
    print("[INFO] Servidor pronto para aceitar novas conexões.\n")

def handle_jogador(conn, player_id):
    global jogo
    print(f"[JOGADOR {player_id}] Conectado de {conn.getpeername()}")

    while True:
        try:
            data = conn.recv(1024).decode('utf-8')
            if not data:
                break

            print(f"[JOGADOR {player_id}] Mensagem: {data}")
            parts = data.split(':')
            command = parts[0]

            with game_lock:
                if jogo.winner:
                    continue

                if command == "MOVE":
                    if jogo.current_turn != player_id:
                        conn.send("ERRO: Calma lá, ainda não é o seu turno!.".encode('utf-8'))
                        continue
                    
                    from_pos = tuple(map(int, parts[1].split(',')))
                    to_pos = tuple(map(int, parts[2].split(',')))
                    
                    if jogo.is_valid_move(player_id, from_pos, to_pos, []):
                        jogo.move_piece(player_id, from_pos, to_pos)
                        broadcast(f"UPDATE:{from_pos[0]},{from_pos[1]}:{to_pos[0]},{to_pos[1]}")
                        
                        if jogo.winner:
                            broadcast(f"VENCEDOR:{jogo.winner}")
                            reset_game()
                        else:
                             jogadores[jogo.current_turn-1].send(f"SEU_TURNO".encode('utf-8'))
                    else:
                        conn.send("ERRO:Movimento inválido.".encode('utf-8'))
                
                elif command == "CHAT":
                    message = parts[1]
                    broadcast(f"CHAT:{player_id}:{message}", sender_conn=conn)
                
                elif command == "DESISTENCIA":
                    winner = 3 - player_id
                    jogo.winner = winner
                    broadcast(f"VENCEDOR:{winner}:DESISTENCIA")
                    reset_game()

        except (ConnectionResetError, IndexError):
            break

    print(f"[JOGADOR {player_id}] Desconectado.")
    if not jogo.winner and len(jogadores) == 2:
        jogadores.remove(conn)
        winner = 3 - player_id
        jogo.winner = winner
        broadcast(f"VENCEDOR:{winner}:DESISTENCIA")
        reset_game()
    elif conn in jogadores:
        jogadores.remove(conn)

def broadcast(message, sender_conn=None):
    for client_conn in jogadores:
        if client_conn != sender_conn:
            try:
                client_conn.send(message.encode('utf-8'))
            except Exception as e:
                print(f"Erro ao transmitir: {e}")

# Função para receber Host e Porta
def start_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_socket.bind((host, port))
    except OSError as e:
        print(f"Erro ao iniciar servidor: {e}. A porta {port} já pode estar em uso.")
        return
        
    server_socket.listen(2)
    print(f"[ESCUTANDO] Servidor em {host}:{port}")

    player_id_counter = 1
    while True:
        if len(jogadores) < 2:
            conn, addr = server_socket.accept()
            jogadores.append(conn)
            player_map[conn] = player_id_counter
            
            thread = threading.Thread(target=handle_jogador, args=(conn, player_id_counter))
            thread.start()
            
            conn.send(f"BEMVINDO:{player_id_counter}".encode('utf-8'))
            
            if len(jogadores) == 2:
                print("Ambos os jogadores conectados. Iniciando o jogo.")
                broadcast("INICIAR_JOGO")
                jogadores[0].send("SEU_TURNO".encode('utf-8'))
                player_id_counter = 1
            else:
                player_id_counter += 1
        else:
            time.sleep(1)

if __name__ == "__main__": #cria argumentos para poder alterar o host e porta
    parser = argparse.ArgumentParser(description="Inicia o servidor do jogo.")
    
    # Define os argumentos que o script pode aceitar
    parser.add_argument('--host', 
                        default='0.0.0.0', 
                        help='Endereço de HOST para o servidor escutar (padrão: 0.0.0.0, aceita todas as conexões).')
    
    parser.add_argument('--port', 
                        type=int, 
                        default=65432, 
                        help='Número da PORTA para o servidor escutar (padrão: 65432).')
    
    # Analisa os argumentos passados pelo usuário
    args = parser.parse_args()
    
    # Inicia o servidor com os argumentos fornecidos
    start_server(args.host, args.port)