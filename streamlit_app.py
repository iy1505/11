import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from itertools import permutations

# --- APIキー（環境変数や安全な場所に置いてね） ---
OPENWEATHER_API_KEY = 'あなたのOpenWeatherMapAPIキー'
GOOGLE_MAPS_API_KEY = 'あなたのGoogleMapsAPIキー'

# 日田市の中心座標（緯度・経度）
HITA_COORDS = (33.3213, 130.9293)

# --- 天気情報取得 ---
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

# --- ルート計算 ---
def get_route(origin, destination, mode='driving'):
    url = 'https://maps.googleapis.com/maps/api/directions/json'
    params = {
        'origin': f'{origin[0]},{origin[1]}',
        'destination': f'{destination[0]},{destination[1]}',
        'mode': mode,
        'key': GOOGLE_MAPS_API_KEY
    }
    res = requests.get(url, params=params)
    data = res.json()
    if data['status'] == 'OK':
        route = data['routes'][0]['overview_polyline']['points']
        legs = data['routes'][0]['legs'][0]
        distance = legs['distance']['text']
        duration = legs['duration']['text']
        steps = legs['steps']
        return route, distance, duration, steps
    else:
        return None, None, None, None

# --- 緯度経度の距離計算（単純な直線距離） ---
from geopy.distance import geodesic

def total_distance(points):
    dist = 0
    for i in range(len(points)-1):
        dist += geodesic(points[i], points[i+1]).km
    return dist

# --- 最短ルート順序の計算（順列全探索） ---
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

# --- Streamlit UI ---
st.title('日田市観光ナビマップ')

# 天気表示
st.header('現在の日田市の天気')
weather_desc, temp, humidity = get_weather(*HITA_COORDS)
if weather_desc:
    st.write(f"天気: {weather_desc}")
    st.write(f"気温: {temp} ℃")
    st.write(f"湿度: {humidity} %")
else:
    st.write("天気情報を取得できませんでした。")

# ユーザーの現在地入力（簡易的にテキスト入力）
st.header('現在地を入力（緯度,経度）')
user_location_input = st.text_input('例: 33.320, 130.930', '33.320,130.930')
try:
    user_location = tuple(map(float, user_location_input.split(',')))
except:
    st.error('緯度と経度をカンマで区切って入力してください')
    st.stop()

# 目的地の追加（最大5ヶ所まで）
st.header('目的地を複数入力')
destinations = []
for i in range(1, 6):
    dest_input = st.text_input(f'目的地{i}（緯度,経度をカンマ区切りで入力）', '')
    if dest_input:
        try:
            coord = tuple(map(float, dest_input.split(',')))
            destinations.append(coord)
        except:
            st.error(f'目的地{i}の入力形式が正しくありません')
            st.stop()

if len(destinations) == 0:
    st.warning('目的地を1つ以上入力してください')
    st.stop()

# 交通手段の選択
mode = st.selectbox('移動手段を選択してください', ['driving', 'walking', 'bicycling', 'transit'])

# 最短ルート計算
best_order, dist = shortest_route(user_location, destinations)

st.write(f'推奨ルート順序（最短距離: {dist:.2f} km）:')
for idx, point in enumerate(best_order):
    st.write(f'{idx+1}. {point}')

# Foliumで地図表示
m = folium.Map(location=user_location, zoom_start=13)

# ユーザー現在地マーカー
folium.Marker(user_location, tooltip='現在地', icon=folium.Icon(color='blue')).add_to(m)

# 目的地マーカー
for idx, point in enumerate(best_order):
    folium.Marker(point, tooltip=f'目的地{idx+1}', icon=folium.Icon(color='red')).add_to(m)

# ルートを順に描画
import polyline
prev = user_location
for point in best_order:
    # Google Maps Directions APIで経路ポリライン取得
    route, distance, duration, steps = get_route(prev, point, mode)
    if route:
        decoded = polyline.decode(route)
        folium.PolyLine(decoded, color='green', weight=5, opacity=0.7).add_to(m)
    prev = point

st_folium(m, width=700, height=500)
