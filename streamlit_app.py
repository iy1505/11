import streamlit as st
import pandas as pd
import folium
import streamlit.components.v1 as components
from streamlit_folium import st_folium
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
from typing import List, Tuple
from gps_component import gps_locator  # GPS機能をインポート

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# ページ設定
st.set_page_config(
    page_title="日田なび",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# セッション状態の初期化
if 'mode' not in st.session_state:
    st.session_state.mode = '観光モード'
if 'current_location' not in st.session_state:
    st.session_state.current_location = [33.3219, 130.9414]
if 'selected_spots' not in st.session_state:
    st.session_state.selected_spots = []
if 'optimized_route' not in st.session_state:
    st.session_state.optimized_route = None
if 'map_optimized_route' not in st.session_state:
    st.session_state.map_optimized_route = None
if 'disaster_optimized_route' not in st.session_state:
    st.session_state.disaster_optimized_route = None
if 'gemini_api_key' not in st.session_state:
    st.session_state.gemini_api_key = ""

# データ読み込み関数
@st.cache_data
def load_spots_data():
    """Excelファイルからスポットデータを読み込む"""
    try:
        # Excelファイルから読み込み
        tourism_df = pd.read_excel('spots.xlsx', sheet_name='観光')
        disaster_df = pd.read_excel('spots.xlsx', sheet_name='防災')
        
        # カラム名の確認と標準化
        required_cols_tourism = ['No', 'スポット名', '緯度', '経度', '説明']
        required_cols_disaster = ['No', 'スポット名', '緯度', '経度', '説明']
        
        # 必須カラムの確認
        for col in required_cols_tourism:
            if col not in tourism_df.columns:
                st.error(f"❌ 観光シートに'{col}'カラムがありません")
                return None, None
        
        for col in required_cols_disaster:
            if col not in disaster_df.columns:
                st.error(f"❌ 防災シートに'{col}'カラムがありません")
                return None, None
        
        # 所要時間の変換処理（「60分」→60のような変換）
        def parse_time(value):
            """所要時間の値を数値に変換"""
            if pd.isna(value) or value == '-':
                return 60  # デフォルト値
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str):
                # 「60分」のような文字列から数値を抽出
                import re
                match = re.search(r'(\d+)', str(value))
                if match:
                    return int(match.group(1))
            return 60  # パースできない場合はデフォルト値
        
        # 観光データの処理
        if '所要時間（参考）' in tourism_df.columns:
            tourism_df['所要時間（参考）'] = tourism_df['所要時間（参考）'].apply(parse_time)
        else:
            tourism_df['所要時間（参考）'] = 60  # デフォルト60分
            
        if 'カテゴリ' not in tourism_df.columns:
            tourism_df['カテゴリ'] = '観光地'
        if '営業時間' not in tourism_df.columns:
            tourism_df['営業時間'] = '終日'
        if '料金' not in tourism_df.columns:
            tourism_df['料金'] = '無料'
        if '待ち時間（分）' not in tourism_df.columns:
            tourism_df['待ち時間（分）'] = 0
        if '混雑状況' not in tourism_df.columns:
            tourism_df['混雑状況'] = '空いている'
        
        # 防災データの処理
        if '所要時間（参考）' in disaster_df.columns:
            disaster_df['所要時間（参考）'] = disaster_df['所要時間（参考）'].apply(parse_time)
            
        if '収容人数' not in disaster_df.columns:
            disaster_df['収容人数'] = 0
        if '状態' not in disaster_df.columns:
            disaster_df['状態'] = '待機中'
        
        # 待ち時間と収容人数を数値型に変換
        tourism_df['待ち時間（分）'] = pd.to_numeric(tourism_df['待ち時間（分）'], errors='coerce').fillna(0).astype(int)
        disaster_df['収容人数'] = pd.to_numeric(disaster_df['収容人数'], errors='coerce').fillna(0).astype(int)
        
        return tourism_df, disaster_df
        
    except FileNotFoundError:
        st.warning("⚠️ spots.xlsxが見つかりません。サンプルデータを使用します。")
        
        # サンプルデータを作成
        tourism_df = pd.DataFrame({
            'No': [1, 2, 3, 4, 5, 6],
            'スポット名': ['豆田町', '日田温泉', '咸宜園', '天ヶ瀬温泉', '小鹿田焼の里', '大山ダム'],
            '緯度': [33.3219, 33.3200, 33.3240, 33.2967, 33.3500, 33.3800],
            '経度': [130.9414, 130.9400, 130.9430, 130.9167, 130.9600, 130.9200],
            '所要時間（参考）': [60, 120, 45, 90, 75, 30],
            '説明': ['江戸時代の町並みが残る歴史的な地区', '日田の名湯・温泉施設',
                   '日本最大の私塾跡・歴史的教育施設', '自然豊かな温泉街',
                   '伝統工芸の陶器の里', '美しい景観のダム'],
            'カテゴリ': ['歴史', 'グルメ', '歴史', '自然', '体験', '自然'],
            '営業時間': ['終日', '9:00-21:00', '9:00-17:00', '終日', '9:00-17:00', '終日'],
            '料金': ['無料', '500円', '300円', '無料', '無料', '無料'],
            '待ち時間（分）': [0, 15, 0, 10, 5, 0],
            '混雑状況': ['空いている', '混雑', '普通', '空いている', '空いている', '空いている']
        })
        disaster_df = pd.DataFrame({
            'No': [1, 2, 3, 4, 5],
            'スポット名': ['日田市役所（避難所）', '中央公民館', '総合体育館', '桂林公民館', '三花公民館'],
            '緯度': [33.3219, 33.3250, 33.3180, 33.3300, 33.3100],
            '経度': [130.9414, 130.9450, 130.9380, 130.9500, 130.9350],
            '所要時間（参考）': [60, 60, 60, 60, 60],
            '説明': ['市役所・第一避難所', '中央地区の避難所', '大規模避難所', 
                   '桂林地区の避難所', '三花地区の避難所'],
            '収容人数': [500, 300, 800, 200, 250],
            '状態': ['開設中', '開設中', '開設中', '待機中', '待機中']
        })
        return tourism_df, disaster_df
    
    except Exception as e:
        st.error(f"❌ Excelファイルの読み込みエラー: {e}")
        return None, None

