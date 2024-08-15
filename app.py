# // import //
import streamlit as st
from streamlit_option_menu import option_menu
from streamlit_extras.metric_cards import style_metric_cards
import pandas as pd
import numpy as np
import pymysql
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import plotly.express as px
import json


# // 레이아웃 및 스타일 //
st.set_page_config(layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@100..900&display=swap');

    /* 모든 텍스트 요소에 폰트 적용 */
    html, body, div, span, root, app, data-testid, app-view-root, [class*="css"], h1, h2, h3, h4, h5, h6 {
        font-family: 'Noto Sans KR', sans-serif !important;
    }

    /* 더 구체적인 선택자를 사용하여 스타일 적용 */    
    div[data-testid="stMetric"], div[data-testid="metric-container"] {
        background-color: #f9f9f9 !important;  /* 배경색 변경 */
        border: 1px solid #ccc !important;  /* 테두리 색상 변경 */
        padding: 5% 5% 5% 10%;
        border-radius: 5px;
        border-left: 0.5rem solid #ffa25d !important;  /* 좌측 바 색상 */
        box-shadow: 0 0.15rem 1.75rem 0 rgba(58, 59, 69, 0.15) !important;
    }
    
    /* 메트릭 카드 내부의 글씨 크기 조절 */
    div[data-testid="stMetric"] > div label {
        font-size: 0.5em;
    }
    div[data-testid="stMetric"] > div div {
        font-size: 0.5em;
    }
    div[data-testid="stMetric"] > div div[data-testid="stMetricDelta"] {
        font-size: 0.5em;
    }
    </style>
    """, unsafe_allow_html=True)


# // 데이터베이스 민감정보 호출 //
def get_dbjson(target):
    f  = open('db.json', encoding='UTF-8')
    dbjson = json.loads(f.read(),strict=False) 
    
    host = dbjson[target]['host']
    user = dbjson[target]['user']
    password = dbjson[target]['password']
    database = dbjson[target]['database']
    port = dbjson[target]['port']
    
    return host, user, password, database, port


#  // 데이터 호출 //
def call_data(media_nm, target):
    conn = pymysql.connect(host=get_dbjson(target)[0],
                           user=get_dbjson(target)[1],
                           password=get_dbjson(target)[2],
                           database=get_dbjson(target)[3],
                           port=get_dbjson(target)[4],
                           charset='utf8')
    query = f"SELECT * FROM {media_nm}"
    rawdata = pd.read_sql(query, con=conn)
    
    conn.close()
    
    # 전처리 (효율)
    rawdata['CPM'] = rawdata['spend']/rawdata['impressions']*1000
    rawdata['CPC'] = rawdata['spend']/rawdata['clicks']
    rawdata['CPV'] = rawdata['spend']/rawdata['view_p25']
    rawdata['CTR'] = rawdata['clicks']/rawdata['impressions']*100
    rawdata['VTR'] = rawdata['view_p25']/rawdata['impressions']*100
    
    # 전처리 (기타)
    rawdata['year'] = rawdata['index'].str.split('_').str[0]
    rawdata['month'] = rawdata['index'].str.split('_').str[1]
    rawdata['year_month'] = rawdata['index'].str.split('_').str[0] + '/' + rawdata['index'].str.split('_').str[1]
    
    return rawdata


# // 메트릭 카드 //
# column_names = 리스트로 전달, 반복문을 사용하여 메트릭 카드를 동적으로 생성, 컬럼별 평균 계산
def draw_metricCard(data, column_names): 
    cols = st.columns(len(column_names))
    
    for i, col_name in enumerate(column_names):
        avg_value = data[col_name].mean()
        cols[i].metric(label=col_name, value=round(avg_value, 1), delta=0)

    style_metric_cards()


# // 파이 차트 //
def draw_pieChart(data, column_name, color_theme='Custom'):
    
    # 수치형 또는 집계형
    if not pd.api.types.is_numeric_dtype(data[column_name]):
        data_to_plot = data[column_name].value_counts().reset_index()
        data_to_plot.columns = [column_name, 'count']
        value_column = 'count'
    else:
        data_to_plot = data
        value_column = column_name
    
    # 5개까지만 표현, 이하 기타
    top_5 = data_to_plot.nlargest(5, value_column)
    others = data_to_plot.iloc[5:].sum(numeric_only=True)[value_column]
    if others > 0:
        etc_df = pd.DataFrame({column_name: ['기타'], value_column: [others]})
        top_5 = pd.concat([top_5, etc_df], ignore_index=True)
        # append 특정 디펜더시에 따른 오류 반환   
        # if others > 0:
        #     top_5 = top_5.append(pd.DataFrame({column_name: ['etc'], value_column: [others]}), ignore_index=True)
        
    # 컬러
    color_palettes = {
        'Plotly': px.colors.qualitative.Plotly,
        'Viridis': px.colors.sequential.Viridis,
        'Cividis': px.colors.sequential.Cividis,
        'Plasma': px.colors.sequential.Plasma,
        'Custom': ['#8075ff', '#24cbde', '#ff6dab', '#ffb700', '#45b7fd']}
    
    colors = color_palettes.get(color_theme, px.colors.qualitative.Plotly)
    
    fig = px.pie(top_5, values=value_column, names=column_name,
                 height=250, width=250, color_discrete_sequence=colors)
    
    fig.update_traces(
        textinfo='label+percent+value',
        hoverinfo='label+percent+value',
        hovertemplate='<b>%{label}</b><br>%{percent:.1%}<br>%{value}<extra></extra>',  # 마우스 오버 시 표시될 정보
        texttemplate='%{percent:.1%}',
        textposition='inside',
        textfont_size=13,
        textfont_color='white',
        hole=0.2,
        domain={'x': [0, 1], 'y': [0, 1]})
    
    fig.update_layout(
        margin=dict(t=50, b=50), # l=20, r=20, t=30, b=0
        showlegend=True,
        legend=dict(y=0.5, yanchor='middle', x=0.9, xanchor='left', orientation="v"),
        uniformtext_minsize=13,
        uniformtext_mode='hide',
        annotations=[dict(text='', x=0.5, y=0.5, font_size=13, showarrow=False)])

    st.plotly_chart(fig, use_container_width=True)


# // 사이드 체크박스 - multiselect //
def draw_sideCheckbox(data, colname, input_title):
    unique_options = data[colname].unique().tolist()
    selected_options = st.sidebar.multiselect(input_title, unique_options)
    return selected_options


# // 히트맵 //
def create_heatmap(df, metric_columns, precision=2):
    colors = ["#f6f5ff", "#BFB9FF"]
    cmap_CustomMap = mcolors.LinearSegmentedColormap.from_list("CustomMap", colors) 
    styled_df = df.style.background_gradient(cmap=cmap_CustomMap, subset=metric_columns).format(precision=precision)
    return styled_df


# // 메인 //
def main():
    
    # 전체 스타일
    st.markdown("""
        <style>
        .css-1d391kg { padding: 1rem 1rem 1rem 1rem; }
        .css-18e3th9 { display: none; }
        .css-1v0mbdj a { font-size: 14px !important; padding: 5px 10px;
        }
        
        /* .menu .container-xxl[data-v-5af006b8]에 글씨체 적용 */
        .menu .container-xxl[data-v-5af006b8] {
            font-family: 'Noto Sans KR', sans-serif !important;
        }
        </style>
        """, unsafe_allow_html=True)

    # 전체 사이드바
    with st.sidebar:
        # 정의
        _sidebar_header = 'the MAP 2.0'
        _sidebar_markdown = '더맵은 전사 광고 캠페인 데이터 기반 <br>디지털마케팅 벤치마크 플랫폼입니다'
        _menu_names = ['메타', '구글', '메뉴3', '메뉴4'] # 리스트 순서대로 페이지 결정
        _menu_icons = ['facebook', 'google', 'heart', 'heart']
        # 구현
        st.header(_sidebar_header)
        st.markdown(_sidebar_markdown, unsafe_allow_html=True); st.text('')
        menu = option_menu(None, _menu_names, icons=_menu_icons, menu_icon="cast", default_index=0)
    
    
    # // 1페이지
    if menu == _menu_names[0]:
        
        # 데이터 - 전체
        _data = call_data('tb_meta', 'server2')
        temp_data = _data.copy()        
        temp_data = temp_data.fillna(0).replace([np.inf, -np.inf], 0)
        
        # 데이터 - 기준 컬럼, 수치 컬럼 
        _grouping_columns_options = ['media_name', 'adproduct_name', 'platform_position', 'device', 'bid_type', 'objective', 'buying_type', 'optimization_goal', 'billing_event', 'inds_name', 'year_month']
        _metric_columns_options = ['CPM', 'CPC', 'CPV', 'CTR', 'VTR', 'clicks', 'impressions', 'reach', 'frequency', 'view_p25', 'view_p50', 'view_p75', 'view_p100', 'spend']

        # 사이드 체크박스
        _filter_conditions = {
            'year_month': '날짜 선택',
            'inds_name': '업종 선택',
            'media_name': '미디어 선택',
            'adproduct_name': '광고상품 선택',
            'platform_position': '게재위치 선택',
            'device': '기기 선택'}
        selected_filters = {col: draw_sideCheckbox(temp_data, col, label) for col, label in _filter_conditions.items()} # 사이드바에서 선택된 필터 값을 저장할 딕셔너리
        for col, selected_values in selected_filters.items(): # 선택된 필터가 있는 경우 해당 데이터를 필터링
            if selected_values:
                temp_data = temp_data[temp_data[col].isin(selected_values)]

        # 본문 0 - 제목
        st.header("메타 대시보드") # divider='gray'
        
        # 본문 1 - 메트릭 카드
        st.text(" ")
        draw_metricCard(temp_data, ['CPM', 'CPC', 'CPV', 'CTR', 'VTR'])
    
        # 본문 2 - 효울 확인
        st.header(" ", anchor=False)
        st.subheader(":mag: 효율 확인하기")
        st.markdown('''선택한 컬럼별 **평균 효율 및 수치**를 확인할 수 있습니다.''')
        
        # 본문 2 - my_form1
        with st.form(key='my_form1'):
            _grouping_columns_options_default = ['media_name']
            _metric_columns_options_default = ['CPM', 'CTR', 'impressions', 'clicks', 'spend']
            col1, col2, col3 = st.columns([6, 6, 1])
            with col1:
                grouping_columns = st.multiselect("기준 컬럼을 선택하세요.", options= _grouping_columns_options, default=_grouping_columns_options_default)
            with col2:
                metric_columns = st.multiselect("수치 컬럼을 선택하세요.", options=_metric_columns_options, default=_metric_columns_options_default)
            with col3:
                st.markdown("<div style='height: 27px;'></div>", unsafe_allow_html=True)
                submit_button = st.form_submit_button(label='적용')
                
        # 본문 2 - 데이터프레임 (디폴트 데이터프레임으로 시작)
        if grouping_columns and metric_columns:
            grouped_df = temp_data.groupby(_grouping_columns_options_default)[_metric_columns_options_default].mean().fillna(0).reset_index()
            grouped_df = grouped_df.replace([np.inf, -np.inf], 0)
            styled_df = create_heatmap(grouped_df.head(100), _metric_columns_options_default) # 히트맵 적용
            dataframe_placeholder = st.dataframe(styled_df.hide(axis='index'), use_container_width=True) # 인덱스 숨기기
        else:
            pass # 패스, 다음 else문에서 워닝

        # 본문 2 - 데이터프레임 업데이트 (버튼 클릭으로 변경)
        if submit_button:
            if grouping_columns and metric_columns:
                grouped_df = temp_data.groupby(grouping_columns)[metric_columns].mean().reset_index()
                styled_df = create_heatmap(grouped_df.head(100), metric_columns) # 히트맵 적용
                dataframe_placeholder.dataframe(styled_df.hide(axis='index'), use_container_width=True)
            else:
                st.warning("기준 컬럼과 수치 컬럼을 선택해주세요. 선택된 컬럼이 없을 경우 데이터를 표시할 수 없습니다.")
            
        # 본문 3 - 비중 확인
        st.header(" ", anchor=False)
        st.subheader(":mag: 비중 확인하기")
        st.markdown('선택한 컬럼별 **집행 비중**을 확인할 수 있습니다.')

        # 본문 3 - myform2
        with st.form(key='myform2'):
            _grouping_columns_options_default = ['media_name']
            col1, col2 = st.columns([12, 1])
            with col1:
                grouping_columns = st.multiselect("기준 컬럼을 선택하세요.", options=_grouping_columns_options, default=_grouping_columns_options_default)
            with col2:
                st.markdown("<div style='height: 27px;'></div>", unsafe_allow_html=True)
                submit_button_ratio = st.form_submit_button(label='적용')

        # 본문 3 - 데이터프레임 (디폴트 데이터프레임으로 시작)
        if grouping_columns:
            grouped_df = temp_data.groupby(grouping_columns).size().reset_index(name='count')
            grouped_df['percentage'] = grouped_df['count'] / grouped_df['count'].sum() * 100
            grouped_df = grouped_df.sort_values(by='percentage', ascending=False).reset_index(drop=True) # 내림차순
            styled_df = create_heatmap(grouped_df.head(100), ['count', 'percentage'])
            dataframe_placeholder = st.dataframe(styled_df.hide(axis='index'), use_container_width=True) # 인덱스 숨기기
        else:
            pass # 패스, 다음 else문에서 워닝

        # 본문 3 - 데이터프레임 업데이트 (버튼 클릭으로 변경)
        if submit_button_ratio:
            if grouping_columns:
                grouped_df = temp_data.groupby(grouping_columns).size().reset_index(name='count')
                grouped_df['percentage'] = grouped_df['count'] / grouped_df['count'].sum() * 100
                grouped_df = grouped_df.sort_values(by='percentage', ascending=False).reset_index(drop=True) # 내림차순
                styled_df = create_heatmap(grouped_df.head(100), ['count', 'percentage'])
                dataframe_placeholder.dataframe(styled_df.hide(axis='index'), use_container_width=True) # 인덱스 숨기기
            else:
                st.warning("기준 컬럼을 선택해주세요. 선택된 컬럼이 없을 경우 데이터를 표시할 수 없습니다.")



        # 본문 4 - 그래프 / Bokeh 대신 Plotly를 사용
        st.header(" ", anchor=False)
        st.subheader(":mag: 추이 확인하기")
        
        # form holding
        with st.form(key='my_form2'):
            col1, col2 = st.columns([12, 1])  # 비율
            
            with col1:
                metric_columns = st.multiselect("수치 컬럼을 선택하세요.", options=_metric_columns_options, default=['CPM'])

            with col2:
                # st.write("")  # 버튼을 아래로 내리기 위한 빈 줄
                st.markdown("<div style='height: 27px;'></div>", unsafe_allow_html=True)  # 30px 만큼의 공간을 추가
                submit_button = st.form_submit_button(label='적용')  # 버튼을 오른쪽에 배치

        # 디폴트 그래프
        grouped_data = temp_data.groupby('year_month')['CPM'].mean().reset_index()
        grouped_data = grouped_data.sort_values('year_month')
        
        fig = px.line(grouped_data, x='year_month', y=['CPM'], labels={'year_month': '연도_월', 'value': '값'})

        fig.update_layout(
            xaxis_title="연도_월",
            yaxis_title="값",
            legend_title="선택된 수치 컬럼",
            font=dict(size=13),  # 그래프 안 글씨 크기를 13pt로 고정
            height=400,
            width=900,
            margin=dict(l=20, r=20, t=50, b=20))
        
        fig.update_traces(
            mode='lines+markers')

        plot_placeholder = st.plotly_chart(fig, use_container_width=True)
        
        # 사용자가 "적용" 버튼을 눌렀을 때만 그래프를 업데이트
        if submit_button:
            if metric_columns:
                grouped_data = temp_data.groupby('year_month')[metric_columns].mean().reset_index()
                grouped_data = grouped_data.sort_values('year_month')

                # Plotly 시각화
                fig = px.line(grouped_data, x='year_month', y=metric_columns, labels={'year_month': '연도_월', 'value': '값'})

                fig.update_layout(
                    xaxis_title="연도_월",
                    yaxis_title="값",
                    legend_title="선택된 수치 컬럼",
                    font=dict(size=13),  # 그래프 안 글씨 크기를 13pt로 고정
                    height=400,
                    width=900,
                    margin=dict(l=20, r=20, t=50, b=20))
                
                fig.update_traces(
                    mode='lines+markers')

                plot_placeholder.plotly_chart(fig, use_container_width=True)
            
            else:
                st.write("수치 컬럼을 선택하세요.")



    ####################################################################################################################
    ##############################################      2 페이지      ###################################################
    ####################################################################################################################

    elif menu == '메뉴2':
        st.title("메뉴2 페이지")
        st.write("여기는 메뉴2 페이지입니다.")

    elif menu == '메뉴3':
        st.title("메뉴3 페이지")
        st.write("여기는 메뉴3 페이지입니다.")

    elif menu == '메뉴4':
        st.title("메뉴4 페이지")
        st.write("여기는 메뉴4 페이지입니다.")


if __name__ == '__main__':
    main()

