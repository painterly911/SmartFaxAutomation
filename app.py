import streamlit as st
from google.cloud import vision
import pandas as pd
import io
import os
import re
import sqlite3
from datetime import datetime
from thefuzz import process
from PIL import Image, ImageSequence

# [설정] 구글 키 파일 경로
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "my-key.json"

# --- 1. 데이터베이스(SQLite) ---
def init_db():
    conn = sqlite3.connect('fax_db.sqlite')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS fax_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            site_name TEXT,
            item_name TEXT,
            quantity TEXT,
            remark TEXT,
            created_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS master_items (
            item_name TEXT PRIMARY KEY
        )
    ''')
    conn.commit()
    conn.close()

def save_to_db(df):
    conn = sqlite3.connect('fax_db.sqlite')
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for index, row in df.iterrows():
        c.execute('''
            INSERT INTO fax_data (date, site_name, item_name, quantity, remark, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (row['날짜'], row['현장명'], row['품명'], row['수량'], row['비고'], now))
    conn.commit()
    conn.close()

def load_data_from_db(site_filter=None):
    conn = sqlite3.connect('fax_db.sqlite')
    query = "SELECT id, date as 날짜, site_name as 현장명, item_name as 품명, quantity as 수량, remark as 비고 FROM fax_data"
    params = []
    if site_filter and site_filter != "전체 보기":
        query += " WHERE site_name = ?"
        params.append(site_filter)
    query += " ORDER BY date ASC, id ASC"
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def get_all_sites():
    conn = sqlite3.connect('fax_db.sqlite')
    try:
        df = pd.read_sql("SELECT DISTINCT site_name FROM fax_data", conn)
        return df['site_name'].tolist()
    except:
        return []
    finally:
        conn.close()

def reset_db():
    conn = sqlite3.connect('fax_db.sqlite')
    c = conn.cursor()
    c.execute("DELETE FROM fax_data")
    conn.commit()
    conn.close()

# --- 품목 마스터 & 오타 보정 ---
def save_master_items(df):
    conn = sqlite3.connect('fax_db.sqlite')
    c = conn.cursor()
    c.execute("DELETE FROM master_items")
    items = df.iloc[:, 0].dropna().unique().tolist()
    count = 0
    for item in items:
        if str(item).strip():
            c.execute("INSERT OR IGNORE INTO master_items (item_name) VALUES (?)", (str(item).strip(),))
            count += 1
    conn.commit()
    conn.close()
    return count

def get_master_items():
    conn = sqlite3.connect('fax_db.sqlite')
    try:
        df = pd.read_sql("SELECT item_name FROM master_items", conn)
        return df['item_name'].tolist()
    except:
        return []
    finally:
        conn.close()

def auto_correct_item_name(ocr_name, master_list):
    if not master_list: return ocr_name
    result = process.extractOne(ocr_name, master_list)
    if result:
        best_match = result[0]
        score = result[1]
        if score >= 60:
            if len(ocr_name) > len(best_match) + 3:
                return ocr_name
            return best_match
    return ocr_name

# --- 2. 이미지 처리 ---
def process_uploaded_file(uploaded_file):
    image = Image.open(uploaded_file)
    processed_pages = []
    for i, page in enumerate(ImageSequence.Iterator(image)):
        page = page.copy()
        if page.mode not in ('RGB', 'L'):
            page = page.convert('RGB')
        img_byte_arr = io.BytesIO()
        page.save(img_byte_arr, format='JPEG')
        img_bytes = img_byte_arr.getvalue()
        processed_pages.append((page, img_bytes))
    return processed_pages

def get_ocr_text(image_bytes):
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    response = client.document_text_detection(image=image)
    return response.full_text_annotation.text