# 距離計算関数
def calculate_distance(lat1, lng1, lat2, lng2):
    """2点間の距離を計算（km）- ヒュベニの公式"""
    R = 6371  # 地球の半径（km）

    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lng = radians(lng2 - lng1)

    a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    return R * c

# 最適化経路算出関数（観光モード：待ち時間考慮）
def optimize_route_tourism(current_loc: List[float], spots_df: pd.DataFrame, selected_indices: List[int]) -> Tuple[List[int], float, float]:
    """
    観光モード用の最適化経路算出（待ち時間と距離を考慮）
    Returns: (訪問順のインデックスリスト, 総移動距離, 総所要時間)
    """
    if not selected_indices:
        return [], 0.0, 0.0

    unvisited = selected_indices.copy()
    route = []
    current_position = current_loc
    total_distance = 0.0
    total_time = 0.0

    while unvisited:
        # 各未訪問スポットのスコアを計算
        scores = []
        distances = []
        wait_times = []

        for idx in unvisited:
            spot = spots_df.iloc[idx]
            dist = calculate_distance(
                current_position[0], current_position[1],
                spot['緯度'], spot['経度']
            )
            distances.append(dist)
            wait_time = spot.get('待ち時間（分）', 0)
            wait_times.append(wait_time)

        # 距離ランキング（近い順に1, 2, 3...）
        distance_ranks = [sorted(distances).index(d) + 1 for d in distances]

        # 待ち時間ランキング（短い順に1, 2, 3...）
        wait_time_ranks = [sorted(wait_times).index(w) + 1 for w in wait_times]

        # スコア計算: S = RD + RW（小さいほど良い）
        scores = [distance_ranks[i] + wait_time_ranks[i] for i in range(len(unvisited))]

        # 最小スコアのスポットを選択
        min_score_idx = scores.index(min(scores))
        selected_idx = unvisited[min_score_idx]

        route.append(selected_idx)
        selected_spot = spots_df.iloc[selected_idx]

        # 移動距離と時間を加算
        travel_dist = distances[min_score_idx]
        total_distance += travel_dist
        total_time += (travel_dist / 40) * 60  # 時速40kmで計算（分）
        total_time += selected_spot.get('所要時間（参考）', 60)
        total_time += selected_spot.get('待ち時間（分）', 0)

        # 現在地を更新
        current_position = [selected_spot['緯度'], selected_spot['経度']]
        unvisited.remove(selected_idx)

    return route, total_distance, total_time

# 最適化経路算出関数（防災モード：最近傍法）
def optimize_route_disaster(current_loc: List[float], spots_df: pd.DataFrame, selected_indices: List[int]) -> Tuple[List[int], float, float]:
    """
    防災モード用の最適化経路算出（距離のみ考慮）
    Returns: (訪問順のインデックスリスト, 総移動距離, 総所要時間)
    """
    if not selected_indices:
        return [], 0.0, 0.0

    unvisited = selected_indices.copy()
    route = []
    current_position = current_loc
    total_distance = 0.0
    total_time = 0.0

    while unvisited:
        # 最も近いスポットを選択
        min_dist = float('inf')
        nearest_idx = None

        for idx in unvisited:
            spot = spots_df.iloc[idx]
            dist = calculate_distance(
                current_position[0], current_position[1],
                spot['緯度'], spot['経度']
            )
            if dist < min_dist:
                min_dist = dist
                nearest_idx = idx

        route.append(nearest_idx)
        selected_spot = spots_df.iloc[nearest_idx]

        # 移動距離と時間を加算
        total_distance += min_dist
        total_time += (min_dist / 4) * 60  # 徒歩時速4kmで計算（分）

        # 現在地を更新
        current_position = [selected_spot['緯度'], selected_spot['経度']]
        unvisited.remove(nearest_idx)

    return route, total_distance, total_time

# 地図作成関数（改良版）
def create_enhanced_map(spots_df, center_location, selected_spot=None, show_route=False, selected_spots_list=None):
    """Foliumマップを作成
    
    Args:
        spots_df: スポットデータフレーム
        center_location: 現在地の座標
        selected_spot: 単一選択時の選択されたスポット名
        show_route: ルート表示フラグ
        selected_spots_list: 複数選択時の選択されたスポット名のリスト
    """
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
        
        # カテゴリ情報（観光モード）
        if 'カテゴリ' in row:
            popup_html += f'<p style="margin: 5px 0;"><b>🏷️ カテゴリ:</b> {row["カテゴリ"]}</p>'
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
        
        # マーカーの色を決定
        # 複数選択モードの場合は、selected_spots_listに含まれるスポットを赤色に
        if selected_spots_list and row['スポット名'] in selected_spots_list:
            marker_color = 'red'
        # 単一選択モードの場合は、選択されたスポットを緑色に
        elif selected_spot == row['スポット名']:
            marker_color = 'green'
        else:
            marker_color = 'blue'
        
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

# Google Mapsリンク生成関数（単一目的地）
def create_google_maps_link(origin, destination, mode='driving'):
    """Google Mapsの外部リンクを生成（単一目的地）"""
    modes = {
        'driving': 'driving',
        'walking': 'walking',
        'bicycling': 'bicycling',
        'transit': 'transit'
    }
    base_url = "https://www.google.com/maps/dir/?api=1"
    link = f"{base_url}&origin={origin[0]},{origin[1]}&destination={destination[0]},{destination[1]}&travelmode={modes[mode]}"
    return link

