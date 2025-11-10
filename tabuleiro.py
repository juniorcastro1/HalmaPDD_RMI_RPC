# tabuleiro.py
# (Este arquivo é o mesmo que já tínhamos,
# apenas garantindo que a função get_board() esteja presente)

class HalmaGame:
    def __init__(self, board_size=10):
        self.board_size = board_size
        self.board = [[0] * board_size for _ in range(board_size)]
        self.current_turn = 1
        self.winner = None
        self._setup_pieces()

    def _setup_pieces(self):
        initial_positions_p1 = [
            (0, 0), (1, 0), (2, 0), (3, 0),
            (0, 1), (1, 1), (2, 1),
            (0, 2), (1, 2),
            (0, 3)
        ]
        for r, c in initial_positions_p1:
            self.board[r][c] = 1
        for r, c in initial_positions_p1:
            self.board[self.board_size - 1 - r][self.board_size - 1 - c] = 2

    def get_board(self):
        """Retorna o estado atual do tabuleiro."""
        return self.board

    def is_valid_move(self, player, from_pos, to_pos, path):
        from_r, from_c = from_pos
        to_r, to_c = to_pos
        if not (0 <= to_r < self.board_size and 0 <= to_c < self.board_size):
            return False
        if self.board[to_r][to_c] != 0:
            return False
        if self.board[from_r][from_c] != player:
            return False
        
        is_adjacent = abs(from_r - to_r) <= 1 and abs(from_c - to_c) <= 1
        if is_adjacent and not path:
            return True
        
        jump_r = from_r + (to_r - from_r) // 2
        jump_c = from_c + (to_c - from_c) // 2
        is_jump = abs(from_r - to_r) in [0, 2] and abs(from_c - to_c) in [0, 2]
        if is_jump and self.board[jump_r][jump_c] != 0:
            if to_pos not in path:
                return True
        return False

    def move_piece(self, player, from_pos, to_pos):
        if self.current_turn != player:
            return False, "Não é o seu turno."
        
        if self.is_valid_move(player, from_pos, to_pos, []):
            from_r, from_c = from_pos
            to_r, to_c = to_pos
            self.board[to_r][to_c] = player
            self.board[from_r][from_c] = 0
            self.check_win_condition()
            if not self.winner:
                self.current_turn = 3 - player
            return True, "Movimento realizado."
        else:
            return False, "Movimento inválido."

    def check_win_condition(self):
        # (Lógica de verificação de vitória)
        p1_wins = True
        destination_p1 = [(9,9), (8,9), (7,9), (6,9), (9,8), (8,8), (7,8), (9,7), (8,7), (9,6)]
        for r, c in destination_p1:
             if self.board[r][c] != 1: p1_wins = False; break
        if p1_wins: self.winner = 1

        p2_wins = True
        destination_p2 = [(0,0), (1,0), (2,0), (3,0), (0,1), (1,1), (2,1), (0,2), (1,2), (0,3)]
        for r, c in destination_p2:
            if self.board[r][c] != 2: p2_wins = False; break
        if p2_wins: self.winner = 2

    def forfeit(self, player_id):
        """Define o vencedor por desistência."""
        self.winner = 3 - player_id
        return True