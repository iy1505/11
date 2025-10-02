import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
import requests

# --- APIキー（各自取得して設定してください）必須項目
GOOGLE_MAPS_API_KEY = "YOUR_GOOGLE_API_KEY"
OPENWEATHER_API_KEY = "YOUR_OPENWEATHER_API_KEY"

# --- デモデータ（実際はAPIやDBから取得してください）
tourism_spots = [
    {"name": "豆田町", "lat": 33.319, "lon": 130.939, "type": "観光地", "hours": "9:00 - 17:00"},
    {"name": "サッポロビール九州日田工場", "lat": 33.3225, "lon": 130.9183, "type": "飲食店", "hours": "10:00 - 18:00"},
    {"name": "日田温泉", "lat": 33.3222, "lon": 130.9333, "type": "温泉", "hours": "15:00 - 23:00"},
]

evacuation_spots = [
    {"name": "日田市民文化会館", "lat": 33.322, "lon": 130.926},
    {"name": "日田市立図書館", "lat": 33.324, "lon": 130.932},
]

disaster_zones = {
    "洪水": [(33.318, 130.930), (33.320, 130.928)],
    "土砂災害": [(33.315, 130.925), (33.316, 130.927)],
}

# --- 関数群

def get_coordinates(address):
    """住所や地名から緯度経度を取得（Google Geocoding API利用）"""
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": GOOGLE_MAPS_API_KEY, "region": "jp"}
    res = requests.get(url, params=params).json()
    if res.get('status') == 'OK':
        loc = res['results'][0]['geometry']['location']
        return (loc['lat'], loc['lng'])
    return None

def get_weather(lat, lon):
    """OpenWeatherMap APIで天気情報を取得"""
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY, "units": "metric", "lang": "ja"}
    res = requests.get(url, params=params).json()
    if "weather" in res and "main" in res:
        return res["weather"][0]["description"], res["main"]["temp"]
    return None, None

def find_nearest(current, locations):
    """現在地(current)から最も近いスポットを返す"""
    return min(locations, key=lambda loc: geodesic(current, (loc["lat"], loc["lon"])).km)

# --- Streamlit UI

st.set_page_config(page_title="日田市ナビアプリ", layout="wide")
st.title("🗾 日田市マップナビ - 観光 / 防災モード切替")

# モード選択
mode = st.radio("モードを選択してください", ["観光モード", "防災モード"])

# 現在地入力
address = st.text_input("📍 現在地を入力（例: JR日田駅）", "JR日田駅")
location = get_coordinates(address)

if not location:
    st.error("現在地の取得に失敗しました。正しい地名を入力してください。")
    st.stop()

# 1. 地図オブジェクト作成
m = folium.Map(location=[緯度, 経度], zoom_start=14)

# 2. マーカーなどを追加
folium.Marker([緯度, 経度], tooltip="ここ！").add_to(m)

# 3. Streamlitに地図を表示
st_folium(m, width=700, height=500)


if mode == "観光モード":
    st.subheader("🗺️ 観光地・飲食店マップ")
    # 観光地マーカー設置
    for spot in tourism_spots:
        folium.Marker(
            [spot["lat"], spot["lon"]],
            tooltip=f'{spot["name"]}（{spot["type"]}）',
            popup=f'営業時間: {spot["hours"]}',
            icon=folium.Icon(color='green', icon="info-sign")
        ).add_to(m)

    # 天気情報表示
    st.markdown("### 🌞 現在の天気情報")
    desc, temp = get_weather(*location)
    if desc:
        st.write(f"天気: **{desc}**, 気温: **{temp}℃**")
    else:
        st.write("天気情報が取得できませんでした。")

    # 季節イベントなど
    st.markdown("### 🎉 季節のイベント")
    st.info("- 10月：日田天領まつり\n- 8月：日田祇園祭\n- 春：桜まつり（亀山公園）")

elif mode == "防災モード":
    st.subheader("🚨 避難場所と災害エリア表示")

    # 最寄り避難場所の表示
    nearest = find_nearest(location, evacuation_spots)
    st.markdown(f"🏃‍♂️ 最寄りの避難場所: **{nearest['name']}**")
    folium.Marker(
        [nearest["lat"], nearest["lon"]],
        tooltip="最寄り避難所",
        icon=folium.Icon(color='red', icon="info-sign")
    ).add_to(m)

    # 災害種別ごとの危険エリア表示
    st.markdown("### ⚠️ 災害種別ごとの危険エリア")
    for disaster, points in disaster_zones.items():
        for lat, lon in points:
            folium.CircleMarker(
                location=[lat, lon],
                radius=30,
                color="orange",
                fill=True,
                fill_opacity=0.4,
                popup=f"{disaster}エリア"
            ).add_to(m)

    # 防災グッズ紹介
    st.markdown("### 🧰 防災グッズリスト")
    st.success(
        "- 懐中電灯\n- モバイルバッテリー\n- 非常食\n- 水\n- ラジオ\n- 救急セット"
    )

# 地図表示
st_folium(m, width=800, height=550)
