import random
import streamlit as st

# トランプのカードを作成
suits = ["♥", "♦", "♣", "♠"]
ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
values = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10, "J": 10, "Q": 10, "K": 10, "A": 11}

# トランプデッキを作成
def create_deck():
    deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
    random.shuffle(deck)
    return deck

# カードの合計値を計算
def calculate_hand_value(hand):
    value = 0
    aces = 0  # エースの数を追跡

    for card in hand:
        rank = card[:-1]  # トランプのランク（数字部分）
        value += values[rank]
        if rank == "A":
            aces += 1
    
    # エースが含まれている場合、合計が 21 を超えないように調整
    while value > 21 and aces:
        value -= 10
        aces -= 1

    return value

# ゲームの初期設定
if 'deck' not in st.session_state:
    st.session_state.deck = create_deck()
    st.session_state.player_hand = [st.session_state.deck.pop(), st.session_state.deck.pop()]
    st.session_state.dealer_hand = [st.session_state.deck.pop(), st.session_state.deck.pop()]
    st.session_state.game_over = False

# プレイヤーとディーラーの手を表示
def show_hands():
    st.subheader("あなたの手札")
    st.write(" ".join(st.session_state.player_hand))
    st.write("合計: ", calculate_hand_value(st.session_state.player_hand))

    st.subheader("ディーラーの手札")
    st.write(" ".join(st.session_state.dealer_hand[:1]) + " ❓")
    st.write("合計: ？？")

# プレイヤーのアクション
def player_turn():
    if st.button("カードを引く"):
        st.session_state.player_hand.append(st.session_state.deck.pop())
        show_hands()

        # プレイヤーの合計が 21 を超えた場合
        if calculate_hand_value(st.session_state.player_hand) > 21:
            st.session_state.game_over = True
            st.write("バーストしました！あなたの負けです...😢")

    if st.button("スタンド"):
        st.session_state.game_over = True
        dealer_turn()

# ディーラーのアクション
def dealer_turn():
    st.subheader("ディーラーの手札")
    st.write(" ".join(st.session_state.dealer_hand))
    dealer_value = calculate_hand_value(st.session_state.dealer_hand)
    st.write(f"合計: {dealer_value}")

    # ディーラーの手が 17 以上になるまでカードを引く
    while dealer_value < 17:
        st.session_state.dealer_hand.append(st.session_state.deck.pop())
        dealer_value = calculate_hand_value(st.session_state.dealer_hand)
        st.write("ディーラーがカードを引きました。")
        st.write(" ".join(st.session_state.dealer_hand))
        st.write(f"合計: {dealer_value}")

    # 勝敗判定
    player_value = calculate_hand_value(st.session_state.player_hand)
    if dealer_value > 21:
        st.write("ディーラーがバーストしました！あなたの勝ち！🎉")
    elif dealer_value > player_value:
        st.write("ディーラーの勝ちです。😢")
    elif dealer_value < player_value:
        st.write("あなたの勝ち！🎉")
    else:
        st.write("引き分けです。🤝")

# ゲームオーバー時のリセットボタン
if st.session_state.game_over:
    if st.button("新しいゲームを始める"):
        st.session_state.deck = create_deck()
        st.session_state.player_hand = [st.session_state.deck.pop(), st.session_state.deck.pop()]
        st.session_state.dealer_hand = [st.session_state.deck.pop(), st.session_state.deck.pop()]
        st.session_state.game_over = False

# ゲームを進行
if not st.session_state.game_over:
    show_hands()
    player_turn()
else:
    dealer_turn()
