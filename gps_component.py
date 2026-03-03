import streamlit.components.v1 as components

def gps_locator():
    """GPSで現在地を取得するコンポーネント"""
    
    gps_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {
                font-family: sans-serif;
                padding: 10px;
                margin: 0;
            }
            button {
                background-color: #FF4B4B;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                width: 100%;
            }
            button:hover {
                background-color: #FF6B6B;
            }
            button:disabled {
                background-color: #cccccc;
                cursor: not-allowed;
            }
            #status {
                margin-top: 10px;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            }
            .success {
                background-color: #D4EDDA;
                color: #155724;
            }
            .error {
                background-color: #F8D7DA;
                color: #721C24;
            }
            .info {
                background-color: #D1ECF1;
                color: #0C5460;
            }
        </style>
    </head>
    <body>
        <button id="gpsButton" onclick="getLocation()">🌐 GPS で現在地を取得</button>
        <div id="status"></div>
        
        <script>
            function getLocation() {
                const statusDiv = document.getElementById('status');
                const button = document.getElementById('gpsButton');
                
                statusDiv.innerHTML = '📍 位置情報を取得中...';
                statusDiv.className = 'info';
                button.disabled = true;
                
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                        function(position) {
                            const lat = position.coords.latitude;
                            const lng = position.coords.longitude;
                            const accuracy = position.coords.accuracy;
                            
                            console.log('位置情報取得成功:', lat, lng, accuracy);
                            
                            // Streamlitに値を返す（複数の方法で試行）
                            const data = {
                                latitude: lat,
                                longitude: lng,
                                accuracy: accuracy
                            };
                            
                            // 方法1: Streamlit Components API
                            if (window.parent.Streamlit) {
                                window.parent.Streamlit.setComponentValue(data);
                            }
                            
                            // 方法2: postMessage
                            window.parent.postMessage({
                                isStreamlitMessage: true,
                                type: 'streamlit:setComponentValue',
                                value: data
                            }, '*');
                            
                            // 方法3: 直接親ウィンドウに設定
                            if (window.parent.streamlitComponentValue !== undefined) {
                                window.parent.streamlitComponentValue = data;
                            }
                            
                            statusDiv.innerHTML = '✅ 現在地を取得しました<br>緯度: ' + lat.toFixed(6) + '<br>経度: ' + lng.toFixed(6) + '<br>精度: ±' + accuracy.toFixed(0) + 'm';
                            statusDiv.className = 'success';
                            button.disabled = false;
                        },
                        function(error) {
                            let errorMsg = '';
                            switch(error.code) {
                                case error.PERMISSION_DENIED:
                                    errorMsg = '❌ 位置情報の使用が拒否されました。ブラウザの設定を確認してください。';
                                    break;
                                case error.POSITION_UNAVAILABLE:
                                    errorMsg = '❌ 位置情報が利用できません。';
                                    break;
                                case error.TIMEOUT:
                                    errorMsg = '❌ タイムアウトしました。もう一度お試しください。';
                                    break;
                                default:
                                    errorMsg = '❌ 不明なエラーが発生しました。';
                            }
                            console.error('位置情報取得エラー:', error);
                            statusDiv.innerHTML = errorMsg;
                            statusDiv.className = 'error';
                            button.disabled = false;
                        },
                        {
                            enableHighAccuracy: true,
                            timeout: 15000,
                            maximumAge: 0
                        }
                    );
                } else {
                    statusDiv.innerHTML = '❌ このブラウザは位置情報に対応していません';
                    statusDiv.className = 'error';
                    button.disabled = false;
                }
            }
        </script>
    </body>
    </html>
    """
    
    # heightを200に増やして、returnでコンポーネントの値を取得
    result = components.html(gps_html, height=200)
    return result