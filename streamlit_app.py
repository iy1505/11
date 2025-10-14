import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import os

# ページ設定
st.set_page_config(
    page_title="日田ナビ（Hita Navi）",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# セッション状態の初期化
if 'mode' not in st.session_state:
    st.session_state.mode = '観光モード'
if 'language' not in st.session_state:
    st.session_state.language = '日本語'
if 'current_location' not in st.session_state:
    st.session_state.current_location = [33.3219, 130.9414]  # 日田市のデフォルト座標

# データ読み込み関数
@st.cache_data
def load_spots_data():
    """Excelファイルからスポットデータを読み込む"""
    try:
        tourism_df = pd.read_excel('spots.xlsx', sheet_name='観光')
        disaster_df = pd.read_excel('spots.xlsx', sheet_name='防災')
        return tourism_df, disaster_df
    except FileNotFoundError:
        # サンプルデータを作成
        tourism_df = pd.DataFrame({
            '番号': [1, 2, 3],
            'スポット名': ['豆田町', '日田温泉', '咸宜園'],
            '緯度': [33.3219, 33.3200, 33.3240],
            '経度': [130.9414, 130.9400, 130.9430],
            '説明': ['江戸時代の町並み', '温泉施設', '歴史的教育施設']
        })
        disaster_df = pd.DataFrame({
            '番号': [1, 2, 3],
            'スポット名': ['日田市役所（避難所）', '中央公民館', '総合体育館'],
            '緯度': [33.3219, 33.3250, 33.3180],
            '経度': [130.9414, 130.9450, 130.9380],
            '説明': ['収容人数: 500名', '収容人数: 300名', '収容人数: 800名']
        })
        return tourism_df, disaster_df

# 地図表示関数
def create_map(spots_df, center_location, zoom=13):
    """Foliumマップを作成"""
    m = folium.Map(
        location=center_location,
        zoom_start=zoom,
        tiles='OpenStreetMap'
    )
    
    # 現在地マーカー
    folium.Marker(
        center_location,
        popup="現在地",
        icon=folium.Icon(color='red', icon='home', prefix='fa')
    ).add_to(m)
    
    # スポットマーカー
    for idx, row in spots_df.iterrows():
        folium.Marker(
            [row['緯度'], row['経度']],
            popup=f"<b>{row['スポット名']}</b><br>{row['説明']}",
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(m)
    
    return m

# サイドバー
with st.sidebar:
    st.title("🗺️ 日田ナビ")
    
    # 言語切替
    language = st.selectbox(
        "言語 / Language",
        ["日本語", "English"],
        key='language_selector'
    )
    st.session_state.language = language
    
    st.divider()
    
    # モード選択
    mode = st.radio(
        "モード選択",
        ["観光モード", "防災モード"],
        key='mode_selector'
    )
    st.session_state.mode = mode
    
    st.divider()
    
    # 天気情報（簡易版）
    st.subheader("🌤️ 現在の天気")
    st.info("日田市: 晴れ 23°C")
    st.caption(f"更新: {datetime.now().strftime('%Y/%m/%d %H:%M')}")

# メインコンテンツ
st.title(f"📍 {st.session_state.mode}")

# データ読み込み
tourism_df, disaster_df = load_spots_data()

# モードに応じた表示
if st.session_state.mode == '観光モード':
    tab1, tab2, tab3, tab4 = st.tabs(["マップ", "スポット一覧", "イベント", "おすすめプラン"])
    
    with tab1:
        st.subheader("🗺️ 観光マップ")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # 地図表示
            m = create_map(tourism_df, st.session_state.current_location)
            map_data = st_folium(m, width=700, height=500)
        
        with col2:
            st.markdown("### 📌 機能")
            if st.button("📍 現在地を取得", use_container_width=True):
                st.success("現在地を更新しました")
            
            st.markdown("### フィルター")
            category = st.multiselect(
                "カテゴリー",
                ["観光地", "飲食店", "温泉", "歴史"],
                default=["観光地"]
            )
    
    with tab2:
        st.subheader("📋 スポット一覧")
        
        # 検索機能
        search = st.text_input("🔍 スポット名で検索")
        
        if search:
            filtered_df = tourism_df[tourism_df['スポット名'].str.contains(search, na=False)]
        else:
            filtered_df = tourism_df
        
        # スポット表示
        for idx, row in filtered_df.iterrows():
            with st.expander(f"📍 {row['スポット名']}"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"**説明:** {row['説明']}")
                    st.write(f"**座標:** {row['緯度']}, {row['経度']}")
                with col2:
                    if st.button(f"ルート案内", key=f"route_{idx}"):
                        st.info("ルート案内機能は準備中です")
    
    with tab3:
        st.subheader("📅 イベントカレンダー")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            selected_month = st.selectbox(
                "月を選択",
                list(range(1, 13)),
                index=datetime.now().month - 1
            )
        
        st.info("イベント情報は準備中です")
    
    with tab4:
        st.subheader("💡 おすすめプラン")
        
        col1, col2 = st.columns(2)
        with col1:
            plan_type = st.selectbox(
                "プランタイプ",
                ["家族向け", "一人旅向け", "カップル向け"]
            )
        with col2:
            budget = st.selectbox(
                "予算",
                ["0～5,000円", "5,001～10,000円", "10,001～30,000円", "30,000円以上"]
            )
        
        if st.button("プランを提案", use_container_width=True):
            st.success(f"{plan_type}・{budget}のプランを提案します（準備中）")

else:  # 防災モード
    tab1, tab2, tab3 = st.tabs(["避難所マップ", "ハザードマップ", "防災情報"])
    
    with tab1:
        st.subheader("🏥 避難所マップ")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # 避難所地図表示
            m = create_map(disaster_df, st.session_state.current_location)
            map_data = st_folium(m, width=700, height=500)
        
        with col2:
            st.markdown("### 🚨 緊急機能")
            if st.button("🚶 最寄り避難所へ", type="primary", use_container_width=True):
                st.warning("最寄りの避難所へのルートを案内します")
            
            st.markdown("### 📊 避難所状況")
            st.metric("開設避難所", "3箇所")
            st.metric("収容可能人数", "1,600名")
    
    with tab2:
        st.subheader("🗾 ハザードマップ")
        
        hazard_type = st.selectbox(
            "ハザードマップの種類",
            ["洪水", "土砂災害", "地震"]
        )
        
        st.info("ハザードマップ表示機能は準備中です")
    
    with tab3:
        st.subheader("📢 防災情報")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🏪 営業中の店舗")
            st.success("✅ ファミリーマート日田店")
            st.success("✅ ローソン日田中央店")
            st.warning("⚠️ セブンイレブン日田店（確認中）")
        
        with col2:
            st.markdown("### 🥤 自動販売機")
            st.info("周辺10箇所の自動販売機を表示")
        
        st.divider()
        
        st.markdown("### 🎒 予算別防災グッズ提案")
        budget = st.selectbox(
            "予算を選択",
            ["3,000円以下", "3,000～10,000円", "10,000円以上"],
            key='disaster_budget'
        )
        
        if st.button("防災グッズを提案", use_container_width=True):
            st.success(f"{budget}の防災グッズを提案します（準備中）")

# フッター
st.divider()
st.caption("© 2025 日田ナビ（Hita Navi） | お問い合わせ | プライバシーポリシー")