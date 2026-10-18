import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Analisis SUT Sumut 2025", page_icon="📊", layout="wide")
st.title("📊 Dashboard Analisis Supply and Use Tables (SUT)")
st.markdown("**Provinsi Sumatera Utara (105 Komoditas x 83 Lapangan Usaha)**")

# Sidebar Upload
st.sidebar.header("📁 Upload Data SUT")
st.sidebar.markdown("Silakan upload file Excel `1200 SUT Provinsi Sumatera Utara Tahun 2025... .xlsx`")
uploaded_file = st.sidebar.file_uploader("Upload File Excel (.xlsx)", type=["xlsx"])

@st.cache_data
def load_sut_data(file):
    try:
        # ==========================================
        # 1. TABEL USE & SUPPLY (105 Komoditas)
        # ==========================================
        df_use = pd.read_excel(file, sheet_name=0, skiprows=5, nrows=105, usecols="D,DH,DI", header=None)
        df_use.columns = ["Komoditas", "Total_Permintaan_Akhir", "Total_Use"]

        df_supply = pd.read_excel(file, sheet_name=0, skiprows=5, nrows=105, usecols="GQ,GR,HA,HI,HM", header=None)
        df_supply.columns = ["Output_Domestik", "Supply_ADH_Dasar", "Impor_dll", "Pajak_kurang_Subsidi", "Total_Supply"]

        df_komoditas = pd.concat([df_use, df_supply], axis=1)

        cols_numeric = ["Total_Permintaan_Akhir", "Total_Use", "Output_Domestik", "Supply_ADH_Dasar", "Impor_dll", "Pajak_kurang_Subsidi", "Total_Supply"]
        for col in cols_numeric:
            df_komoditas[col] = pd.to_numeric(df_komoditas[col], errors='coerce').fillna(0)
            
        df_komoditas["Diskrepansi"] = df_komoditas["Total_Supply"] - df_komoditas["Total_Use"]

        # ==========================================
        # 2. NILAI TAMBAH BRUTO (83 Industri)
        # ==========================================
        df_nama_industri = pd.read_excel(file, sheet_name=0, skiprows=3, nrows=1, header=None)
        df_ntb_row = pd.read_excel(file, sheet_name=0, skiprows=119, nrows=1, header=None)
        
        nama_industri = df_nama_industri.iloc[0, 4:87].values
        ntb_series = pd.to_numeric(df_ntb_row.iloc[0, 4:87], errors='coerce').fillna(0)
        
        df_industri = pd.DataFrame({
            "Industri": nama_industri,
            "NTB": ntb_series.values
        })
        
        df_industri = df_industri.dropna(subset=['Industri'])
        df_industri['Industri'] = df_industri['Industri'].astype(str).str.replace('\n', ' ')

        return df_komoditas, df_industri

    except Exception as e:
        st.error(f"Error membaca file: Detail: {e}")
        return None, None


