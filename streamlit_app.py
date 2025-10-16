import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
import requests

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
    st.session_state.current_location = [33.3219, 130.9414]
if 'selected_spots' not in st.session_state:
    st.session_state.selected_spots = []

# データ読み込み関数
@st.cache_data
def load_spots_data():
    """Excelファイルからスポットデータを読み込む"""
    try:
        tourism_df = pd.read_excel('spots.xlsx', sheet_name='観光')
        disaster_df = pd.read_excel('spots.xlsx', sheet_name='防災')
        return tourism_df, disaster_df
    except FileNotFoundError:
        # サンプルデータ
        tourism_df = pd.DataFrame({
            '番号': [1, 2, 3, 4, 5, 6],
            'スポット名': ['豆田町', '日田温泉', '咸宜園', '天ヶ瀬温泉', '小鹿田焼の里', '大山ダム'],
            '緯度': [33.3219, 33.3200, 33.3240, 33.2967, 33.3500, 33.3800],
            '経度': [130.9414, 130.9400, 130.9430, 130.9167, 130.9600, 130.9200],
            '説明': ['江戸時代の町並みが残る歴史的な地区', '日田の名湯・温泉施設', 
                   '日本最大の私塾跡・歴史的教育施設', '自然豊かな温泉街', 
                   '伝統工芸の陶器の里', '美しい景観のダム'],
            'カテゴリー': ['観光地', '温泉', '歴史', '温泉', '観光地', '観光地'],
            '営業時間': ['終日', '9:00-21:00', '9:00-17:00', '終日', '9:00-17:00', '終日'],
            '料金': ['無料', '500円', '300円', '無料', '無料', '無料']
        })
        disaster_df = pd.DataFrame({
            '番号': [1, 2, 3, 4, 5],
            'スポット名': ['日田市役所（避難所）', '中央公民館', '総合体育館', '桂林公民館', '三花公民館'],
            '緯度': [33.3219, 33.3250, 33.3180, 33.3300, 33.3100],
            '経度': [130.9414, 130.9450, 130.9380, 130.9500, 130.9350],
            '説明': ['市役所・第一避難所', '中央地区の避難所', '大規模避難所', 
                   '桂林地区の避難所', '三花地区の避難所'],
            '収容人数': [500, 300, 800, 200, 250],
            '状態': ['開設中', '開設中', '開設中', '待機中', '待機中']
        })
        return tourism_df, disaster_df

# 距離計算関数
def calculate_distance(lat1, lng1, lat2, lng2):
    """2点間の距離を計算（km）"""
    R = 6371  # 地球の半径（km）
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lng = radians(lng2 - lng1)
    
    a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

