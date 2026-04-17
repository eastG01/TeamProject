import sqlite3
import pandas as pd

def extract_to_csv():
    #  DB 연결
    conn = sqlite3.connect("hate_filter.db")
    
    
    # result가 보류 악플  추출
    query = """
        SELECT original_text AS sentence, 
               CASE WHEN result = '악플' THEN 1 ELSE 0 END AS label
        FROM filter_logs
        WHERE result IN ('악플', '보류', '정상')
    """
    
    # 데이터프레임으로 읽기
    df = pd.read_sql_query(query, conn)
    
    # CSV로 저장 (학습에 쓰기 좋은 형태)
    df.to_csv("train_data.csv", index=False, encoding="utf-8-sig")
    
    print(f"✅ 총 {len(df)}개의 로그를 'train_data.csv'로 추출했습니다!")
    conn.close()

if __name__ == "__main__":
    extract_to_csv()