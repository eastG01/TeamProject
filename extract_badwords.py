import sqlite3
import pandas as pd
import json

def make_learning_csv():
    # DB 연결
    conn = sqlite3.connect("hate_filter.db")
    cursor = conn.cursor()
    
    # 데이터 가져오기 (대표 단어와 변형 패턴들)
    query = "SELECT word, patterns FROM badwords"
    cursor.execute(query)
    rows = cursor.fetchall()
    
    learning_data = []
    
    for word, patterns_json in rows:
        # 대표 단어 추가 (Label 1)
        learning_data.append({"sentence": word, "label": 1})
        
        #  변형 패턴들 추가 (Label 1)
        try:
            patterns = json.loads(patterns_json)
            for p in patterns:
                # 중복 방지를 위해 대표 단어와 다를 때만 추가
                if p != word:
                    learning_data.append({"sentence": p, "label": 1})
        except:
            continue

    # 데이터프레임 생성 및 저장
    df = pd.DataFrame(learning_data)
    
    # 중복 데이터 제거 (깔끔한 학습을 위해)
    df = df.drop_duplicates(subset=['sentence'])
    
    # CSV 저장 (학습용이므로 utf-8로 저장)
    output_file = "badwords_train.csv"
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    
    print(f"✅ 학습용 데이터 생성 완료! 총 {len(df)}개의 문장이 '{output_file}'에 저장되었습니다.")
    print("-" * 30)
    print(df.head(10)) # 상위 10개 미리보기
    
    conn.close()

if __name__ == "__main__":
    make_learning_csv()