import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="Dashboard Analisis SUT Sumut 2025", page_icon="📊", layout="wide")
st.title("📊 Dashboard Analisis Supply and Use Tables (SUT)")
st.markdown("**Provinsi Sumatera Utara (83 Komoditas x 105 Lapangan Usaha)**")

st.sidebar.header("📁 Upload Data SUT")
st.sidebar.markdown("Silakan upload file Excel `1200 SUT Provinsi Sumatera Utara Tahun 2025... .xlsx`")
uploaded_file = st.sidebar.file_uploader("Upload File Excel (.xlsx)", type=["xlsx"])

@st.cache_data
def load_sut_data(file):
    try:
        # --- TABEL USE ---
        # 1. Baris 6 hingga 110 (Index pandas 5 - 109) merepresentasikan Komoditas (83 baris)
        # 2. Kolom D = Nama Sektor (kita anggap sebagai kolom komoditas/industri untuk sumbu Y)
        # 3. Kolom CK hingga DG (Komponen Pengeluaran), DH (Total Permintaan Akhir), DI (Total Use)
        # Menggunakan kolom spesifik berdasar huruf Excel:
        # D: Komoditas, DH: Permintaan Akhir, DI: Total Use Harga Pembeli
        cols_use = "D,DH,DI"
        df_use = pd.read_excel(file, sheet_name=0, skiprows=5, nrows=83, usecols=cols_use, header=None)
        df_use.columns = ["Komoditas", "Total_Permintaan_Akhir", "Total_Use"]

        # --- TABEL SUPPLY ---
        # 1. Kolom DL (Nama Sektor), GQ (Output Domestik), GR (Supply ADH Dasar), 
        #    HA (Impor/Komponen), HI (Total Pajak - Subsidi), 
        #    Margin Transpor (Berdasarkan gambar, asumsikan HK/HL), HM (Total Supply ADH Pembeli)
        # *Catatan: Pandas usecols harus string berurutan atau list integer. Kita pakai urutan huruf Excel.
        cols_supply = "DL,GQ,GR,HA,HI,HM"
        df_supply = pd.read_excel(file, sheet_name=0, skiprows=5, nrows=83, usecols=cols_supply, header=None)
        df_supply.columns = ["Komoditas_Supply", "Output_Domestik", "Supply_ADH_Dasar", 
                             "Impor_dll", "Pajak_kurang_Subsidi", "Total_Supply"]

        # Menggabungkan Supply dan Use berdasarkan baris (karena urutannya sama)
        df_komoditas = pd.concat([df_use, df_supply.drop(columns=["Komoditas_Supply"])], axis=1)

        # Konversi ke numerik
        for col in ["Total_Permintaan_Akhir", "Total_Use", "Output_Domestik", 
                    "Supply_ADH_Dasar", "Impor_dll", "Pajak_kurang_Subsidi", "Total_Supply"]:
            df_komoditas[col] = pd.to_numeric(df_komoditas[col], errors='coerce').fillna(0)
            
        df_komoditas["Diskrepansi"] = df_komoditas["Total_Supply"] - df_komoditas["Total_Use"]

        # --- NILAI TAMBAH BRUTO (NTB) ---
        # Baris 120 (Index 119) di Excel adalah Nilai Tambah Bruto
        # Kolom E hingga CI (Ada 83 kolom industri, namun Anda menyebut 105 sektor awal, 
        # mari asumsikan kita ambil rentang kolom E (index 4) sampai CI (index 86) untuk industri).
        # Nama sektor di baris 5 (Index 4)
        df_nama_industri = pd.read_excel(file, sheet_name=0, skiprows=4, nrows=1, header=None)
        df_ntb_row = pd.read_excel(file, sheet_name=0, skiprows=119, nrows=1, header=None)
        
        # Ambil nama industri (E s.d. CI) -> Indeks pandas 4 s.d. 86
        nama_industri = df_nama_industri.iloc[0, 4:87].values
        ntb_values = df_ntb_row.iloc[0, 4:87].values
        
        df_industri = pd.DataFrame({
            "Industri": nama_industri,
            "NTB": pd.to_numeric(ntb_values, errors='coerce').fillna(0)
        })
        
        df_industri = df_industri.dropna(subset=['Industri'])
        df_industri['Industri'] = df_industri['Industri'].astype(str).str.replace('\n', ' ')

        return df_komoditas, df_industri

    except Exception as e:
        st.error(f"Error membaca file: Periksa struktur sel Excel. Detail: {e}")
        return None, None