# Google Mapsリンク生成関数（複数経由地）
def create_google_maps_multi_link(origin: List[float], waypoints: List[Tuple[float, float]], destination: Tuple[float, float], mode='driving') -> str:
    """
    Google Mapsの外部リンクを生成（複数経由地対応）
    Args:
        origin: 出発地 [緯度, 経度]
        waypoints: 経由地のリスト [(緯度, 経度), ...]
        destination: 最終目的地 (緯度, 経度)
        mode: 移動手段
    Returns:
        Google Maps URL
    """
    modes = {
        'driving': 'driving',
        'walking': 'walking',
        'bicycling': 'bicycling',
        'transit': 'transit'
    }

    base_url = "https://www.google.com/maps/dir/?api=1"
    url = f"{base_url}&origin={origin[0]},{origin[1]}&destination={destination[0]},{destination[1]}"

    if waypoints:
        waypoints_str = "|".join([f"{lat},{lng}" for lat, lng in waypoints])
        url += f"&waypoints={waypoints_str}"

    url += f"&travelmode={modes.get(mode, 'driving')}"

    return url


# サイドバー
with st.sidebar:
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
    
    # GPS座標をチェック（LocalStorageから）
    check_gps_html = """
    <script>
        const lat = localStorage.getItem('gps_lat');
        const lng = localStorage.getItem('gps_lng');
        
        if (lat && lng) {
            // Streamlitのクエリパラメータに設定
            const url = new URL(window.parent.location.href);
            url.searchParams.set('gps_lat', lat);
            url.searchParams.set('gps_lng', lng);
            
            // LocalStorageをクリア
            localStorage.removeItem('gps_lat');
            localStorage.removeItem('gps_lng');
            localStorage.removeItem('gps_timestamp');
            
            // URLを更新
            window.parent.history.replaceState({}, '', url);
            
            // ページをリロード
            window.parent.location.reload();
        }
    </script>
    """
    
    components.html(check_gps_html, height=0)
    
    # クエリパラメータから座標を取得
    query_params = st.query_params
    
    if 'gps_lat' in query_params and 'gps_lng' in query_params:
        try:
            new_lat = float(query_params['gps_lat'])
            new_lng = float(query_params['gps_lng'])
            
            # 現在地を更新
            old_location = st.session_state.current_location.copy()
            st.session_state.current_location = [new_lat, new_lng]
            
            # クエリパラメータをクリア
            st.query_params.clear()
            
            # 位置が変わった場合のみリロード
            if old_location[0] != new_lat or old_location[1] != new_lng:
                st.success("✅ GPS位置を反映しました！")
                st.write(f"📍 緯度: {new_lat:.6f}")
                st.write(f"📍 経度: {new_lng:.6f}")
                st.rerun()
        except Exception as e:
            st.error(f"エラー: {e}")
    
    # GPS取得コンポーネント
    gps_locator()
    
    # 現在の位置を表示
    st.info(f"📍 現在地\n緯度: {st.session_state.current_location[0]:.6f}\n経度: {st.session_state.current_location[1]:.6f}")
    
    st.divider()
    
    # 天気情報（シンプル版 - APIキー不要）
    st.subheader("🌤️ 天気情報")
    
    # 現在の日時から天気アイコンを選択（サンプル）
    hour = datetime.now().hour
    if 6 <= hour < 18:
        weather_icon = "☀️"
        weather_text = "晴れ"
    else:
        weather_icon = "🌙"
        weather_text = "夜間"
    
    st.markdown(f"### {weather_icon} {weather_text}")
    
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        st.metric("気温", "23°C")
    with col_w2:
        st.metric("湿度", "65%")
    
    # 外部天気サイトへのリンク
    with st.expander("🔗 詳細な天気情報"):
        # 気象庁
        jma_url = "https://www.jma.go.jp/bosai/forecast/#area_type=class20s&area_code=4410200"
        st.link_button(
            "📊 気象庁（日田市）",
            jma_url,
            use_container_width=True
        )
        
        # Yahoo天気
        yahoo_weather_url = "https://weather.yahoo.co.jp/weather/jp/44/8330/44204.html"
        st.link_button(
            "🌐 Yahoo!天気",
            yahoo_weather_url,
            use_container_width=True
        )
    
    st.caption(f"表示: {datetime.now().strftime('%Y/%m/%d %H:%M')}")
    
    st.divider()
    
    # 統計情報
    if st.session_state.mode == '観光モード':
        st.metric("登録スポット数", "49箇所")
    else:
        st.metric("避難所数", "122箇所")
        st.metric("開設中", "3箇所", delta="安全")

# メインコンテンツ
# ページトップのタイトル
st.title("🗺️ 日田なび")
st.caption("Ver. 1.2 - 観光と防災におけるタイムパフォーマンスを向上")
st.divider()

# データ読み込み
tourism_df, disaster_df = load_spots_data()

# 現在のモード表示
st.subheader(f"📍 {st.session_state.mode}")

