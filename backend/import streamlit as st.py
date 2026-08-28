import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator, MACD

# Sayfa Yapılandırması
st.set_page_config(page_title="Canlı Borsa & Analiz Paneli", layout="wide")

st.title("📈 Localhost Canlı Borsa & Algoritmik Sinyal Paneli")
st.caption("Not: Üretilen sinyaller teknik göstergelere dayalıdır, yatırım tavsiyesi değildir.")

# Yan Menü - Parametreler
st.sidebar.header("Hisse & Zaman Ayarları")
ticker_input = st.sidebar.text_input("Hisse Sembolü (Örn: THYAO.IS, GARAN.IS, AAPL, BTC-USD)", value="THYAO.IS")
period = st.sidebar.selectbox("Veri Aralığı", ["1d", "5d", "1mo", "3mo", "1y"], index=2)
interval = st.sidebar.selectbox("Mum Aralığı", ["1m", "5m", "15m", "60m", "1d"], index=2)

# Canlı Veri Çekme Fonksiyonu
@st.cache_data(ttl=15)
def get_stock_data(symbol, period_val, interval_val):
    data = yf.download(symbol, period=period_val, interval=interval_val)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data

data = get_stock_data(ticker_input, period, interval)

if not data.empty and len(data) > 30:
    # -------------------------------------------------------------
    # TEKNİK GÖSTERGE HESAPLAMALARI
    # -------------------------------------------------------------
    close_prices = data['Close']
    
    # RSI (14)
    rsi_ind = RSIIndicator(close=close_prices, window=14)
    data['RSI'] = rsi_ind.rsi()
    
    # Hareketli Ortalamalar (SMA 20 & SMA 50)
    data['SMA20'] = SMAIndicator(close=close_prices, window=20).sma_indicator()
    data['SMA50'] = SMAIndicator(close=close_prices, window=50).sma_indicator()
    
    # MACD
    macd_ind = MACD(close=close_prices)
    data['MACD'] = macd_ind.macd()
    data['MACD_Signal'] = macd_ind.macd_signal()
    
    # Son Değerler
    last_price = float(data['Close'].iloc[-1])
    last_rsi = float(data['RSI'].iloc[-1])
    last_sma20 = float(data['SMA20'].iloc[-1])
    last_sma50 = float(data['SMA50'].iloc[-1])
    last_macd = float(data['MACD'].iloc[-1])
    last_macd_signal = float(data['MACD_Signal'].iloc[-1])

    # -------------------------------------------------------------
    # SİNYAL & ANALİZ MOTORU
    # -------------------------------------------------------------
    signals = []
    
    # RSI Sinyali
    if last_rsi < 30:
        rsi_signal = "GÜÇLÜ AL (Aşırı Satımda)"
        signals.append("AL")
    elif last_rsi > 70:
        rsi_signal = "GÜÇLÜ SAT (Aşırı Alımda)"
        signals.append("SAT")
    else:
        rsi_signal = "NÖTR"
        
    # SMA Kesişimi
    if last_sma20 > last_sma50:
        sma_signal = "AL (Kısa Vade Trend Yukarı)"
        signals.append("AL")
    else:
        sma_signal = "SAT (Kısa Vade Trend Aşağı)"
        signals.append("SAT")
        
    # MACD Sinyali
    if last_macd > last_macd_signal:
        macd_signal = "AL (Momentum Pozitif)"
        signals.append("AL")
    else:
        macd_signal = "SAT (Momentum Negatif)"
        signals.append("SAT")

    # Genel Karar
    al_sayisi = signals.count("AL")
    sat_sayisi = signals.count("SAT")
    
    if al_sayisi >= 2:
        genel_karar = "🟢 AL SİNYALİ"
        karar_renk = "green"
    elif sat_sayisi >= 2:
        genel_karar = "🔴 SAT SİNYALİ"
        karar_renk = "red"
    else:
        genel_karar = "🟡 NÖTR / BEKLE"
        karar_renk = "orange"

    # -------------------------------------------------------------
    # ARAYÜZ (DASHBOARD)
    # -------------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Son Fiyat", f"{last_price:.2f} TL/$")
    col2.metric("RSI (14)", f"{last_rsi:.1f}")
    col3.metric("SMA 20 / 50", f"{last_sma20:.1f} / {last_sma50:.1f}")
    col4.metric("Otomatik Sistem Kararı", genel_karar)

    st.markdown("---")
    
    # Grafik Alanı
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'], high=data['High'],
        low=data['Low'], close=data['Close'],
        name="Fiyat"
    ))
    fig.add_trace(go.Scatter(x=data.index, y=data['SMA20'], line=dict(color='orange', width=1.5), name="SMA 20"))
    fig.add_trace(go.Scatter(x=data.index, y=data['SMA50'], line=dict(color='blue', width=1.5), name="SMA 50"))
    fig.update_layout(title=f"{ticker_input} Canlı Fiyat & Ortalamalar", xaxis_rangeslider_visible=False, height=500)
    st.plotly_chart(fig, use_container_width=True)

    # Detaylı Analiz Tablosu
    st.subheader("📋 Algoritmik Değerlendirme Özeti")
    analiz_df = pd.DataFrame({
        "Gösterge": ["RSI (14)", "SMA 20/50 Kesişimi", "MACD Momentum"],
        "Mevcut Değer": [f"{last_rsi:.2f}", f"SMA20: {last_sma20:.2f} | SMA50: {last_sma50:.2f}", f"MACD: {last_macd:.2f}"],
        "Üretilen Sinyal": [rsi_signal, sma_signal, macd_signal]
    })
    st.table(analiz_df)
    
else:
    st.error("Veri alınamadı veya girilen sembol geçersiz. Lütfen BIST için `.IS` uzantısını unutmayın (Örn: `THYAO.IS`).")