# 地図作成関数（改良版）
def create_enhanced_map(spots_df, center_location, selected_spot=None, show_route=False):
    """Foliumマップを作成"""
    m = folium.Map(
        location=center_location,
        zoom_start=13,
        tiles='OpenStreetMap'
    )
    
    # 現在地マーカー（赤・大きめ）
    folium.Marker(
        center_location,
        popup=folium.Popup("📍 <b>現在地</b>", max_width=200),
        tooltip="現在地",
        icon=folium.Icon(color='red', icon='home', prefix='fa')
    ).add_to(m)
    
    # スポットマーカー
    for idx, row in spots_df.iterrows():
        # 距離計算
        distance = calculate_distance(
            center_location[0], center_location[1],
            row['緯度'], row['経度']
        )
        
        # ポップアップHTML
        popup_html = f"""
        <div style="width: 250px; font-family: sans-serif;">
            <h4 style="margin: 0 0 10px 0; color: #1f77b4;">{row['スポット名']}</h4>
            <p style="margin: 5px 0;"><b>📝 説明:</b><br>{row['説明']}</p>
            <p style="margin: 5px 0;"><b>📏 現在地から:</b> {distance:.2f} km</p>
        """
        
        # カテゴリー情報（観光モード）
        if 'カテゴリー' in row:
            popup_html += f'<p style="margin: 5px 0;"><b>🏷️ カテゴリー:</b> {row["カテゴリー"]}</p>'
        if '営業時間' in row:
            popup_html += f'<p style="margin: 5px 0;"><b>🕐 営業時間:</b> {row["営業時間"]}</p>'
        if '料金' in row:
            popup_html += f'<p style="margin: 5px 0;"><b>💰 料金:</b> {row["料金"]}</p>'
        
        # 収容人数情報（防災モード）
        if '収容人数' in row:
            popup_html += f'<p style="margin: 5px 0;"><b>👥 収容人数:</b> {row["収容人数"]}名</p>'
        if '状態' in row:
            status_color = 'green' if row['状態'] == '開設中' else 'orange'
            popup_html += f'<p style="margin: 5px 0;"><b>🚨 状態:</b> <span style="color: {status_color};">{row["状態"]}</span></p>'
        
        popup_html += "</div>"
        
        # マーカーの色を選択されたスポットで変更
        marker_color = 'green' if selected_spot == row['スポット名'] else 'blue'
        
        folium.Marker(
            [row['緯度'], row['経度']],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=row['スポット名'],
            icon=folium.Icon(color=marker_color, icon='info-sign')
        ).add_to(m)
        
        # 選択されたスポットへのルート（直線）を表示
        if show_route and selected_spot == row['スポット名']:
            folium.PolyLine(
                locations=[center_location, [row['緯度'], row['経度']]],
                color='red',
                weight=3,
                opacity=0.7,
                popup=f"直線距離: {distance:.2f} km"
            ).add_to(m)
    
    return m

# Google Mapsリンク生成関数
def create_google_maps_link(origin, destination, mode='driving'):
    """Google Mapsの外部リンクを生成"""
    modes = {
        'driving': 'driving',
        'walking': 'walking',
        'bicycling': 'bicycling',
        'transit': 'transit'
    }
    base_url = "https://www.google.com/maps/dir/?api=1"
    link = f"{base_url}&origin={origin[0]},{origin[1]}&destination={destination[0]},{destination[1]}&travelmode={modes[mode]}"
    return link

# サイドバー
with st.sidebar:
    st.title("🗺️ 日田ナビ")
    st.caption("APIキー不要版")
    
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
    
    # 現在地設定
    st.subheader("📍 現在地設定")
    
    # プリセット位置
    preset_locations = {
        '日田市中心部': [33.3219, 130.9414],
        '豆田町': [33.3219, 130.9414],
        '日田駅': [33.3205, 130.9407],
        '天ヶ瀬温泉': [33.2967, 130.9167]
    }
    
    preset = st.selectbox(
        "プリセット位置から選択",
        ['カスタム'] + list(preset_locations.keys())
    )
    
    if preset != 'カスタム':
        st.session_state.current_location = preset_locations[preset]
    
    col1, col2 = st.columns(2)
    with col1:
        current_lat = st.number_input(
            "緯度",
            value=st.session_state.current_location[0],
            format="%.6f",
            key='lat_input'
        )
    with col2:
        current_lng = st.number_input(
            "経度",
            value=st.session_state.current_location[1],
            format="%.6f",
            key='lng_input'
        )
    
    if st.button("📍 位置を更新", use_container_width=True):
        st.session_state.current_location = [current_lat, current_lng]
        st.success("✅ 位置を更新しました")
        st.rerun()
    
    st.divider()
    
    # 天気情報
    st.subheader("🌤️ 現在の天気")
    st.info("☀️ 日田市: 晴れ 23°C")
    st.caption(f"更新: {datetime.now().strftime('%Y/%m/%d %H:%M')}")
    
    st.divider()
    
    # 統計情報
    if st.session_state.mode == '観光モード':
        st.metric("登録スポット数", "6箇所")
    else:
        st.metric("避難所数", "5箇所")
        st.metric("開設中", "3箇所", delta="安全")

