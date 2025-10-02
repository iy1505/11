import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from itertools import permutations
from geopy.distance import geodesic
import polyline

# ========================
# 🔐 APIキーを入れてください
# ========================
OPENWEATHER_API_KEY = 'YOUR_OPENWEATHERMAP_API_KEY'  # OpenWeatherMap
GOOGLE_MAPS_API_KEY = 'YOUR_GOOGLE_MAPS_API_KEY'     # Google Maps Platform

# ========================
# 📍 住所 → 緯度・経度に変換
# ========================
def get_coordinates(address):
    url = 'https://maps.googleapis.com/maps/api/geocode/json'
    params = {
        'address': address,
        'region': 'jp',
        'language': 'ja',
        'key': GOOGLE_MAPS_API_KEY
    }
    res = requests.get(url, params=params)
    data = res.json()
    if data['status'] == 'OK':
        location = data['results'][0]['geometry']['location']
        return (location['lat'], location['lng'])
    else:
        return None

# ========================
# ☀️ 天気情報取得
# ========================
def get_weather(lat, lon):
    url = f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja'
    res = requests.get(url)
    data = res.json()
    if res.status_code == 200:
        weather_desc = data['weather'][0]['description']
        temp = data['main']['temp']
        humidity = data['main']['humidity']
        return weather_desc, temp, humidity
    else:
        return None, None, None

# ========================
# 🚗 Google Maps APIでルート取得
# ========================
def get_route(origin, destination, mode='driving'):
    url = 'https://maps.googleapis.com/maps/api/directions/json'
    params = {
        'origin': f'{origin[0]},{origin[1]}',
        'destination': f'{destination[0]},{destination[1]}',
        'mode': mode,
        'language': 'ja',
        'region': 'jp',
        'key': GOOGLE_MAPS_API_KEY
    }
    res = requests.get(url, params=params)
    data = res.json()
    if data['status'] == 'OK':
        route = data['routes'][0]['overview_polyline']['points']
        legs = data['routes'][0]['legs'][0]
        distance = legs['distance']['text']
        duration = legs['duration']['text']
        return route, distance, duration
    else:
        return None, None, None

# ========================
# 📈 最短ルートを決定（順列全探索）
# ========================
def total_distance(points):
    dist = 0
    for i in range(len(points)-1):
        dist += geodesic(points[i], points[i+1]).km
    return dist

def shortest_route(start, destinations):
    min_dist = float('inf')
    best_order = None
    for order in permutations(destinations):
        route = [start] + list(order)
        dist = total_distance(route)
        if dist < min_dist:
            min_dist = dist
            best_order = order
    return best_order, min_dist

# ========================
# 🌐 Streamlit UI
# ========================
st.set_page_config(page_title="日田市観光マップ", layout="wide")
st.title('🗺️ 日田市観光ナビマップ')

# --- 現在地（地名入力） ---
st.header('📍 現在地を入力（住所・施設名）')
user_address = st.text_input('例: JR日田駅, サッポロビール九州日田工場', 'JR日田駅')
user_location = get_coordinates(user_address)
if not user_location:
    st.error('現在地の住所が正しく変換できませんでした。')
    st.stop()

# --- 天気情報表示 ---
st.subheader('☀️ 現在の天気')
weather_desc, temp, humidity = get_weather(*user_location)
if weather_desc:
    st.write(f"天気: {weather_desc}")
    st.write(f"気温: {temp} ℃")
    st.write(f"湿度: {humidity} %")
else:
    st.warning("天気情報を取得できませんでした。")

# --- 目的地の入力 ---
st.header('🎯 行きたい場所（最大5件）')
destinations = []
for i in range(1, 6):
    dest_input = st.text_input(f'目的地{i}', '')
    if dest_input:
        coord = get_coordinates(dest_input)
        if coord:
            destinations.append(coord)
        else:
            st.error(f'目的地{i}の住所が正しく変換できませんでした')
            st.stop()

if len(destinations) == 0:
    st.warning("目的地を1つ以上入力してください。")
    st.stop()

# --- 移動手段の選択 ---
mode = st.selectbox('🚶‍♀️ 移動手段', ['driving', 'walking', 'bicycling', 'transit'])

# --- 最短ルート計算 ---
best_order, total_km = shortest_route(user_location, destinations)
st.subheader(f"📍 最適な巡回順（合計距離: {total_km:.2f} km）")
for idx, point in enumerate(best_order):
    st.write(f"{idx+1}. 緯度: {point[0]}, 経度: {point[1]}")

# --- 地図描画 ---
m = folium.Map(location=user_location, zoom_start=14)
folium.Marker(user_location, tooltip='現在地', icon=folium.Icon(color='blue')).add_to(m)

# マーカーとルート
prev = user_location
for idx, dest in enumerate(best_order):
    folium.Marker(dest, tooltip=f'目的地{idx+1}', icon=folium.Icon(color='red')).add_to(m)
    route_polyline, dist_text, duration_text = get_route(prev, dest, mode)
    if route_polyline:
        decoded = polyline.decode(route_polyline)
        folium.PolyLine(decoded, color='green', weight=5).add_to(m)
    prev = dest

# --- 地図を表示 ---
st.subheader("🗺️ 地図")
st_folium(m, width=800, height=500)
