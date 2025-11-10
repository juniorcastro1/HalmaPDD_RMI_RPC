# servidor_rpc.py
from xmlrpc.server import SimpleXMLRPCServer
from tabuleiro import HalmaGame # Usa o mesmo tabuleiro.py
import argparse
import time
import threading

# Esta classe é a "Interface de Operações"
# Todos os métodos aqui podem ser chamados remotamente pelo cliente.
class HalmaServerLogic:
    def __init__(self):
        self.jogo = HalmaGame()
        self.jogadores = []
        self.chat_messages = []
        # Contador de estado para o cliente saber se algo mudou
        self.estado_id = 0
        print("[INFO] Instância do jogo e lógica do servidor iniciadas.")

    def registrar_jogador(self):
        """Chamado por um cliente para entrar no jogo."""
        if len(self.jogadores) >= 2:
            return 0  # Retorna 0 como ID de erro (sala cheia)
        
        player_id = len(self.jogadores) + 1
        self.jogadores.append(player_id)
        print(f"[INFO] Jogador {player_id} registrado.")
        
        if len(self.jogadores) == 2:
            print("[INFO] Ambos os jogadores conectados. O jogo vai começar.")
            self.estado_id += 1 # Informa que o jogo começou
            
        return player_id

    def fazer_jogada(self, player_id, from_pos, to_pos):
        """Cliente chama esta função para tentar mover uma peça."""
        print(f"[JOGADA] Jogador {player_id} tentando mover de {from_pos} para {to_pos}")
        sucesso, mensagem = self.jogo.move_piece(player_id, from_pos, to_pos)
        if sucesso:
            self.estado_id += 1 # Atualiza o estado se a jogada foi válida
        return sucesso, mensagem

    def get_estado_do_jogo(self):
        """
        Cliente chama esta função (em loop) para pegar o estado completo do jogo.
        Isso é o coração da arquitetura de polling (sondagem).
        """
        return {
            "board": self.jogo.get_board(),
            "turn": self.jogo.current_turn,
            "winner": self.jogo.winner,
            "estado_id": self.estado_id,
            "jogadores_conectados": len(self.jogadores)
        }
        
    def enviar_chat(self, player_id, mensagem):
        """Cliente chama para enviar uma mensagem de chat."""
        print(f"[CHAT] Jogador {player_id}: {mensagem}")
        self.chat_messages.append(f"Jogador {player_id}: {mensagem}")
        # Retorna o ID da última mensagem (o índice dela)
        return len(self.chat_messages) - 1
        
    def get_novas_mensagens_chat(self, ultimo_id_conhecido):
        """Cliente chama para pegar apenas as mensagens que ele ainda não viu."""
        if ultimo_id_conhecido < len(self.chat_messages) - 1:
            return self.chat_messages[ultimo_id_conhecido + 1:]
        return []

    def desistir(self, player_id):
        """Cliente chama para desistir."""
        if self.jogo.winner: # Se o jogo já acabou, não faz nada
            return True

        print(f"[INFO] Jogador {player_id} desistiu.")
        self.jogo.forfeit(player_id)
        self.estado_id += 1
        return True
    
    def reset_game_se_necessario(self):
        """Verifica se o jogo acabou e, se sim, reinicia."""
        if self.jogo.winner and len(self.jogadores) > 0:
            print("\n[INFO] Fim de jogo detectado. Reiniciando o servidor em 5 segundos...")
            time.sleep(5)
            self.jogo = HalmaGame()
            self.jogadores = []
            self.chat_messages = []
            self.estado_id = 0
            print("[INFO] Servidor pronto para aceitar novas conexões.\n")
        return True


# --- BLOCO PRINCIPAL MODIFICADO (com argparse) ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inicia o servidor RMI/RPC do jogo Halma.")
    
    parser.add_argument('--host', 
                        default='0.0.0.0', 
                        help='Endereço de HOST para o servidor escutar (padrão: 0.0.0.0).')
    
    parser.add_argument('--port', 
                        type=int, 
                        default=8000,  # Porta padrão para RPC
                        help='Número da PORTA para o servidor escutar (padrão: 8000).')
    
    args = parser.parse_args()

    # Configuração e inicialização do servidor RPC
    try:
        with SimpleXMLRPCServer((args.host, args.port), allow_none=True) as server:
            server.register_instance(HalmaServerLogic())
            print(f"[ESCUTANDO] Servidor RMI/RPC pronto em {args.host}:{args.port}...")
            
            # Uma thread simples para verificar se o jogo acabou e reiniciar
            def game_reset_loop():
                while True:
                    server.instance.reset_game_se_necessario()
                    time.sleep(1)
            
            reset_thread = threading.Thread(target=game_reset_loop, daemon=True)
            reset_thread.start()

            server.serve_forever()
            
    except OSError as e:
        print(f"Erro ao iniciar servidor: {e}. A porta {args.port} já pode estar em uso.")
    except KeyboardInterrupt:
        print("\n[INFO] Servidor encerrado.")