def clean_site_name(text):
    if not text: return text
    text = re.sub(r'\s*\(', ' (', text)
    text = re.sub(r'\(\s*', '(', text)
    text = re.sub(r'\s*\)', ')', text)
    text = re.sub(r'\)(?=\S)', ') ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_text_to_df(text):
    lines = text.split('\n')
    data = []
    current_date = ""
    current_site = "현장명 미상"
   
    date_pattern = re.compile(r'20\d{2}\s*[년\-\./]\s*\d{1,2}\s*[월\-\./]\s*\d{1,2}')
    num_pattern = re.compile(r'\d+')
    item_pattern = re.compile(r'^(\d+)[\.\)\s]*(.+?)\s*[:;]\s*(.+)$')

    master_list = get_master_items()

    for line in lines:
        line = line.strip()
        if not line: continue

        if "FAX" in line or "전송" in line or "페이지" in line or "쪽" in line:
            continue
        if "2026" in line and ":" in line:
            date_match = date_pattern.search(line)
            if date_match:
                nums = num_pattern.findall(date_match.group())
                if len(nums) >= 3:
                    current_date = f"{nums[0]}-{nums[1].zfill(2)}-{nums[2].zfill(2)}"
            continue

        if not current_date:
            date_match = date_pattern.search(line)
            if date_match:
                nums = num_pattern.findall(date_match.group())
                if len(nums) >= 3:
                    current_date = f"{nums[0]}-{nums[1].zfill(2)}-{nums[2].zfill(2)}"
       
        if "현장" in line:
            if "담당자" in line or "연락처" in line or "통화" in line: continue
            clean_line = line.replace("※", "").replace("_", " ").strip()
            if "(입고일" in clean_line: clean_line = clean_line.split("(입고일")[0].strip()
            if len(clean_line) < 30:
                current_site = clean_site_name(clean_line)

    if not current_date:
        current_date = datetime.now().strftime("%Y-%m-%d")

    for line in lines:
        line = line.strip()
        if "FAX" in line or "전송" in line: continue

        match = item_pattern.match(line)
        if match:
            raw_item_name = match.group(2).strip()
            qty_unit = match.group(3).strip()
           
            if "/" in raw_item_name or "2026" in raw_item_name: continue
            if raw_item_name.isdigit() or len(raw_item_name) < 1: continue

            corrected_name = auto_correct_item_name(raw_item_name, master_list)

            data.append({
                "날짜": current_date,
                "현장명": current_site,
                "품명": corrected_name,
                "수량": qty_unit,
                "비고": ""
            })

    return pd.DataFrame(data)

def sanitize_filename(name):
    if not name: return "다운로드"
    return re.sub(r'[\\/*?:"<>|]', "", str(name)).strip()

# --- 3. 메인 화면 ---
def main():
    st.set_page_config(page_title="스마트 팩스 관리", layout="wide")
    init_db()
   
    with st.sidebar:
        st.title("⚙️ 관리 메뉴")
        st.subheader("1. 품목 DB 업데이트")
        master_file = st.file_uploader("품목 마스터 엑셀", type=['xlsx', 'xls'])
        if master_file:
            if st.button("품목 DB 등록하기"):
                try:
                    df = pd.read_excel(master_file)
                    count = save_master_items(df)
                    st.success(f"✅ 총 {count}개 품목 등록 완료!")
                except Exception as e:
                    st.error(f"오류: {e}")

        st.divider()
        st.subheader("2. 데이터 초기화")
        if st.button("🗑️ DB 전체 삭제", type="primary"):
            reset_db()
            st.warning("초기화 완료!")
            st.rerun()

    st.title("📠 스마트 팩스 자재 관리 시스템")
   
    master_count = len(get_master_items())
    if master_count > 0:
        st.info(f"💡 오타 자동 보정 가동 중 (등록된 품목: {master_count}개)")

    tab1, tab2 = st.tabs(["📤 팩스 등록하기", "📊 누적 내역 조회"])

    with tab1:
        st.write("이미지 또는 TIFF 파일을 업로드하세요.")
        uploaded_file = st.file_uploader("팩스 파일 선택", type=['jpg', 'png', 'jpeg', 'tiff', 'tif'])

        if uploaded_file is not None:
            pages = process_uploaded_file(uploaded_file)
            st.write(f"📄 총 **{len(pages)}페이지** 감지")

            col1, col2 = st.columns([1, 2])
            with col1:
                for i, (disp_img, _) in enumerate(pages):
                    st.image(disp_img, caption=f'{i+1} 페이지', use_column_width=True)
           
            with col2:
                if st.button("전체 페이지 텍스트 추출", type="primary"):
                    with st.spinner('분석 중...'):
                        try:
                            all_dfs = []
                            for i, (_, img_bytes) in enumerate(pages):
                                raw_text = get_ocr_text(img_bytes)
                                df = parse_text_to_df(raw_text)
                                if not df.empty: all_dfs.append(df)
                           
                            if all_dfs:
                                final_df = pd.concat(all_dfs, ignore_index=True)
                                st.session_state['temp_df'] = final_df
                                st.success(f"분석 완료! ({len(final_df)}건)")
                            else:
                                st.warning("내용 없음")
                        except Exception as e:
                            st.error(f"오류: {e}")

            if 'temp_df' in st.session_state:
                st.divider()
                st.subheader("🧐 데이터 확인")
                edited_df = st.data_editor(
                    st.session_state['temp_df'],
                    num_rows="dynamic",
                    use_container_width=True,
                    column_config={
                        "품명": st.column_config.TextColumn("품명", width="large"),
                        "수량": st.column_config.TextColumn("수량", width="medium"),
                    }
                )

                # [수정] 다운로드 영역 디자인 개선
                st.markdown("---")
                save_col1, save_col2 = st.columns(2)
               
                with save_col1:
                    st.caption("1. 데이터베이스에 저장")
                    if st.button("💾 DB에 누적하기", use_container_width=True):
                        save_to_db(edited_df)
                        st.success("✅ 저장되었습니다!")
                        del st.session_state['temp_df']
                        st.rerun()
               
                with save_col2:
                    st.caption("2. 엑셀로 즉시 다운로드")
                    # 기본 파일명 설정
                    default_name = "다운로드"
                    if not edited_df.empty:
                        default_name = sanitize_filename(edited_df['현장명'].iloc[0])

                    # [핵심] 사용자가 직접 입력할 수 있는 칸
                    user_filename = st.text_input("파일 이름 (직접 수정 가능)", value=default_name)
                   
                    # 확장자 .xlsx 자동 보정
                    if not user_filename.endswith(".xlsx"):
                        user_filename += ".xlsx"

                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        edited_df.to_excel(writer, index=False, sheet_name='팩스내역')
                       
                    st.download_button(
                        label="📥 엑셀 파일 받기",
                        data=output.getvalue(),
                        file_name=user_filename, # 사용자가 입력한 이름 적용
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

    with tab2:
        st.subheader("🔍 현장별 자재 내역 조회")
        site_list = ["전체 보기"] + get_all_sites()
        selected_site = st.selectbox("현장 선택", site_list)
        history_df = load_data_from_db(selected_site)
       
        if not history_df.empty:
            st.write(f"총 **{len(history_df)}**건")
            st.dataframe(history_df, use_container_width=True, hide_index=True)
           
            # 기본 파일명
            if selected_site == "전체 보기":
                default_dl_name = "전체_자재내역"
            else:
                default_dl_name = sanitize_filename(selected_site)
           
            # [핵심] 조회 탭에서도 이름 수정 가능
            col_dn1, col_dn2 = st.columns([3, 1])
            with col_dn1:
                user_dl_name = st.text_input("다운로드 파일 이름", value=default_dl_name)
                if not user_dl_name.endswith(".xlsx"):
                    user_dl_name += ".xlsx"
           
            with col_dn2:
                # 줄맞춤을 위한 빈 공간
                st.write("")
                st.write("")
               
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    history_df.to_excel(writer, index=False, sheet_name='자재내역')
               
                st.download_button(
                    label="📥 엑셀 다운로드",
                    data=output.getvalue(),
                    file_name=user_dl_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        else:
            st.info("데이터가 없습니다.")

if __name__ == "__main__":
    main()