if uploaded_file is not None:
    with st.spinner("Mengekstrak Matriks SUT (105 Komoditas x 83 Industri)..."):
        df_komoditas, df_industri = load_sut_data(uploaded_file)
    
    if df_komoditas is not None:
        st.sidebar.success("Data berhasil diproses!")
        
        # ==========================================
        # PERHITUNGAN AGREGAT PDRB
        # ==========================================
        total_ntb_dasar = df_industri["NTB"].sum()                       # CK119
        total_pajak_subsidi = df_komoditas["Pajak_kurang_Subsidi"].sum() # HJ111
        total_permintaan_akhir = df_komoditas["Total_Permintaan_Akhir"].sum() # DI111 (atau DH sesuai kolom)
        total_impor = df_komoditas["Impor_dll"].sum()                    # HA111
        
        # 1. PDRB Lapangan Usaha = NTB Harga Dasar + Pajak dikurang Subsidi Produk
        pdrb_lapangan_usaha = total_ntb_dasar + total_pajak_subsidi
        
        # 2. PDRB Pengeluaran = Total Permintaan Akhir - Total Impor
        pdrb_pengeluaran = total_permintaan_akhir - total_impor
        
        # Cek Selisih PDRB
        selisih_pdrb = pdrb_lapangan_usaha - pdrb_pengeluaran
        
        # Variabel untuk Sankey
        total_output = df_komoditas["Output_Domestik"].sum()
        total_supply = df_komoditas["Total_Supply"].sum()
        total_use = df_komoditas["Total_Use"].sum()
        total_input_antara = total_use - total_permintaan_akhir

        # ==========================================
        # TABS DASHBOARD
        # ==========================================
        tab1, tab2, tab3, tab4 = st.tabs([
            "🌊 Makroekonomi & Aliran SUT", "🏭 PDRB Lapangan Usaha (Ranking)", "📦 Profil Komoditas", "⚖️ Balancing Tracker"
        ])
        
        # --- TAB 1: MAKROEKONOMI & ALIRAN SANKEY ---
        with tab1:
            st.subheader("Ringkasan Makroekonomi Sumatera Utara")
            def format_rupiah(val): return f"Rp {val:,.2f}"
            
            # Menampilkan PDRB Pendekatan Lapangan Usaha vs Pengeluaran
            col_pu, col_pe, col_diff = st.columns(3)
            col_pu.metric("PDRB (Lapangan Usaha)", format_rupiah(pdrb_lapangan_usaha), help="Total NTB + Pajak dikurang Subsidi")
            col_pe.metric("PDRB (Pengeluaran)", format_rupiah(pdrb_pengeluaran), help="Permintaan Akhir - Impor")
            
            # Alert jika PDRB tidak balance
            if abs(selisih_pdrb) > 1: # Toleransi pembulatan 1 juta
                col_diff.metric("Diskrepansi PDRB", format_rupiah(selisih_pdrb), delta_color="inverse")
                st.error(f"⚠️ Peringatan: PDRB Lapangan Usaha dan PDRB Pengeluaran belum seimbang. Selisih: {format_rupiah(selisih_pdrb)}")
            else:
                col_diff.metric("Status Makro", "Seimbang / Balanced", delta_color="normal")
                st.success("✅ PDRB Agregat sudah seimbang antara sisi Lapangan Usaha dan Pengeluaran.")
            
            st.divider()
            
            st.markdown("#### Analisis Aliran Supply dan Use (Sankey Diagram)")
            fig_sankey = go.Figure(data=[go.Sankey(
                valueformat = ",.0f",
                valuesuffix = " Juta",
                node = dict(
                  pad = 20, thickness = 30,
                  line = dict(color = "black", width = 0.5),
                  label = ["Output Domestik", "Impor & Margin", "Pajak - Subsidi", 
                           "TOTAL MARKET SUPPLY", 
                           "Input Antara (Industri)", "Permintaan Akhir (Konsumsi, PMTB, Ekspor)"],
                  color = ["#1f77b4", "#ff7f0e", "#2ca02c", "#7f7f7f", "#9467bd", "#d62728"]
                ),
                link = dict(
                  source = [0, 1, 2, 3, 3],
                  target = [3, 3, 3, 4, 5],
                  value =  [total_output, total_impor, total_pajak_subsidi, 
                            total_input_antara, total_permintaan_akhir]
              ))])
            
            fig_sankey.update_layout(height=500, font_size=12, title_text="Aliran Penyediaan dan Penggunaan SUT")
            st.plotly_chart(fig_sankey, use_container_width=True)

        # --- TAB 2: PDRB LAPANGAN USAHA (RANKING) ---
        with tab2:
            st.subheader("Kontribusi 83 Lapangan Usaha Terhadap NTB")
            
            df_ind_sorted = df_industri.sort_values(by="NTB", ascending=False).reset_index(drop=True)
            df_ind_sorted.index = df_ind_sorted.index + 1
            
            col_chart, col_table = st.columns([2, 1])
            
            with col_chart:
                fig_bar_all = px.bar(
                    df_ind_sorted, x="NTB", y="Industri", orientation='h',
                    color="NTB", color_continuous_scale="Blues",
                    height=900, title="Perankingan NTB 83 Industri"
                )
                fig_bar_all.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_bar_all, use_container_width=True)
                
            with col_table:
                st.markdown("**Tabel Ranking NTB**")
                st.dataframe(df_ind_sorted.style.format({"NTB": "{:,.2f}"}), use_container_width=True, height=900)

        # --- TAB 3: PROFIL KOMODITAS ---
        with tab3:
            st.subheader("Profil Sisi Supply dan Use 105 Komoditas")
            fig_scatter = px.scatter(
                df_komoditas, x="Output_Domestik", y="Total_Permintaan_Akhir", 
                hover_name="Komoditas", size="Total_Supply", color="Pajak_kurang_Subsidi",
                color_continuous_scale="RdBu", title="Output Domestik vs Permintaan Akhir per Komoditas"
            )
            fig_scatter.update_layout(height=600)
            st.plotly_chart(fig_scatter, use_container_width=True)

        # --- TAB 4: BALANCING TRACKER ---
        with tab4:
            st.subheader("Tracker Keseimbangan 105 Komoditas")
            df_bal = df_komoditas[["Komoditas", "Total_Supply", "Total_Use", "Diskrepansi"]].copy()
            
            def highlight_diff(val):
                if pd.isna(val): return ''
                return 'color: #ff4b4b; font-weight: bold;' if abs(val) > 0.1 else 'color: #00cc66;'
            
            jml_unbalanced = df_bal[abs(df_bal['Diskrepansi']) > 0.1].shape[0]
            st.warning(f"⚠️ Terdapat **{jml_unbalanced}** dari 105 Komoditas yang selisihnya > 0.1")
            
            st.dataframe(
                df_bal.style.map(highlight_diff, subset=['Diskrepansi']).format("{:,.2f}", subset=["Total_Supply", "Total_Use", "Diskrepansi"]),
                use_container_width=True, height=600
            )

else:
    st.info("👋 Silakan upload file SUT (1200 SUT Provinsi Sumatera Utara Tahun 2025... .xlsx) di sidebar sebelah kiri.")