# メインコンテンツ
st.title(f"📍 {st.session_state.mode}")

# データ読み込み
tourism_df, disaster_df = load_spots_data()

# モードに応じた表示
if st.session_state.mode == '観光モード':
    tab1, tab2, tab3, tab4 = st.tabs(["🗺️ マップ", "📋 スポット一覧", "📅 イベント", "💡 おすすめプラン"])
    
    with tab1:
        st.subheader("🗺️ 観光マップ")
        
        col_map, col_control = st.columns([3, 1])
        
        with col_control:
            st.markdown("### 🎯 目的地選択")
            
            # カテゴリーフィルター
            categories = ['すべて'] + sorted(tourism_df['カテゴリー'].unique().tolist())
            selected_category = st.selectbox("カテゴリー", categories)
            
            # フィルター適用
            if selected_category != 'すべて':
                filtered_df = tourism_df[tourism_df['カテゴリー'] == selected_category]
            else:
                filtered_df = tourism_df
            
            # 目的地選択
            destination = st.selectbox(
                "行きたい場所",
                ['選択してください'] + filtered_df['スポット名'].tolist(),
                key='destination_select'
            )
            
            if destination != '選択してください':
                dest_row = filtered_df[filtered_df['スポット名'] == destination].iloc[0]
                dest_coords = (dest_row['緯度'], dest_row['経度'])
                
                # 情報表示
                st.info(f"📍 **{destination}**")
                
                # 距離表示
                distance = calculate_distance(
                    st.session_state.current_location[0],
                    st.session_state.current_location[1],
                    dest_coords[0],
                    dest_coords[1]
                )
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("直線距離", f"{distance:.2f} km")
                with col_b:
                    # 徒歩時間の概算（時速4km）
                    walk_time = int((distance / 4) * 60)
                    st.metric("徒歩概算", f"{walk_time}分")
                
                # 詳細情報
                with st.expander("📝 詳細情報", expanded=True):
                    st.write(f"**説明:** {dest_row['説明']}")
                    st.write(f"**カテゴリー:** {dest_row['カテゴリー']}")
                    st.write(f"**営業時間:** {dest_row['営業時間']}")
                    st.write(f"**料金:** {dest_row['料金']}")
                
                st.markdown("---")
                st.markdown("### 🚗 ルート案内")
                
                # 移動手段選択
                travel_mode = st.selectbox(
                    "移動手段",
                    ["driving", "walking", "bicycling", "transit"],
                    format_func=lambda x: {
                        'driving': '🚗 車',
                        'walking': '🚶 徒歩',
                        'bicycling': '🚲 自転車',
                        'transit': '🚌 公共交通'
                    }[x]
                )
                
                # Google Mapsで開くボタン
                maps_link = create_google_maps_link(
                    st.session_state.current_location,
                    dest_coords,
                    travel_mode
                )
                
                st.link_button(
                    "🗺️ Google Mapsでルートを見る",
                    maps_link,
                    use_container_width=True,
                    type="primary"
                )
                
                # 地図上に直線ルートを表示
                show_route = st.checkbox("地図上に直線を表示", value=True)
            else:
                destination = None
                show_route = False
        
        with col_map:
            # 地図表示
            m = create_enhanced_map(
                tourism_df,
                st.session_state.current_location,
                selected_spot=destination if destination != '選択してください' else None,
                show_route=show_route
            )
            st_folium(m, width=700, height=600, key='tourism_map')
    
    with tab2:
        st.subheader("📋 スポット一覧")
        
        # 検索とフィルター
        col1, col2 = st.columns([2, 1])
        with col1:
            search = st.text_input("🔍 スポット名で検索", placeholder="例: 温泉")
        with col2:
            sort_by = st.selectbox("並び替え", ["番号順", "距離が近い順", "名前順"])
        
        # データフィルタリング
        display_df = tourism_df.copy()
        
        if search:
            display_df = display_df[
                display_df['スポット名'].str.contains(search, na=False) |
                display_df['説明'].str.contains(search, na=False)
            ]
        
        # 距離を計算
        display_df['距離'] = display_df.apply(
            lambda row: calculate_distance(
                st.session_state.current_location[0],
                st.session_state.current_location[1],
                row['緯度'],
                row['経度']
            ),
            axis=1
        )
        
        # 並び替え
        if sort_by == "距離が近い順":
            display_df = display_df.sort_values('距離')
        elif sort_by == "名前順":
            display_df = display_df.sort_values('スポット名')
        
        st.write(f"**表示件数:** {len(display_df)}件")
        
        # カード表示
        for idx, row in display_df.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"### {row['スポット名']}")
                    st.write(f"📝 {row['説明']}")
                    st.caption(f"🏷️ {row['カテゴリー']} | 🕐 {row['営業時間']} | 💰 {row['料金']}")
                
                with col2:
                    st.metric("距離", f"{row['距離']:.2f}km")
                
                with col3:
                    maps_link = create_google_maps_link(
                        st.session_state.current_location,
                        (row['緯度'], row['経度']),
                        'driving'
                    )
                    st.link_button("🗺️", maps_link, use_container_width=True)
                
                st.divider()
    
    with tab3:
        st.subheader("📅 年間イベントカレンダー")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            selected_month = st.selectbox(
                "月を選択",
                list(range(1, 13)),
                index=datetime.now().month - 1,
                format_func=lambda x: f"{x}月"
            )
        
        # サンプルイベントデータ
        events = {
            5: [("日田川開き観光祭", "5月20日-21日", "花火大会と伝統行事")],
            7: [("祇園祭", "7月20日-21日", "300年の歴史を持つ祭り")],
            10: [("日田天領まつり", "10月中旬", "時代行列と郷土芸能")],
            11: [("天ヶ瀬温泉もみじ祭り", "11月中旬", "紅葉の名所でのイベント")]
        }
        
        if selected_month in events:
            for event_name, event_date, event_desc in events[selected_month]:
                with st.container():
                    st.markdown(f"### 🎉 {event_name}")
                    st.write(f"📅 **開催日:** {event_date}")
                    st.write(f"📝 **内容:** {event_desc}")
                    st.divider()
        else:
            st.info(f"{selected_month}月には現在登録されているイベントはありません")
    
    with tab4:
        st.subheader("💡 おすすめプラン提案")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            plan_type = st.selectbox(
                "👥 プランタイプ",
                ["家族向け", "一人旅向け", "カップル向け", "グループ向け"]
            )
        with col2:
            budget = st.selectbox(
                "💰 予算",
                ["0～5,000円", "5,001～10,000円", "10,001～30,000円", "30,000円以上"]
            )
        with col3:
            duration = st.selectbox(
                "⏱️ 滞在時間",
                ["半日（3-4時間）", "1日（6-8時間）", "1泊2日", "2泊3日"]
            )
        
        if st.button("🎯 プランを提案", type="primary", use_container_width=True):
            st.success(f"✅ {plan_type} {budget} {duration}のプランを提案します")
            
            # サンプルプラン
            st.markdown("### 📋 提案されたプラン")
            
            plan_spots = tourism_df.sample(min(3, len(tourism_df)))
            
            for i, (idx, spot) in enumerate(plan_spots.iterrows(), 1):
                with st.expander(f"スポット{i}: {spot['スポット名']}", expanded=True):
                    col_a, col_b = st.columns([2, 1])
                    with col_a:
                        st.write(f"**説明:** {spot['説明']}")
                        st.write(f"**料金:** {spot['料金']}")
                        st.write(f"**おすすめ滞在時間:** 1-2時間")
                    with col_b:
                        maps_link = create_google_maps_link(
                            st.session_state.current_location,
                            (spot['緯度'], spot['経度']),
                            'driving'
                        )
                        st.link_button("🗺️ ルートを見る", maps_link, use_container_width=True)

