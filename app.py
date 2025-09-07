import streamlit as st
import pandas as pd
from vnstock import * # Sử dụng các hàm từ thư viện vnstock
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ------------------------------------------------------------------------------
# CẤU HÌNH TRANG WEB
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Chứng Khoán Việt Nam",
    page_icon="📈",
    layout="wide"
)

# ------------------------------------------------------------------------------
# CÁC HÀM LẤY DỮ LIỆU (VỚI CACHING)
# ------------------------------------------------------------------------------

# Cache để không cần tải lại danh sách mã CK mỗi lần tương tác
@st.cache_data(ttl=3600) # Cache trong 1 giờ
def get_stock_list():
    """Lấy danh sách tất cả các mã chứng khoán từ sàn."""
    try:
        companies = listing_companies()
        return companies['ticker'].tolist()
    except Exception as e:
        st.error(f"Lỗi khi lấy danh sách mã chứng khoán: {e}")
        return []

# Cache dữ liệu giá lịch sử để vẽ biểu đồ
@st.cache_data(ttl=60) # Cache trong 60 giây
def get_historical_data(symbol, days_to_fetch=365):
    """Lấy dữ liệu lịch sử của một mã chứng khoán."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_to_fetch)
        df = stock_historical_data(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), "1D")
        if df is not None and not df.empty:
            df.set_index('time', inplace=True)
            df.index = pd.to_datetime(df.index)
            return df
    except Exception as e:
        st.error(f"Lỗi khi lấy dữ liệu lịch sử cho {symbol}: {e}")
    return pd.DataFrame()

# Cache dữ liệu giá hiện tại
@st.cache_data(ttl=30) # Cache trong 30 giây
def get_quote_data(symbol):
    """Lấy thông tin giá gần real-time."""
    try:
        quote = stock_quote(symbol)
        return quote
    except Exception as e:
        st.error(f"Lỗi khi lấy dữ liệu giá cho {symbol}: {e}")
        return pd.DataFrame()

# Cache dữ liệu top tăng/giảm giá
@st.cache_data(ttl=60) # Cache trong 60 giây
def get_top_movers():
    """Lấy danh sách top cổ phiếu tăng/giảm/giao dịch nhiều nhất."""
    try:
        gainers = market_top_mover('gainers', 5)
        losers = market_top_mover('losers', 5)
        return gainers, losers
    except Exception as e:
        st.error(f"Lỗi khi lấy dữ liệu top movers: {e}")
        return pd.DataFrame(), pd.DataFrame()

# ------------------------------------------------------------------------------
# HÀM VẼ BIỂU ĐỒ
# ------------------------------------------------------------------------------
def plot_candlestick(df, symbol):
    """Vẽ biểu đồ nến bằng Plotly."""
    if df.empty:
        return go.Figure()

    fig = go.Figure(data=[go.Candlestick(x=df.index,
                                           open=df['open'],
                                           high=df['high'],
                                           low=df['low'],
                                           close=df['close'],
                                           name=symbol)])

    fig.update_layout(
        title=f'Biểu đồ nến cho mã {symbol.upper()}',
        xaxis_title='Thời gian',
        yaxis_title='Giá (VND)',
        xaxis_rangeslider_visible=False,
        template='plotly_dark'
    )
    return fig

# ------------------------------------------------------------------------------
# KHỞI TẠO SESSION STATE
# ------------------------------------------------------------------------------
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ['VNM', 'FPT', 'HPG']

# ------------------------------------------------------------------------------
# GIAO DIỆN NGƯỜI DÙNG (UI)
# ------------------------------------------------------------------------------

# --- SIDEBAR ---
with st.sidebar:
    st.title("📈 Dashboard Chứng Khoán")
    st.markdown("---")

    # Lấy danh sách mã chứng khoán
    stock_list = get_stock_list()
    
    # Chọn mã chứng khoán chính
    selected_stock = st.selectbox("Chọn mã cổ phiếu", stock_list, index=stock_list.index('VNM') if 'VNM' in stock_list else 0)

    st.markdown("---")

    # Quản lý Watchlist
    st.header("Watchlist")
    new_stock = st.text_input("Thêm mã vào Watchlist", "").upper()
    if st.button("Thêm mã"):
        if new_stock and new_stock in stock_list and new_stock not in st.session_state.watchlist:
            st.session_state.watchlist.append(new_stock)
            st.success(f"Đã thêm {new_stock} vào watchlist!")
        elif new_stock in st.session_state.watchlist:
            st.warning(f"{new_stock} đã có trong watchlist.")
        else:
            st.error(f"Mã {new_stock} không hợp lệ.")
    
    # Hiển thị và xóa mã khỏi watchlist
    if st.session_state.watchlist:
        for stock in st.session_state.watchlist:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info(stock)
            with col2:
                if st.button("Xóa", key=f"del_{stock}"):
                    st.session_state.watchlist.remove(stock)
                    st.rerun()

    # Nút refresh dữ liệu
    st.markdown("---")
    if st.button("Làm mới dữ liệu"):
        st.cache_data.clear()
        st.success("Đã làm mới dữ liệu!")


# --- MAIN CONTENT ---
st.title(f"Thông tin cổ phiếu: {selected_stock.upper()}")

# Lấy dữ liệu cho mã đã chọn
quote_df = get_quote_data(selected_stock)

# Hiển thị thông tin giá
if not quote_df.empty:
    price_info = quote_df.iloc[0]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Giá hiện tại", f"{price_info['priceCurrent']:,}", f"{price_info['priceChange']:,} ({price_info['priceChangeRatio']:.2f}%)")
    col2.metric("Giá tham chiếu", f"{price_info['referencePrice']:,}")
    col3.metric("Giá cao nhất", f"{price_info['highPrice']:,}")
    col4.metric("Khối lượng", f"{price_info['totalVolume']:,}")
else:
    st.warning("Không thể tải thông tin giá cho mã này.")

# Hiển thị biểu đồ nến
hist_data = get_historical_data(selected_stock)
if not hist_data.empty:
    st.plotly_chart(plot_candlestick(hist_data, selected_stock), use_container_width=True)
else:
    st.warning("Không có dữ liệu lịch sử để vẽ biểu đồ.")


st.markdown("---")
st.header("Tổng quan thị trường")

# Lấy và hiển thị top tăng/giảm
gainers, losers = get_top_movers()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Top 5 tăng giá")
    st.dataframe(gainers, use_container_width=True)

with col2:
    st.subheader("Top 5 giảm giá")
    st.dataframe(losers, use_container_width=True)