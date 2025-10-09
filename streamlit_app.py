import streamlit as st
import streamlit.components.v1 as components
import json
import os

# 観光モード・防災モードのデータ
tourism_spots = [
    {"name": "豆田町", "lat": 33.319, "lon": 130.939, "type": "観光地"},
    {"name": "サッポロビール九州日田工場", "lat": 33.3225, "lon": 130.9183, "type": "飲食店"},
    {"name": "日田温泉", "lat": 33.3222, "lon": 130.9333, "type": "温泉"},
]

evacuation_spots = [
    {"name": "日田市民文化会館", "lat": 33.322, "lon": 130.926, "type": "避難所"},
    {"name": "日田市立図書館", "lat": 33.324, "lon": 130.932, "type": "避難所"},
]

# ページ設定
st.set_page_config(page_title="日田市マップナビ", layout="wide")
st.title("🗾 日田市マップナビ（Google Maps版）")

mode = st.radio("モードを選んでください", ["観光モード", "防災モード"])

# モードに応じたデータを選ぶ
selected_data = tourism_spots if mode == "観光モード" else evacuation_spots

# static フォルダを作って JSON を保存
os.makedirs("static", exist_ok=True)
with open("static/map_data.json", "w", encoding="utf-8") as f:
    json.dump(selected_data, f, ensure_ascii=False)

# Google Map を表示
with open("google_map.html", "r", encoding="utf-8") as f:
    html = f.read()

components.html(html, height=600)

# --- デモの現在地（豆田町あたりの日田市中心地に固定）
current_location = (33.319, 130.939)
lat, lon = current_location

st.info(f"現在地はデモのため固定です: 豆田町付近（緯度: {lat}, 経度: {lon}）")

# 1. 地図オブジェクト作成
m = folium.Map(location=[lat, lon], zoom_start=14)

# 2. 現在地マーカー追加
folium.Marker([lat, lon], tooltip="現在地（豆田町付近）", icon=folium.Icon(color='blue')).add_to(m)

if mode == "観光モード":
    st.subheader("🗺️ 観光地・飲食店マップ")
    for spot in tourism_spots:
        folium.Marker(
            [spot["lat"], spot["lon"]],
            tooltip=f'{spot["name"]}（{spot["type"]}）',
            popup=f'営業時間: {spot["hours"]}',
            icon=folium.Icon(color='green', icon="info-sign")
        ).add_to(m)

    st.markdown("### 🌞 現在の天気情報")
    desc, temp = get_weather(lat, lon)
    if desc:
        st.write(f"天気: **{desc}**, 気温: **{temp}℃**")
    else:
        st.write("天気情報が取得できませんでした。")

    st.markdown("### 🎉 季節のイベント")
    st.info("- 10月：日田天領まつり\n- 8月：日田祇園祭\n- 春：桜まつり（亀山公園）")

elif mode == "防災モード":
    st.subheader("🚨 避難場所と災害エリア表示")

    nearest = find_nearest(current_location, evacuation_spots)
    st.markdown(f"🏃‍♂️ 最寄りの避難場所: **{nearest['name']}**")
    folium.Marker(
        [nearest["lat"], nearest["lon"]],
        tooltip="最寄り避難所",
        icon=folium.Icon(color='red', icon="info-sign")
    ).add_to(m)

    st.markdown("### ⚠️ 災害種別ごとの危険エリア")
    for disaster, points in disaster_zones.items():
        for lat_d, lon_d in points:
            folium.CircleMarker(
                location=[lat_d, lon_d],
                radius=30,
                color="orange",
                fill=True,
                fill_opacity=0.4,
                popup=f"{disaster}エリア"
            ).add_to(m)

    st.markdown("### 🧰 防災グッズリスト")
    st.success(
        "- 懐中電灯\n- モバイルバッテリー\n- 非常食\n- 水\n- ラジオ\n- 救急セット"
    )

# 3. 地図表示
st_folium(m, width=800, height=550)
