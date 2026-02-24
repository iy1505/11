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
            #status {
                margin-top: 10px;
                padding: 10px;
                border-radius: 5px;
            }
            .success {
                background-color: #D4EDDA;
                color: #155724;
            }
            .error {
                background-color: #F8D7DA;
                color: #721C24;
            }
        </style>
    </head>
    <body>
        <button onclick="getLocation()">🌐 GPS で現在地を取得</button>
        <div id="status"></div>
        
        <script>
            function getLocation() {
                const statusDiv = document.getElementById('status');
                statusDiv.innerHTML = '位置情報を取得中...';
                statusDiv.className = '';
                
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                        function(position) {
                            const lat = position.coords.latitude;
                            const lng = position.coords.longitude;
                            const accuracy = position.coords.accuracy;
                            
                            // Streamlitに値を返す
                            window.parent.postMessage({
                                isStreamlitMessage: true,
                                type: 'streamlit:setComponentValue',
                                value: {
                                    latitude: lat,
                                    longitude: lng,
                                    accuracy: accuracy
                                }
                            }, '*');
                            
                            statusDiv.innerHTML = '✅ 現在地を取得しました<br>緯度: ' + lat.toFixed(6) + '<br>経度: ' + lng.toFixed(6) + '<br>精度: ±' + accuracy.toFixed(0) + 'm';
                            statusDiv.className = 'success';
                        },
                        function(error) {
                            let errorMsg = '';
                            switch(error.code) {
                                case error.PERMISSION_DENIED:
                                    errorMsg = '❌ 位置情報の使用が拒否されました';
                                    break;
                                case error.POSITION_UNAVAILABLE:
                                    errorMsg = '❌ 位置情報が利用できません';
                                    break;
                                case error.TIMEOUT:
                                    errorMsg = '❌ タイムアウトしました';
                                    break;
                            }
                            statusDiv.innerHTML = errorMsg;
                            statusDiv.className = 'error';
                        },
                        {
                            enableHighAccuracy: true,
                            timeout: 10000,
                            maximumAge: 0
                        }
                    );
                } else {
                    statusDiv.innerHTML = '❌ このブラウザは位置情報に対応していません';
                    statusDiv.className = 'error';
                }
            }
        </script>
    </body>
    </html>
    """
    
    return components.html(gps_html, height=150)