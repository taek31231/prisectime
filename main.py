import streamlit as st
import folium
from streamlit_folium import st_folium
import numpy as np
from scipy.optimize import fsolve

# --- 1. 설정 및 인터페이스 ---
st.set_page_config(page_title="지진 진앙지 결정 시뮬레이터", layout="wide")
st.title("🌎 지진 관측소 데이터를 활용한 진앙 찾기")

st.markdown("""
이 페이지에서는 세 곳의 관측소에서 측정된 **PS시(P파와 S파의 도착 시간 차이)**를 이용하여 지진의 발생 위치인 **진앙**을 계산합니다.
""")

# 사이드바: 물리적 상수 설정
st.sidebar.header("⚒️ 물리 상수 설정")
vp = st.sidebar.number_input("P파 속도 (km/s)", value=6.0)
vs = st.sidebar.number_input("S파 속도 (km/s)", value=3.5)
k_factor = (vp * vs) / (vp - vs)

# --- 2. 데이터 저장소 초기화 ---
if 'stations' not in st.session_state:
    st.session_state.stations = []

# --- 3. 지도 및 관측소 설정 ---
st.subheader("📍 단계 1: 지도에서 관측소 3곳 선택")
c1, c2 = st.columns([2, 1])

with c1:
    m = folium.Map(location=[36.5, 127.5], zoom_start=7)
    for i, s in enumerate(st.session_state.stations):
        folium.Marker([s['lat'], s['lon']], tooltip=f"관측소 {i+1}", icon=folium.Icon(color="blue")).add_to(m)
    
    map_data = st_folium(m, width=700, height=500)

    # 클릭 시 관측소 추가
    if map_data['last_clicked'] and len(st.session_state.stations) < 3:
        new_lat, new_lon = map_data['last_clicked']['lat'], map_data['last_clicked']['lng']
        if not any(s['lat'] == new_lat for s in st.session_state.stations):
            st.session_state.stations.append({'lat': new_lat, 'lon': new_lon, 'ps': 5.0})
            st.rerun()

with c2:
    st.write("### 관측소 목록 및 TS시 입력")
    if not st.session_state.stations:
        st.info("지도 위를 클릭하여 관측소를 추가하세요.")
    
    for i, s in enumerate(st.session_state.stations):
        st.session_state.stations[i]['ps'] = st.number_input(
            f"관측소 {i+1} PS시 (초)", 
            value=float(st.session_state.stations[i]['ps']),
            key=f"input_ps_{i}"
        )
        dist = k_factor * st.session_state.stations[i]['ps']
        st.session_state.stations[i]['dist'] = dist
        st.caption(f"계산된 진원 거리: {dist:.2f} km")

    if st.button("관측소 초기화"):
        st.session_state.stations = []
        st.rerun()

# --- 4. 계산 과정 설명 (Markdown) ---
st.divider()
st.subheader("📑 단계 2: 계산 과정 이해하기")
with st.expander("여기를 클릭하여 계산 원리 보기"):
    st.latex(r"d = \frac{V_p \times V_s}{V_p - V_s} \times PS")
    st.write(f"현재 설정된 상수값에 따라, 진원 거리 $d$는 $PS \times {k_factor:.2f}$ 입니다.")
    st.write("""
    1. 각 관측소의 위도/경도를 평면 좌표($x, y$)로 변환합니다.
    2. 각 관측소를 중심으로 하고 진원 거리 $d$를 반지름으로 하는 세 개의 원 방정식을 세웁니다.
    3. 세 원이 공통으로 만나는 지점(최적해)을 수치 해석법으로 찾아 진앙을 결정합니다.
    """)

# --- 5. 교점 계산 및 시각화 ---
if len(st.session_state.stations) == 3:
    st.subheader("🎯 단계 3: 진앙지 작도 및 결과")
    
    from scipy.optimize import least_squares
    import math

    # 목적 함수 정의
    def residuals(p, stations):
        x, y = p
        res = []
        for s in stations:
            sx, sy = s['lon'] * 88.8, s['lat'] * 111.0 
            current_dist = math.sqrt((x - sx)**2 + (y - sy)**2)
            res.append(current_dist - s['dist'])
        return res

    # 초기값 계산
    avg_lon = sum(s['lon'] for s in st.session_state.stations) / 3 * 88.8
    avg_lat = sum(s['lat'] for s in st.session_state.stations) / 3 * 111.0
    
    # 최적화 실행
    result = least_squares(residuals, [avg_lon, avg_lat], args=(st.session_state.stations,))
    
    if result.success:
        res_lon, res_lat = result.x[0] / 88.8, result.x[1] / 111.0

        # 결과 지도 시각화
        res_map = folium.Map(location=[res_lat, res_lon], zoom_start=7)
        
        for s in st.session_state.stations:
            folium.Marker([s['lat'], s['lon']], icon=folium.Icon(color='blue')).add_to(res_map)
            folium.Circle(
                [s['lat'], s['lon']], 
                radius=s['dist'] * 1000, 
                color='blue', 
                fill=True, 
                fill_opacity=0.1
            ).add_to(res_map)
        
        folium.Marker(
            [res_lat, res_lon], 
            popup=f"예측 진앙지", 
            icon=folium.Icon(color='red', icon='star')
        ).add_to(res_map)

        # 주의: 여기서 괄호가 잘 닫혔는지 확인하세요!
        st_folium(res_map, width=900, height=500, key="result_map")
        
        st.success(f"✅ 계산 완료! 예측 진앙 위치: 북위 {res_lat:.4f}°, 경도 {res_lon:.4f}°")
    else:
        st.error("진앙지를 계산하는 데 실패했습니다.")

# 이 else 문이 위 if len(...) == 3: 과 줄이 맞아야 합니다.
else:
    st.info("지도에서 관측소 3곳을 모두 클릭해야 진앙 계산 결과가 나타납니다.")