# モードに応じた表示
if st.session_state.mode == '観光モード':
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🗺️ マップ",
        "📋 スポット一覧",
        "📅 イベント",
        "⭐ おすすめスポット",
        "🤖 AIプラン提案"
    ])
    
    with tab1:
        st.subheader("🗺️ 観光マップ")
        
        col_map, col_control = st.columns([3, 1])
        
        with col_control:
            st.markdown("### 🎯 目的地選択")

            # カテゴリーフィルター
            categories = ['すべて'] + sorted(tourism_df['カテゴリ'].unique().tolist())
            selected_category = st.selectbox("カテゴリー", categories, key='map_category')

            # フィルター適用
            if selected_category != 'すべて':
                filtered_df = tourism_df[tourism_df['カテゴリ'] == selected_category]
            else:
                filtered_df = tourism_df

            # 複数スポット選択（0個以上選択可能）
            selected_spots_names = st.multiselect(
                "訪問したいスポットを選択",
                filtered_df['スポット名'].tolist(),
                default=[],
                key='map_multi_select',
                help="1つだけ選択した場合は単一ルート、2つ以上選択した場合は最適化ルートを表示します"
            )

            # 選択数に応じた処理
            if len(selected_spots_names) == 0:
                # スポット未選択
                st.info("↑ 訪問したいスポットを選択してください")
                show_route = False
                
            elif len(selected_spots_names) == 1:
                # 単一スポット選択モード
                destination = selected_spots_names[0]
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
                    st.write(f"**カテゴリー:** {dest_row['カテゴリ']}")
                    st.write(f"**営業時間:** {dest_row['営業時間']}")
                    st.write(f"**料金:** {dest_row['料金']}")
                    st.write(f"**所要時間（参考）:** {dest_row['所要時間（参考）']}分")
                    st.write(f"**待ち時間:** {dest_row['待ち時間（分）']}分")
                    st.write(f"**混雑状況:** {dest_row['混雑状況']}")

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
                    }[x],
                    key='map_travel_mode'
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
                show_route = st.checkbox("地図上に直線を表示", value=True, key='map_show_route')
                
            else:
                # 複数スポット選択モード（2つ以上）
                destination = None
                show_route = False

                st.markdown("### 🎯 複数スポット選択中")
                st.success(f"✅ {len(selected_spots_names)}箇所のスポットを選択中")

                # 移動手段選択
                travel_mode_opt = st.selectbox(
                    "🚗 移動手段",
                    ["driving", "walking", "bicycling", "transit"],
                    format_func=lambda x: {
                        'driving': '🚗 車',
                        'walking': '🚶 徒歩',
                        'bicycling': '🚲 自転車',
                        'transit': '🚌 公共交通'
                    }[x],
                    key='map_opt_travel_mode'
                )

                if st.button("🎯 最適化ルートを算出", type="primary", use_container_width=True, key='map_optimize_btn'):
                    # 選択されたスポットのインデックスを取得
                    selected_indices = []
                    for spot_name in selected_spots_names:
                        idx = tourism_df[tourism_df['スポット名'] == spot_name].index[0]
                        selected_indices.append(idx)

                    # 最適化ルート算出
                    route, total_dist, total_time = optimize_route_tourism(
                        st.session_state.current_location,
                        tourism_df,
                        selected_indices
                    )

                    # セッション状態に保存
                    st.session_state.map_optimized_route = {
                        'route': route,
                        'total_distance': total_dist,
                        'total_time': total_time,
                        'mode': travel_mode_opt
                    }

                    st.success("✅ 最適化ルートを算出しました！")
                    st.rerun()

                # 最適化ルート表示
                if 'map_optimized_route' in st.session_state and st.session_state.map_optimized_route is not None:
                    route_data = st.session_state.map_optimized_route
                    route = route_data['route']
                    total_dist = route_data['total_distance']
                    total_time = route_data['total_time']

                    st.markdown("---")
                    st.markdown("### 📋 最適化された訪問順序")

                    # 統計情報
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("総移動距離", f"{total_dist:.2f} km")
                    with col2:
                        hours = int(total_time // 60)
                        minutes = int(total_time % 60)
                        st.metric("総所要時間", f"{hours}時間{minutes}分")

                    # 訪問順序リスト（簡易版）
                    with st.expander("📍 訪問順序を確認", expanded=False):
                        for i, idx in enumerate(route, 1):
                            spot = tourism_df.iloc[idx]
                            st.write(f"{i}. {spot['スポット名']}")

                    # Google Maps複数経由地リンク生成
                    if len(route) > 0:
                        origin = st.session_state.current_location

                        if len(route) == 1:
                            dest_spot = tourism_df.iloc[route[0]]
                            destination_coords = (dest_spot['緯度'], dest_spot['経度'])
                            waypoints = []
                        else:
                            waypoints = []
                            for idx in route[:-1]:
                                spot = tourism_df.iloc[idx]
                                waypoints.append((spot['緯度'], spot['経度']))

                            dest_spot = tourism_df.iloc[route[-1]]
                            destination_coords = (dest_spot['緯度'], dest_spot['経度'])

                        maps_url = create_google_maps_multi_link(
                            origin,
                            waypoints,
                            destination_coords,
                            route_data['mode']
                        )

                        st.link_button(
                            "🗺️ Google Mapで最適化ルートを開く",
                            maps_url,
                            use_container_width=True,
                            type="primary"
                        )
        
        with col_map:
            # 地図表示（カテゴリーフィルターを適用）
            # 選択されたスポットのリストを渡す
            m = create_enhanced_map(
                filtered_df,
                st.session_state.current_location,
                selected_spot=selected_spots_names[0] if len(selected_spots_names) == 1 else None,
                show_route=show_route if 'show_route' in locals() else False,
                selected_spots_list=selected_spots_names if len(selected_spots_names) > 0 else None
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
                    st.caption(f"🏷️ {row['カテゴリ']} | 🕐 {row['営業時間']} | 💰 {row['料金']}")
                
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
        
        # 日田市の年間イベントデータ
        events = {
            2: [("天領日田おひなまつり", "2月中旬～3月下旬", "豆田町一帯で雛人形を展示する春の風物詩")],
            3: [
                ("天領日田おひなまつり", "2月中旬～3月下旬", "豆田町一帯で雛人形を展示する春の風物詩"),
                ("おおやま梅まつり", "3月上旬～中旬", "約6,000本の梅が咲き誇る梅園での祭り")
            ],
            4: [("亀山公園桜まつり", "3月下旬～4月上旬", "約1,000本の桜が咲く日田市を代表する桜の名所")],
            5: [
                ("日田川開き観光祭", "5月第4土曜・日曜", "九州最大級の花火大会を含む日田最大の祭り"),
            ],
            6: [("あまがせの夏まつり", "6月下旬", "天ヶ瀬温泉街で開催される夏の祭り")],
            7: [("日田祇園祭", "7月第4土曜・日曜", "300年以上の歴史を持つユネスコ無形文化遺産の祭り")],
            8: [("天ヶ瀬おもてなし花火", "8月中旬", "天ヶ瀬温泉街で開催される花火大会")],
            9: [("日田市民音楽祭", "9月中旬", "日田市で開催される音楽イベント")],
            10: [
                ("日田天領まつり", "10月第3土曜・日曜", "西国筋郡代着任行列や時代絵巻パレードが見どころ"),
                ("千年あかり", "10月下旬～11月中旬", "豆田町と花月川周辺で竹灯籠を灯すイベント"),
                 ("小鹿田焼民陶祭", "5月第2土曜・日曜", "伝統工芸の小鹿田焼の窯元を巡るイベント")
            ],
            11: [
                ("千年あかり", "10月下旬～11月中旬", "豆田町と花月川周辺で竹灯籠を灯すイベント")
            ],
            12: [("大山ダム湖畔周遊ウォーキング", "12月上旬", "大山ダム周辺を歩くウォーキングイベント")]
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
        st.subheader("⭐ おすすめスポット")

        st.info("日田市の特におすすめの観光スポットをご紹介します")

        # おすすめスポットのリスト（年間を通したおすすめ）
        recommended_spots = [
            ("豆田町（重要伝統的建造物群保存地区）", "🔥 必見！", "江戸時代の風情が残る歴史的な町並み"),
            ("咸宜園跡（日本遺産）", "🗾 日本遺産", "日本最大の私塾跡・世界遺産"),
            ("三隈川（屋形船・鵜飼い）", "🚣 伝統", "屋形船で川下りと鵜飼い体験"),
            ("大山ダム（進撃の巨人像）", "🎬 人気", "進撃の巨人ファン必見のスポット"),
            ("慈恩の滝", "💧 絶景", "裏側から見られる美しい滝"),
            ("日田祇園山鉾会館", "🎉 文化", "日田祇園祭の山鉾を展示"),
            ("ひなの里（天領日田資料館）", "🏛️ 歴史", "天領時代の資料を展示"),
            ("亀山公園", "🌸 自然", "桜の名所として有名な公園"),
            ("日田市立博物館（AOSE内）", "🏛️ 学習", "日田の歴史と文化を学べる"),
            ("月隈公園", "🌳 散策", "市街地を一望できる公園")
        ]

        for i, (spot_name, badge, description) in enumerate(recommended_spots, 1):
            # スポット情報を取得
            spot_df = tourism_df[tourism_df['スポット名'] == spot_name]

            if len(spot_df) > 0:
                spot = spot_df.iloc[0]

                with st.container():
                    col_rank, col_info, col_action = st.columns([0.5, 3, 1])

                    with col_rank:
                        if i == 1:
                            st.markdown("## 🥇")
                        elif i == 2:
                            st.markdown("## 🥈")
                        elif i == 3:
                            st.markdown("## 🥉")
                        else:
                            st.markdown(f"## {i}")

                    with col_info:
                        st.markdown(f"### {spot_name} {badge}")
                        st.write(f"📝 {spot['説明']}")
                        st.caption(f"🏷️ {spot['カテゴリ']} | 💰 {spot['料金']} | ⏱️ 所要時間: {spot['所要時間（参考）']}分")

                    with col_action:
                        # 距離計算
                        distance = calculate_distance(
                            st.session_state.current_location[0],
                            st.session_state.current_location[1],
                            spot['緯度'],
                            spot['経度']
                        )
                        st.metric("距離", f"{distance:.1f}km")
                        maps_link = create_google_maps_link(
                            st.session_state.current_location,
                            (spot['緯度'], spot['経度']),
                            'driving'
                        )
                        st.link_button("🗺️", maps_link, use_container_width=True)

                    st.divider()

    with tab5:
        st.subheader("🤖 AIプラン提案（Gemini API）")

        st.info("Gemini AIがあなたの予算・時間・興味に合わせた最適な観光プランを提案します。")

        # APIキー入力
        st.markdown("### 🔑 APIキー設定")

        api_key_input = st.text_input(
            "Gemini APIキーを入力してください",
            type="password",
            value=st.session_state.gemini_api_key,
            help="APIキーはセッション中のみ保持され、サーバーには保存されません"
        )

        if api_key_input:
            st.session_state.gemini_api_key = api_key_input

        st.markdown("[🔑 Gemini APIキーを取得する →](https://aistudio.google.com/app/apikey)")

        st.divider()

        # プラン条件入力
        st.markdown("### 📝 プラン条件を入力")

        col1, col2 = st.columns(2)

        with col1:
            user_budget = st.text_input("💰 予算", placeholder="例: 5000円以内", key='ai_budget')
            user_duration = st.text_input("⏱️ 滞在時間", placeholder="例: 3時間", key='ai_duration')

        with col2:
            user_companion = st.selectbox(
                "👥 同行者",
                ["一人旅", "家族連れ", "カップル", "友人グループ"],
                key='ai_companion'
            )

        # 興味カテゴリー
        st.markdown("**🎯 興味のあるカテゴリー（複数選択可）:**")
        interest_categories = st.multiselect(
            "興味のあるカテゴリーを選択",
            ["歴史", "自然", "グルメ", "体験", "温泉", "文化"],
            default=["歴史"],
            key='ai_interests'
        )

        # その他の要望
        st.markdown("**💬 その他の要望（任意）:**")
        user_request = st.text_area(
            "自由に要望を入力してください",
            placeholder="例: 子供が楽しめるスポットを含めてほしい、写真映えする場所を優先してほしい、ランチは和食がいい、など",
            height=100,
            key='ai_request'
        )

        # プラン生成ボタン
        if st.button("🎯 AIプランを生成", type="primary", use_container_width=True):
            if not GENAI_AVAILABLE:
                st.error("❌ google-generativeai パッケージがインストールされていません。")
                st.info("以下のコマンドでインストールしてください: `pip install google-generativeai`")
            elif not st.session_state.gemini_api_key:
                st.error("❌ Gemini APIキーを入力してください")
            elif not user_budget or not user_duration:
                st.warning("⚠️ 予算と滞在時間を入力してください")
            else:
                try:
                    with st.spinner("🤖 AIがプランを生成中..."):
                        # Gemini API設定
                        genai.configure(api_key=st.session_state.gemini_api_key)
                        model = genai.GenerativeModel('gemini-2.0-flash-exp')

                        # スポットリスト作成
                        spots_context = []
                        for _, spot in tourism_df.iterrows():
                            spots_context.append(
                                f"- {spot['スポット名']}: {spot['説明']} (カテゴリ: {spot['カテゴリ']}, 料金: {spot['料金']}, 所要時間: {spot['所要時間（参考）']}分)"
                            )
                        spots_text = "\n".join(spots_context)

                        # 現在の日時と季節情報を取得
                        current_date = datetime.now()
                        month = current_date.month

                        # 季節判定
                        if month in [3, 4, 5]:
                            season = "春"
                            season_desc = "桜の季節で、温暖な気候"
                        elif month in [6, 7, 8]:
                            season = "夏"
                            season_desc = "暑い季節で、川開き観光祭や祇園祭などのイベントがある時期"
                        elif month in [9, 10, 11]:
                            season = "秋"
                            season_desc = "紅葉が美しく、天領まつりやもみじ祭りがある時期"
                        else:
                            season = "冬"
                            season_desc = "寒い季節で、温泉が特に人気"

                        # プロンプト作成
                        system_prompt = "あなたは日田市の観光コンシェルジュです。現在の天気・季節を考慮しながら、以下の観光スポットリストとユーザーの要望に基づき、魅力的な観光プランを提案してください。"

                        user_prompt = f"""
現在の日付: {current_date.strftime('%Y年%m月%d日')}
現在の季節: {season}（{season_desc}）

観光スポットリスト:
{spots_text}

ユーザーの要望:
- 予算: {user_budget}
- 滞在時間: {user_duration}
- 興味: {', '.join(interest_categories)}
- 同行者: {user_companion}
{f'- その他の要望: {user_request}' if user_request else ''}

上記の条件と現在の季節・天気を考慮して、日田市の観光プランを訪問順序を含めて具体的に提案してください。
各スポットの魅力や、なぜそのスポットを選んだのか、季節に合わせたおすすめポイントも簡潔に説明してください。
                        """

                        # API呼び出し
                        response = model.generate_content(f"{system_prompt}\n\n{user_prompt}")

                        # 結果表示
                        st.markdown("---")
                        st.markdown("### 📋 AI提案プラン")
                        st.markdown(response.text)

                        st.success("✅ プラン生成完了！")

                except Exception as e:
                    st.error(f"❌ エラーが発生しました: {str(e)}")
                    st.info("💡 APIキーが正しいか確認してください。また、Gemini APIが有効化されているか確認してください。")

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
                ["すべて", "開設中のみ", "待機中のみ"],
                key='disaster_status_filter'
            )

            # フィルター適用
            if status_filter == "開設中のみ":
                filtered_df = disaster_df[disaster_df['状態'] == '開設中']
            elif status_filter == "待機中のみ":
                filtered_df = disaster_df[disaster_df['状態'] == '待機中']
            else:
                filtered_df = disaster_df

            # 複数避難所選択（0個以上選択可能）
            selected_shelters_names = st.multiselect(
                "避難所を選択",
                filtered_df['スポット名'].tolist(),
                default=[],
                key='disaster_multi_select',
                help="1つだけ選択した場合は単一ルート、2つ以上選択した場合は最適化避難ルートを表示します"
            )

            # 選択数に応じた処理
            if len(selected_shelters_names) == 0:
                # 避難所未選択
                st.info("↑ 避難所を選択してください")
                show_route = False
                
            elif len(selected_shelters_names) == 1:
                # 単一避難所選択モード
                shelter = selected_shelters_names[0]
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

                show_route = st.checkbox("地図上に直線を表示", value=True, key='disaster_show_route')
                
            else:
                # 複数避難所選択モード（2つ以上）
                shelter = None
                show_route = False

                st.markdown("### 🎯 複数避難所選択中")
                st.success(f"✅ {len(selected_shelters_names)}箇所の避難所を選択中")

                if st.button("🎯 最適化避難ルートを算出", type="primary", use_container_width=True, key='disaster_optimize_btn'):
                    # 選択された避難所のインデックスを取得
                    selected_indices = []
                    for shelter_name in selected_shelters_names:
                        idx = disaster_df[disaster_df['スポット名'] == shelter_name].index[0]
                        selected_indices.append(idx)

                    # 最適化ルート算出（防災モード：最近傍法）
                    route, total_dist, total_time = optimize_route_disaster(
                        st.session_state.current_location,
                        disaster_df,
                        selected_indices
                    )

                    # セッション状態に保存
                    st.session_state.disaster_optimized_route = {
                        'route': route,
                        'total_distance': total_dist,
                        'total_time': total_time,
                        'mode': 'walking'
                    }

                    st.success("✅ 最適化避難ルートを算出しました！")
                    st.rerun()

                # 最適化ルート表示
                if 'disaster_optimized_route' in st.session_state and st.session_state.disaster_optimized_route is not None:
                    route_data = st.session_state.disaster_optimized_route
                    route = route_data['route']
                    total_dist = route_data['total_distance']
                    total_time = route_data['total_time']

                    st.markdown("---")
                    st.markdown("### 📋 最適化された避難順序")

                    # 統計情報
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("総移動距離", f"{total_dist:.2f} km")
                    with col2:
                        hours = int(total_time // 60)
                        minutes = int(total_time % 60)
                        st.metric("総所要時間", f"{hours}時間{minutes}分")

                    # 訪問順序リスト（簡易版）
                    with st.expander("📍 避難順序を確認", expanded=False):
                        for i, idx in enumerate(route, 1):
                            shelter_info = disaster_df.iloc[idx]
                            st.write(f"{i}. {shelter_info['スポット名']} (収容: {shelter_info['収容人数']}名)")

                    # Google Maps複数経由地リンク生成
                    if len(route) > 0:
                        origin = st.session_state.current_location

                        if len(route) == 1:
                            dest_shelter = disaster_df.iloc[route[0]]
                            destination_coords = (dest_shelter['緯度'], dest_shelter['経度'])
                            waypoints = []
                        else:
                            waypoints = []
                            for idx in route[:-1]:
                                shelter_info = disaster_df.iloc[idx]
                                waypoints.append((shelter_info['緯度'], shelter_info['経度']))

                            dest_shelter = disaster_df.iloc[route[-1]]
                            destination_coords = (dest_shelter['緯度'], dest_shelter['経度'])

                        maps_url = create_google_maps_multi_link(
                            origin,
                            waypoints,
                            destination_coords,
                            'walking'
                        )

                        st.link_button(
                            "🚶 Google Mapで最適化避難ルートを開く",
                            maps_url,
                            use_container_width=True,
                            type="primary"
                        )
        
        with col_map:
            # 地図表示
            # 選択された避難所のリストを渡す
            m = create_enhanced_map(
                filtered_df,
                st.session_state.current_location,
                selected_spot=selected_shelters_names[0] if len(selected_shelters_names) == 1 else None,
                show_route=show_route if 'show_route' in locals() else False,
                selected_spots_list=selected_shelters_names if len(selected_shelters_names) > 0 else None
            )
            st_folium(m, width=700, height=600, key='disaster_map')

    with tab2:
        st.subheader("🗾 ハザードマップ")

        st.info("日田市の公式ハザードマップで、災害時の危険箇所や避難場所を確認できます")

        st.markdown("""
        ### 📌 確認事項
        - 最寄りの避難所を事前に確認
        - 避難経路を複数確認
        - 非常持ち出し袋の準備
        - 家族との連絡方法を決めておく
        """)

        st.divider()

        st.markdown("### 🗾 日田市公式ハザードマップ")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 📍 洪水・土砂災害ハザードマップ")
            st.write("日田市の洪水・土砂災害の危険エリアを確認できます")
            st.link_button(
                "🗾 洪水・土砂災害ハザードマップを見る",
                "https://www.city.hita.oita.jp/soshiki/somubu/kikikanrishitu/kikikanri/anshin/bosai/Preparing_for_disaster/3317.html",
                use_container_width=True,
                type="primary"
            )

        with col2:
            st.markdown("#### 📍 地震ハザードマップ")
            st.write("日田市の地震による被害想定を確認できます")
            st.link_button(
                "🗾 地震ハザードマップを見る",
                "https://www.city.hita.oita.jp/soshiki/somubu/kikikanrishitu/kikikanri/anshin/bosai/Preparing_for_disaster/12441.html",
                use_container_width=True,
                type="primary"
            )

    with tab3:
        st.subheader("📢 防災情報")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🏪 営業中の店舗")
            
            stores = [
                ("ファミリーマート日田淡窓店", "✅ 営業中", "green"),
                ("ローソン日田中央一丁目店", "✅ 営業中", "green"),
                ("セブンイレブン日田三本松2丁目店", "⚠️ 確認中", "orange"),
            ]
            
            for store_name, status, color in stores:
                st.markdown(f":{color}[{status}] {store_name}")
        
        with col2:
            st.markdown("### 🥤 近くの自動販売機")
            st.info("現在地から500m圏内: 8台")
            st.success("すべて稼働中")
        
        st.divider()
        
        st.markdown("### 🎒 AI防災グッズ提案")

        st.info("💡 Gemini AIがあなたの予算や状況に合わせた最適な防災グッズを提案します")

        # 条件入力
        col1, col2 = st.columns(2)
        with col1:
            disaster_budget = st.selectbox(
                "💰 予算",
                ["3,000円以下", "3,000～10,000円", "10,000～30,000円", "30,000円以上"],
                key='disaster_budget_select'
            )
            
            household_size = st.selectbox(
                "👥 家族構成",
                ["一人暮らし", "二人暮らし", "3～4人家族", "5人以上の家族"],
                key='household_size'
            )

        with col2:
            living_situation = st.selectbox(
                "🏠 住居タイプ",
                ["マンション・アパート", "一戸建て", "高層階（5階以上）", "1階・低層階"],
                key='living_situation'
            )
            
            priority = st.multiselect(
                "🎯 重視する項目（複数選択可）",
                ["持ち運びやすさ", "長期保存", "衛生面", "通信手段", "照明・電源", "食料・水"],
                default=["食料・水"],
                key='disaster_priority'
            )

        # その他の要望
        additional_requirements = st.text_area(
            "💬 その他の要望（任意）",
            placeholder="例: ペットがいる、小さい子供がいる、高齢者と同居、アレルギーがある、など",
            height=80,
            key='disaster_additional'
        )

        # AI提案ボタン
        if st.button("🤖 AI防災グッズ提案を生成", type="primary", use_container_width=True, key='disaster_ai_btn'):
            if not GENAI_AVAILABLE:
                st.error("❌ google-generativeai パッケージがインストールされていません。")
                st.info("以下のコマンドでインストールしてください: `pip install google-generativeai`")
            elif not st.session_state.gemini_api_key:
                st.warning("⚠️ AIプラン提案タブでGemini APIキーを設定してください")
                st.markdown("👉 **観光モード** → **AIプラン提案タブ** → **APIキー設定**")
            else:
                try:
                    with st.spinner("🤖 AIが防災グッズを提案中..."):
                        # Gemini API設定
                        genai.configure(api_key=st.session_state.gemini_api_key)
                        model = genai.GenerativeModel('gemini-2.0-flash-exp')

                        # プロンプト作成
                        system_prompt = """あなたは防災の専門家です。ユーザーの予算、家族構成、住居状況、優先項目に基づいて、
実用的で具体的な防災グッズのリストを提案してください。各商品には概算価格も含めてください。"""

                        user_prompt = f"""
以下の条件に基づいて、防災グッズのおすすめリストを作成してください：

【条件】
- 予算: {disaster_budget}
- 家族構成: {household_size}
- 住居タイプ: {living_situation}
- 重視する項目: {', '.join(priority) if priority else 'なし'}
{f'- その他の要望: {additional_requirements}' if additional_requirements else ''}

【回答形式】
1. 優先度の高い順に防災グッズをリスト化
2. 各グッズの名称、概算価格、選定理由を簡潔に記載
3. 予算内で収まるように調整
4. 合計金額を最後に表示

実用的で、すぐに購入できる具体的な商品名を挙げてください。
"""

                        # API呼び出し
                        response = model.generate_content(f"{system_prompt}\n\n{user_prompt}")

                        # 結果表示
                        st.markdown("---")
                        st.markdown("### 📋 AI提案：あなたに最適な防災グッズ")
                        st.markdown(response.text)

                        st.success("✅ 提案完了！")
                        
                        # 注意事項
                        st.info("💡 **購入前の確認事項**\n- 価格は目安です。購入時に最新価格を確認してください\n- 賞味期限・使用期限を定期的にチェックしましょう\n- 家族で避難場所や連絡方法を事前に話し合いましょう")

                except Exception as e:
                    st.error(f"❌ エラーが発生しました: {str(e)}")
                    st.info("💡 APIキーが正しいか確認してください")
        
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
            st.markdown("### 0973-23-3111")

# フッター
st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    st.caption("© 2025 日田市総合案内コンシェルジュ")
with col2:
    st.caption("📧 お問い合わせ")
with col3:
    st.caption("🔒 プライバシーポリシー")

# 使い方ヒント
with st.expander("💡 使い方のヒント"):
    st.markdown("""
    ### 📖 日田市総合案内コンシェルジュの使い方

    #### 観光モードでできること
    1. **地図でスポットを確認**: マップタブで日田市内の観光スポットを一覧表示
    2. **スポットを選択**: 1つまたは複数のスポットを自由に選択
       - 1つだけ選択：単一ルートを表示（距離・時間・詳細情報）
       - 2つ以上選択：最適化ルートを算出（待ち時間と距離を考慮）
    3. **カテゴリーフィルター**: 歴史、自然、グルメ、体験など、カテゴリー別に絞り込み。マップのピンも連動してフィルタリング
    4. **スポット検索**: スポット一覧タブでキーワード検索や並び替えが可能
    5. **天気情報**: 天気タブで気象情報サイトへアクセス
    6. **イベント情報**: 月別にイベントを確認できます
    7. **おすすめスポット**: 日田市の人気観光地をランキング形式で表示
    8. **AIプラン提案**: Gemini APIを使って、予算・時間・興味に合わせた最適な観光プランを自動生成

    #### 防災モードでできること
    1. **最寄り避難所の確認**: 現在地から近い避難所を表示
    2. **避難所を選択**: 1つまたは複数の避難所を自由に選択
       - 1つだけ選択：単一ルートを表示（距離・時間・詳細情報）
       - 2つ以上選択：最適化避難ルートを算出（最短距離）
    3. **避難ルート**: 徒歩での避難ルートをGoogle Mapsで確認
    4. **開設状況の確認**: 避難所の開設状況と収容人数をリアルタイム表示
    5. **営業店舗情報**: 災害時の営業中コンビニ・スーパーを確認
    6. **防災グッズ提案**: 予算に応じた防災グッズのおすすめ

    #### 最適化ルート機能について
    - **観光モード**: 待ち時間と距離を考慮したスコアリングで最適な訪問順序を算出
    - **防災モード**: 最近傍法により最短距離での避難順序を算出
    - Google Maps連携で実際のルートをナビゲーション可能

    #### AIプラン提案機能について
    - Gemini API（gemini-2.0-flash-exp）を使用
    - ユーザーが自身のAPIキーを入力（セッション中のみ保持）
    - 予算、時間、興味、同行者に基づいた具体的なプランを生成

    #### GPS機能について（スマホ推奨）
    - **スマホで現在地を自動取得**: サイドバーの「🌐 GPS で現在地を取得」ボタンをタップ
    - ブラウザが位置情報の使用許可を求めるので「許可」を選択
    - 自動的に現在地の緯度・経度が設定され、地図が更新されます
    - HTTPS接続が必要（Streamlit Cloudでは自動的にHTTPS）
    - 手動で緯度・経度を入力することも可能です

    #### 便利な機能
    - **現在地の設定**: サイドバーからGPSで自動取得、または手動で緯度・経度を入力
    - **カテゴリーフィルター**: 歴史、自然、グルメ、体験など、カテゴリー別に絞り込み。マップのピンも連動してフィルタリング
    - **選択されたスポットの可視化**: 選択したスポットは赤いピンで表示され、視覚的に分かりやすい
    - **距離表示**: すべてのスポットに現在地からの距離を表示
    - **直線表示**: 地図上で現在地から目的地への直線を表示可能（単一選択時）
    - **待ち時間・混雑状況**: 飲食店や観光地の待ち時間と混雑状況を確認可能

    #### Google Maps連携について
    - 実際の道路に沿ったルート案内は、「Google Mapsでルートを見る」ボタンから外部アプリで確認できます
    - 移動手段（車・徒歩・自転車・公共交通）を選択してからボタンを押してください
    - スマートフォンではGoogle Mapsアプリが自動的に開きます
    - 最適化ルートでは複数の経由地を含むルートをGoogle Mapsで開くことができます
    """)