if uploaded_file is not None:
    with st.spinner("Memproses Matriks SUT 83x105..."):
        df_komoditas, df_industri = load_sut_data(uploaded_file)
    
    if df_komoditas is not None:
        st.sidebar.success("Data Matriks SUT berhasil diekstrak!")
        
        # Agregasi Makro
        total_pdrb = df_industri["NTB"].sum()
        total_output = df_komoditas["Output_Domestik"].sum()
        total_supply = df_komoditas["Total_Supply"].sum()
        total_use = df_komoditas["Total_Use"].sum()
        total_permintaan_akhir = df_komoditas["Total_Permintaan_Akhir"].sum()
        total_pajak_subsidi = df_komoditas["Pajak_kurang_Subsidi"].sum()
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 Indikator Makro", "🏭 Analisis Industri (NTB)", "📦 Profil Komoditas", "⚖️ Balancing Matriks"
        ])
        
        # --- TAB 1: MAKROEKONOMI ---
        with tab1:
            st.subheader("Ringkasan Makroekonomi Sumatera Utara")
            def f_curr(v): return f"Rp {v:,.0f}"
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("PDRB (Total NTB Industri)", f_curr(total_pdrb))
            c2.metric("Total Output Domestik", f_curr(total_output))
            c3.metric("Total Pajak - Subsidi Produk", f_curr(total_pajak_subsidi))
            c4.metric("Total Permintaan Akhir", f_curr(total_permintaan_akhir))
            
            st.divider()
            st.markdown("#### Struktur Pembentuk SUT (Agregat)")
            fig_sankey = go.Figure(data=[go.Sankey(
                node=dict(
                    pad=15, thickness=20,
                    line=dict(color="black", width=0.5),
                    label=["Output Domestik", "Impor & Lainnya", "Pajak-Subsidi & Margin", 
                           "TOTAL SUPPLY / USE", "Permintaan Antara", "Permintaan Akhir"],
                    color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
                ),
                link=dict(
                    source=[0, 1, 2, 3, 3],
                    target=[3, 3, 3, 4, 5],
                    value=[total_output, total_supply - total_output - total_pajak_subsidi, total_pajak_subsidi,
                           total_use - total_permintaan_akhir, total_permintaan_akhir]
                )
            )])
            fig_sankey.update_layout(height=450)
            st.plotly_chart(fig_sankey, use_container_width=True)

        # --- TAB 2: INDUSTRI (NTB) ---
        with tab2:
            st.subheader("Penciptaan Nilai Tambah Bruto (NTB) per Industri")
            top_ind = df_industri.sort_values(by="NTB", ascending=False).head(15)
            fig_bar = px.bar(top_ind, y="Industri", x="NTB", orientation='h',
                             title="Top 15 Industri Penyumbang NTB Terbesar",
                             color="NTB", color_continuous_scale="Blues", text_auto='.2s')
            fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_bar, use_container_width=True)

        # --- TAB 3: KOMODITAS ---
        with tab3:
            st.subheader("Analisis Sisi Supply dan Use per Komoditas")
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Top 10 Komoditas Output Domestik Terbesar**")
                top_out = df_komoditas.sort_values(by="Output_Domestik", ascending=False).head(10)
                fig_out = px.pie(top_out, values="Output_Domestik", names="Komoditas", hole=0.3)
                st.plotly_chart(fig_out, use_container_width=True)
            with col_b:
                st.markdown("**Top 10 Komoditas dengan Permintaan Akhir Tertinggi**")
                top_pa = df_komoditas.sort_values(by="Total_Permintaan_Akhir", ascending=False).head(10)
                fig_pa = px.pie(top_pa, values="Total_Permintaan_Akhir", names="Komoditas", hole=0.3)
                st.plotly_chart(fig_pa, use_container_width=True)

        # --- TAB 4: BALANCING ---
        with tab4:
            st.subheader("Balancing Matriks (Supply vs Use)")
            df_bal = df_komoditas[["Komoditas", "Total_Supply", "Total_Use", "Diskrepansi"]].copy()
            
            def color_diff(val):
                if pd.isna(val): return ''
                return 'color: #ff4b4b; font-weight: bold;' if abs(val) > 0.1 else 'color: #00cc66;'
            
            unbalanced = df_bal[abs(df_bal['Diskrepansi']) > 0.1].shape[0]
            st.warning(f"⚠️ Terdapat **{unbalanced}** dari 83 Komoditas yang belum *balance* (Selisih > 0.1)")
            
            st.dataframe(df_bal.style.map(color_diff, subset=['Diskrepansi']).format("{:,.2f}", subset=["Total_Supply", "Total_Use", "Diskrepansi"]), use_container_width=True, height=500)

else:
    st.info("Silakan upload file Excel Matriks SUT 83x105 di sidebar.")
