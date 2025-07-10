import streamlit as st
import random

# タイトル
st.title("✊✋✌️ じゃんけんゲーム")

# 説明
st.write("好きな手を選んでね！")

# 選択肢
choices = ["✊ グー", "✋ パー", "✌️ チョキ"]
user_choice = st.radio("あなたの手を選んでください：", choices)

# 勝敗を判定する関数
def judge(player, computer):
    if player == computer:
        return "引き分け！"
    elif (
        (player == "グー" and computer == "チョキ") or
        (player == "チョキ" and computer == "パー") or
        (player == "パー" and computer == "グー")
    ):
        return "あなたの勝ち！🎉"
    else:
        return "あなたの負け...😢"

# ボタンを押したら実行
if st.button("勝負！"):
    # ユーザーの選択を絵文字を除いて取得
    player_hand = user_choice.split()[1]
    # コンピューターの手をランダムで選ぶ
    computer_hand = random.choice(["グー", "チョキ", "パー"])
    
    # 結果表示
    st.write(f"あなたの手：{player_hand}")
    st.write(f"コンピューターの手：{computer_hand}")
    result = judge(player_hand, computer_hand)
    st.subheader(result)
