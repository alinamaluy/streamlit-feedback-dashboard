import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
from datetime import datetime

# Настройка Streamlit
st.set_page_config(page_title="FEEDBACK: аналитика отзывов по блюдам", layout="wide")

# Заголовок
st.title("FEEDBACK: аналитика отзывов по блюдам")

# Настройка Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = st.secrets["connections"]["gsheets"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials, scope)
client = gspread.authorize(creds)

# Кэшированная функция для загрузки данных
@st.cache_data(ttl=3600)
def load_data():
    sheet = client.open_by_key("1ymTQHXs7rCH6giN8lyefioQeyXR2nToYLosTRcj5--s").worksheet("Sheet1")
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'], format="%d.%m.%Y", errors="coerce")
    return df

# Загрузка данных
df = load_data()

# Фильтры
st.sidebar.header("Фильтры")
date_range = st.sidebar.date_input("Выберите диапазон дат", [df['date'].min(), df['date'].max()])

# Фильтр ресторанов (перенесен выше)
restaurants = st.sidebar.multiselect(
    "Выберите ресторан", 
    options=df['source'].unique(), 
    default=df['source'].unique(),
    placeholder="Выберите один или несколько ресторанов..."
)

# Фильтр блюд с автодополнением (после ресторанов)
all_dishes = df[df['source'].isin(restaurants)]['dish'].unique() if restaurants else df['dish'].unique()
selected_dishes = st.sidebar.multiselect(
    "Выберите блюдо", 
    options=all_dishes, 
    default=all_dishes,
    placeholder="Начните вводить название..."
)

# Фильтр негативных отзывов
negative_filter = st.sidebar.checkbox("Показать только негативные отзывы", value=False)

# Фильтрация данных с явной копией
filtered_df = df[
    (df['date'].dt.date >= date_range[0]) & 
    (df['date'].dt.date <= date_range[1]) &
    (df['dish'].isin(selected_dishes)) &
    (df['source'].isin(restaurants))
].copy()

# Выделение негативных отзывов
filtered_df['Negative'] = filtered_df['comment'].str.lower().str.contains("плохо|ужасно|невкусно|жутко", na=False)
if negative_filter:
    filtered_df = filtered_df[filtered_df['Negative']]

# Форматирование даты в таблице на DD.MM.YYYY
filtered_df['date'] = filtered_df['date'].dt.strftime("%d.%m.%Y")

# Таблица: Количество отзывов по блюдам
st.subheader("Отзывы по блюдам")
dish_counts = filtered_df.groupby('dish').size().reset_index(name='Количество отзывов')
dish_counts = dish_counts.sort_values('Количество отзывов', ascending=False)
st.dataframe(dish_counts, use_container_width=True)

# Круговая диаграмма: Распределение по ресторанам
st.subheader("Распределение отзывов по ресторанам")
restaurant_counts = filtered_df.groupby('source').size().reset_index(name='Количество')
fig_pie = px.pie(restaurant_counts, names='source', values='Количество', color='source',
                 color_discrete_map={'Restaurant 23': '#1f77b4', 'Restaurant 25': '#2ca02c', 'Restaurant 28': '#d62728'})
st.plotly_chart(fig_pie, use_container_width=True)

# Линейный график: Динамика отзывов по датам
st.subheader("Динамика отзывов по датам")
date_counts = filtered_df.groupby(filtered_df['date']).size().reset_index(name='Количество')
fig_line = px.line(date_counts, x='date', y='Количество', title="Отзывы по дням")
fig_line.update_xaxes(tickformat="%d.%m.%Y")
st.plotly_chart(fig_line, use_container_width=True)

# Подробная таблица с отзывами
st.subheader("Подробные отзывы")
st.dataframe(filtered_df[['date', 'comment', 'dish', 'source', 'Negative']], use_container_width=True)