else:  # 防災モード
    tab1, tab2, tab3 = st.tabs(["🏥 避難所マップ", "🗾 ハザードマップ", "📢 防災情報"])
    
    with tab1:
        st.subheader("🏥 避難所マップ")
        
        col_map, col_control = st.columns([3, 1])
        
        with col_control:
            st.markdown("### 🚨 避難所情報")
            
            # 状態フィルター
            status_filter = st.radio(
                "表示する避難所",
                ["すべて", "開設中のみ", "待機中のみ"]
            )
            
            # フィルター適用
            if status_filter == "開設中のみ":
                filtered_df = disaster_df[disaster_df['状態'] == '開設中']
            elif status_filter == "待機中のみ":
                filtered_df = disaster_df[disaster_df['状態'] == '待機中']
            else:
                filtered_df = disaster_df
            
            # 避難所選択
            shelter = st.selectbox(
                "避難所を選択",
                ['選択してください'] + filtered_df['スポット名'].tolist()
            )
            
            if shelter != '選択してください':
                shelter_row = filtered_df[filtered_df['スポット名'] == shelter].iloc[0]
                shelter_coords = (shelter_row['緯度'], shelter_row['経度'])
                
                # 情報表示
                st.warning(f"🏥 **{shelter}**")
                
                # 距離表示
                distance = calculate_distance(
                    st.session_state.current_location[0],
                    st.session_state.current_location[1],
                    shelter_coords[0],
                    shelter_coords[1]
                )
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("距離", f"{distance:.2f} km")
                with col_b:
                    walk_time = int((distance / 4) * 60)
                    st.metric("徒歩", f"{walk_time}分")
                
                # 詳細情報
                with st.expander("📊 詳細情報", expanded=True):
                    st.write(f"**収容人数:** {shelter_row['収容人数']}名")
                    st.write(f"**状態:** {shelter_row['状態']}")
                    st.write(f"**説明:** {shelter_row['説明']}")
                
                # Google Mapsで開く
                maps_link = create_google_maps_link(
                    st.session_state.current_location,
                    shelter_coords,
                    'walking'
                )
                
                st.link_button(
                    "🚶 徒歩ルートを見る（Google Maps）",
                    maps_link,
                    use_container_width=True,
                    type="primary"
                )
                
                show_route = st.checkbox("地図上に直線を表示", value=True)
            else:
                shelter = None
                show_route = False
        
        with col_map:
            # 地図表示
            m = create_enhanced_map(
                filtered_df,
                st.session_state.current_location,
                selected_spot=shelter if shelter != '選択してください' else None,
                show_route=show_route
            )
            st_folium(m, width=700, height=600, key='disaster_map')
    
    with tab2:
        st.subheader("🗾 ハザードマップ")
        
        hazard_type = st.selectbox(
            "ハザードマップの種類",
            ["洪水", "土砂災害", "地震", "津波"]
        )
        
        st.info(f"📍 {hazard_type}のハザードマップ情報")
        
        # プレースホルダー
        st.warning("⚠️ ハザードマップの画像データは別途準備が必要です")
        
        st.markdown("""
        ### 📌 確認事項
        - 最寄りの避難所を事前に確認
        - 避難経路を複数確認
        - 非常持ち出し袋の準備
        - 家族との連絡方法を決めておく
        """)
    
    with tab3:
        st.subheader("📢 防災情報")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🏪 営業中の店舗")
            
            stores = [
                ("ファミリーマート日田店", "✅ 営業中", "green"),
                ("ローソン日田中央店", "✅ 営業中", "green"),
                ("セブンイレブン日田店", "⚠️ 確認中", "orange"),
                ("マックスバリュ日田店", "✅ 営業中", "green")
            ]
            
            for store_name, status, color in stores:
                st.markdown(f":{color}[{status}] {store_name}")
        
        with col2:
            st.markdown("### 🥤 近くの自動販売機")
            st.info("現在地から500m圏内: 8台")
            st.success("すべて稼働中")
        
        st.divider()
        
        st.markdown("### 🎒 予算別防災グッズ提案")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            disaster_budget = st.selectbox(
                "予算を選択",
                ["3,000円以下", "3,000～10,000円", "10,000円以上"]
            )
        
        if st.button("💡 おすすめグッズを表示", use_container_width=True):
            st.success(f"✅ {disaster_budget}のおすすめ防災グッズ")
            
            if disaster_budget == "3,000円以下":
                items = [
                    "🔦 懐中電灯（LED）- 500円",
                    "🍫 非常食（3日分）- 1,500円",
                    "💧 保存水（2L×6本）- 800円"
                ]
            elif disaster_budget == "3,000～10,000円":
                items = [
                    "🎒 防災リュックセット - 5,000円",
                    "📻 手回し充電ラジオ - 2,500円",
                    "🏕️ 簡易トイレセット - 1,500円"
                ]
            else:
                items = [
                    "🏕️ テント・寝袋セット - 15,000円",
                    "🔋 大容量ポータブル電源 - 30,000円",
                    "🚰 浄水器 - 8,000円",
                    "🍱 長期保存食セット（1ヶ月分）- 12,000円"
                ]
            
            for item in items:
                st.write(f"• {item}")
        
        st.divider()
        
        # 緊急連絡先
        st.markdown("### 📞 緊急連絡先")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.error("**🚒 消防・救急**")
            st.markdown("### 119")
        with col2:
            st.info("**🚓 警察**")
            st.markdown("### 110")
        with col3:
            st.warning("**🏛️ 日田市役所**")
            st.markdown("### 0973-22-8888")

