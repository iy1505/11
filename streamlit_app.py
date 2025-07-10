import streamlit as st
import numpy as np

# オセロの盤面を初期化
def initialize_board():
    board = np.zeros((8, 8), dtype=int)
    board[3, 3] = 1  # 中央に白石
    board[4, 4] = 1  # 中央に白石
    board[3, 4] = -1  # 中央に黒石
    board[4, 3] = -1  # 中央に黒石
    return board

# 石を反転する処理
def flip_stones(board, row, col, player):
    directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    opponent = -player
    flipped = []
    
    for dr, dc in directions:
        r, c = row + dr, col + dc
        to_flip = []
        
        # 隣接する石を辿って、反対の色の石を探す
        while 0 <= r < 8 and 0 <= c < 8 and board[r, c] == opponent:
            to_flip.append((r, c))
            r, c = r + dr, c + dc
        
        # その方向にプレイヤーの石があれば反転
        if 0 <= r < 8 and 0 <= c < 8 and board[r, c] == player:
            flipped.extend(to_flip)
    
    # 反転する石を実際に反転
    for r, c in flipped:
        board[r, c] = player
    
    return flipped

# オセロのプレイが可能かどうかを判定
def valid_moves(board, player):
    valid = []
    for r in range(8):
        for c in range(8):
            if board[r, c] == 0:  # 空きマス
                flipped = flip_stones(board, r, c, player)
                if flipped:
                    valid.append((r, c))
    return valid

# ゲーム状態を表示
def display_board(board):
    colors = {1: 'white', -1: 'black'}
    st.write('## Othello Game')
    
    # 盤面を表示
    for i in range(8):
        row = ''
        for j in range(8):
            if board[i, j] == 0:
                row += '⬛ '  # 空のマス
            else:
                row += f'🟢 ' if board[i, j] == 1 else f'⚫ '
        st.text(row)

# ゲームの実行
def othello_game():
    board = initialize_board()
    current_player = -1  # 最初は黒（-1）
    player_name = {1: 'White', -1: 'Black'}

    # ゲームループ
    while True:
        # 盤面を表示
        display_board(board)
        
        # 現在のプレイヤーを表示
        st.write(f"Current Player: {player_name[current_player]}")
        
        # 有効な手を取得
        valid = valid_moves(board, current_player)

        if not valid:  # 有効な手がない場合
            st.write(f"{player_name[current_player]} has no valid moves. Skipping turn.")
            current_player = -current_player  # プレイヤー交代
            continue

        # 次に置く手を選択
        move = st.selectbox("Choose your move:", [f"({r},{c})" for r, c in valid])
        
        # 選択した手をボードに反映
        r, c = map(int, move[1:-1].split(','))
        board[r, c] = current_player
        
        # 石を反転
        flip_stones(board, r, c, current_player)

        # プレイヤー交代
        current_player = -current_player

# StreamlitのUI部分
st.title("Othello Game")

# ゲームスタートボタン
if st.button('Start Game'):
    othello_game()
