# jogador_rpc.py
import xmlrpc.client
import threading
import time
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox
from PIL import Image, ImageTk
import argparse # <-- Importa argparse

# Constantes do tabuleiro (mesmas de antes)
BOARD_SIZE = 10
CELL_SIZE = 40
P1_INITIAL_POSITIONS = [
    (0, 0), (1, 0), (2, 0), (3, 0), (0, 1), (1, 1), (2, 1), (0, 2), (1, 2), (0, 3)
]
P2_INITIAL_POSITIONS = [
    (BOARD_SIZE - 1 - r, BOARD_SIZE - 1 - c) for r, c in P1_INITIAL_POSITIONS
]

class HalmaClient:
    def __init__(self, master, host, port):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.board = [[0] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.player_id = 0
        self.is_my_turn = False
        self.selected_piece = None
        self.possible_moves = []
        self.jogo_ativo = True

        # Variáveis para sincronização de estado
        self.ultimo_estado_id = -1
        self.ultimo_chat_id = -1

        self.carrega_imagens()
        self._setup_ui()
        
        # Conecta-se ao servidor RPC
        try:
            self.servidor = xmlrpc.client.ServerProxy(f"http://{host}:{port}", allow_none=True)
            self.player_id = self.servidor.registrar_jogador()
            if self.player_id == 0:
                messagebox.showerror("Erro", "Sala cheia. Não foi possível conectar.")
                self.master.destroy()
                return
            self.master.title(f"Halma RPC - Jogador {self.player_id}")
            self.set_status("Aguardando oponente...")
        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar ao servidor em {host}:{port}\n{e}")
            self.master.destroy()
            return
            
        self.dispor_pecas()
        
        # Inicia o loop que verifica por atualizações do servidor
        self.update_thread = threading.Thread(target=self.loop_de_atualizacao, daemon=True)
        self.update_thread.start()

    # --- Funções de UI (carrega_imagens, _setup_ui, dispor_pecas, draw_board, set_status) ---
    # (Elas são idênticas ao código que você já tem, exceto por `dispor_pecas` renomeado)
    
    def carrega_imagens(self):
        """Carrega as imagens das peças"""
        try:
            planeta1 = Image.open("assets/planeta1.png").resize((32,32), Image.LANCZOS)
            planeta2 = Image.open("assets/planeta2.png").resize((32,32), Image.LANCZOS)
            self.planeta1_peca = ImageTk.PhotoImage(planeta1)
            self.planeta2_peca = ImageTk.PhotoImage(planeta2)
        except FileNotFoundError:
            messagebox.showerror("Erro de Imagem", "Poxa, aparentemente os arquivos de imagens não foram encontrados na pasta 'assets'. Verifique se estão nomeados corretamente.")
            self.master.destroy()

    def _setup_ui(self):
        self.status_label = tk.Label(self.master, text="Conectando...", font=("Arial", 12))
        self.status_label.pack(pady=5)
        self.canvas = tk.Canvas(self.master, width=BOARD_SIZE*CELL_SIZE, height=BOARD_SIZE*CELL_SIZE, bg='beige')
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.chat_display = scrolledtext.ScrolledText(self.master, height=6, state='disabled')
        self.chat_display.pack(pady=5, padx=5, fill=tk.X)
        chat_frame = tk.Frame(self.master)
        chat_frame.pack(fill=tk.X, padx=5)
        self.chat_input = tk.Entry(chat_frame)
        self.chat_input.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.chat_input.bind("<Return>", self.send_chat_message)
        self.send_button = tk.Button(chat_frame, text="Enviar", command=self.send_chat_message)
        self.send_button.pack(side=tk.RIGHT)
        self.forfeit_button = tk.Button(self.master, text="Desistir da Partida", command=self.forfeit_game, bg="red", fg="white", activebackground="darkred")
        self.forfeit_button.pack(pady=5)

    def dispor_pecas(self):
        for r, c in P1_INITIAL_POSITIONS: self.board[r][c] = 1
        for r, c in P2_INITIAL_POSITIONS: self.board[r][c] = 2
        self.draw_board()

    def draw_board(self):
        self.canvas.delete("all")
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                x1, y1 = c * CELL_SIZE, r * CELL_SIZE
                fill_color = "#f2e396"
                if (r, c) in P1_INITIAL_POSITIONS: fill_color = "#E0E8FF"
                elif (r, c) in P2_INITIAL_POSITIONS: fill_color = "#FFE0E0"
                self.canvas.create_rectangle(x1, y1, x1 + CELL_SIZE, y1 + CELL_SIZE, outline="black", fill=fill_color)
        for r, c in self.possible_moves:
            x1, y1 = c * CELL_SIZE, r * CELL_SIZE
            self.canvas.create_oval(x1 + 15, y1 + 15, x1 + CELL_SIZE - 15, y1 + CELL_SIZE - 15, fill="#90EE90", outline="")
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                player = self.board[r][c]
                if player != 0:
                    x_center = (c * CELL_SIZE) + (CELL_SIZE // 2)
                    y_center = (r * CELL_SIZE) + (CELL_SIZE // 2)
                    # Sua lógica de jogador 1 ser sempre planeta 1
                    image_to_draw = self.planeta1_peca if player == 1 else self.planeta2_peca
                    self.canvas.create_image(x_center, y_center, image=image_to_draw)
        if self.selected_piece:
            r, c = self.selected_piece
            x1, y1 = c * CELL_SIZE, r * CELL_SIZE
            self.canvas.create_oval(x1 + 2, y1 + 2, x1 + CELL_SIZE - 2, y1 + CELL_SIZE - 2, outline="red", width=3)

    def set_status(self, message, color="black"):
        self.status_label.config(text=message, fg=color)
    
    def loop_de_atualizacao(self):
        """Thread que pergunta ao servidor por atualizações (Polling)."""
        while self.jogo_ativo:
            try:
                # Pede o estado do jogo
                estado = self.servidor.get_estado_do_jogo()
                
                # Verifica se algo mudou 
                if estado["estado_id"] != self.ultimo_estado_id:
                    self.ultimo_estado_id = estado["estado_id"]
                    
                    self.board = estado["board"]
                    self.is_my_turn = (estado["turn"] == self.player_id) and (estado["winner"] is None)
                    self.draw_board() 
                    
                    if estado["winner"]:
                        self.jogo_ativo = False
                        if estado["winner"] == self.player_id:
                            self.set_status("Você Venceu!", "blue")
                        else:
                            self.set_status("Você Perdeu.", "black")
                    elif estado["jogadores_conectados"] < 2:
                        self.set_status("Aguardando oponente...")
                    elif self.is_my_turn:
                        self.set_status("É a sua vez!", "green")
                    else:
                        self.set_status("Vez do oponente.", "darkred")

                novas_mensagens = self.servidor.get_novas_mensagens_chat(self.ultimo_chat_id)
                if novas_mensagens:
                    for msg in novas_mensagens:
                        self.display_message(msg)
                    self.ultimo_chat_id += len(novas_mensagens)

            except Exception as e:
                if self.jogo_ativo:
                    print(f"Erro no loop de atualização: {e}")
                    self.set_status("Erro de conexão com o servidor...", "red")
                break
            
            time.sleep(1) # atualiza a cada um segundo

    def on_canvas_click(self, event):
        """Chamado quando o jogador clica no tabuleiro."""
        if not self.is_my_turn or not self.jogo_ativo:
            return
            
        c, r = event.x // CELL_SIZE, event.y // CELL_SIZE
        clicked_pos = (r, c)

        if self.selected_piece and clicked_pos in self.possible_moves:
            from_pos = self.selected_piece
            
            # --- CHAMADA RPC PARA O SERVIDOR ---
            try:
                # Chama a função remota como se fosse local
                sucesso, mensagem = self.servidor.fazer_jogada(self.player_id, from_pos, clicked_pos)
                if not sucesso:
                    messagebox.showwarning("Movimento Inválido", mensagem)
            except Exception as e:
                messagebox.showerror("Erro de Conexão", f"Falha ao enviar jogada: {e}")

            self.selected_piece = None
            self.possible_moves = []
            # O loop_de_atualizacao vai pegar a mudança e redesenhar.
            
        elif self.board[r][c] == self.player_id:
            self.selected_piece = clicked_pos
            self.possible_moves = self.calculate_possible_moves(r, c)
            self.draw_board()
        else:
            self.selected_piece = None
            self.possible_moves = []
            self.draw_board()

    def send_chat_message(self, event=None):
        """Envia uma mensagem de chat via RPC."""
        message = self.chat_input.get()
        if message:
            try:
                # Chame o servidor E guarde o ID da nova mensagem
                novo_id = self.servidor.enviar_chat(self.player_id, message)
                
                # Atualize o seu "último ID" localmente
                self.ultimo_chat_id = novo_id 
                
                # Exiba a sua mensagem local
                self.display_message(f"Eu: {message}")
                self.chat_input.delete(0, tk.END)
                
            except Exception as e:
                messagebox.showerror("Erro de Chat", f"Não foi possível enviar a mensagem: {e}")

    def forfeit_game(self):
        """Envia um comando de desistência via RPC."""
        if not self.jogo_ativo: return
        if messagebox.askyesno("Confirmar", "Você tem certeza que deseja desistir?"):
            try:
                self.servidor.desistir(self.player_id)
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao desistir: {e}")

    def on_closing(self):
        self.jogo_ativo = False # Para a thread de atualização
        self.master.destroy()
        
    def display_message(self, message):
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, message + "\n")
        self.chat_display.config(state='disabled')
        self.chat_display.yview(tk.END)
        
    def calculate_possible_moves(self, r, c):
        moves = set()
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0: continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and self.board[nr][nc] == 0:
                    moves.add((nr, nc))
        self._find_jumps_recursive((r, c), moves, set())
        return list(moves)

    def _find_jumps_recursive(self, current_pos, all_moves, visited_path):
        r, c = current_pos
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0: continue
                jump_over_r, jump_over_c = r + dr, c + dc
                dest_r, dest_c = r + 2*dr, c + 2*dc
                if (0 <= dest_r < BOARD_SIZE and 0 <= dest_c < BOARD_SIZE and
                        self.board[dest_r][dest_c] == 0 and
                        self.board[jump_over_r][jump_over_c] != 0):
                    if (dest_r, dest_c) not in visited_path:
                        all_moves.add((dest_r, dest_c))
                        new_path = visited_path.copy()
                        new_path.add((dest_r, dest_c))
                        self._find_jumps_recursive((dest_r, dest_c), all_moves, new_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inicia o cliente RMI/RPC do jogo Halma.")
    
    parser.add_argument('--host', 
                        default='127.0.0.1', 
                        help='Endereço de HOST do servidor para conectar (padrão: 127.0.0.1).')
    
    parser.add_argument('--port', 
                        type=int, 
                        default=8000, # Porta padrão para RPC
                        help='Número da PORTA do servidor para conectar (padrão: 8000).')
    
    args = parser.parse_args()

    root = tk.Tk()
    app = HalmaClient(root, args.host, args.port)
    root.mainloop()