# フッター
st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    st.caption("© 2025 日田ナビ（Hita Navi）")
with col2:
    st.caption("📧 お問い合わせ")
with col3:
    st.caption("🔒 プライバシーポリシー")

# 使い方ヒント
with st.expander("💡 使い方のヒント"):
    st.markdown("""
    ### 📖 日田ナビの使い方
    
    #### 観光モードでできること
    1. **地図でスポットを確認**: マップタブで日田市内の観光スポットを一覧表示
    2. **目的地を選択**: 行きたい場所を選ぶと、距離と概算時間を表示
    3. **ルート案内**: 「Google Mapsでルートを見る」ボタンで実際の道路に沿ったナビゲーション
    4. **スポット検索**: スポット一覧タブでキーワード検索や並び替えが可能
    5. **イベント情報**: 月別にイベントを確認できます
    6. **プラン提案**: 予算や滞在時間に合わせたおすすめプランを提案
    
    #### 防災モードでできること
    1. **最寄り避難所の確認**: 現在地から近い避難所を表示
    2. **避難ルート**: 徒歩での避難ルートをGoogle Mapsで確認
    3. **開設状況の確認**: 避難所の開設状況と収容人数をリアルタイム表示
    4. **営業店舗情報**: 災害時の営業中コンビニ・スーパーを確認
    5. **防災グッズ提案**: 予算に応じた防災グッズのおすすめ
    
    #### 便利な機能
    - **現在地の設定**: サイドバーから緯度・経度を入力、またはプリセット位置から選択
    - **カテゴリーフィルター**: 観光地、温泉、歴史など、カテゴリー別に絞り込み
    - **距離表示**: すべてのスポットに現在地からの距離を表示
    - **直線表示**: 地図上で現在地から目的地への直線を表示可能
    
    #### Google Maps連携について
    - 実際の道路に沿ったルート案内は、「Google Mapsでルートを見る」ボタンから外部アプリで確認できます
    - 移動手段（車・徒歩・自転車・公共交通）を選択してからボタンを押してください
    - スマートフォンではGoogle Mapsアプリが自動的に開きます
    """)

# デバッグ情報（開発時のみ表示）
if st.checkbox("🔧 デバッグ情報を表示", value=False):
    st.json({
        "現在地": st.session_state.current_location,
        "モード": st.session_state.mode,
        "言語": st.session_state.language
    })