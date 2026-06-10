import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

# UTF-8 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

# 한글 데이터 생성을 위한 설정
np.random.seed(42)

# 데이터 디렉토리 생성
os.makedirs('data', exist_ok=True)

# 1. 기기마스터 데이터 (기본정보)
print("1. 기기마스터 데이터 생성 중...")
equipment_ids = [f'EQ{i:04d}' for i in range(1, 301)]
equipment_names = []
locations = ['공장A-1층', '공장A-2층', '공장A-3층', '공장B-1층', '공장B-2층', '창고-1층', '창고-2층']
manufacturers = ['삼성중공업', '현대중공업', 'LS산전', '효성', '두산중공업', '한화Q셀', '케이시']
equipment_types = ['펌프', '컴프레서', '모터', '밸브', '냉각기', '열교환기', '분사기', '센서', '제어판', '변압기']

for i in range(300):
    eq_type = np.random.choice(equipment_types)
    eq_name = f"{eq_type}-{i % 30 + 1}"
    equipment_names.append(eq_name)

master_data = pd.DataFrame({
    '기기ID': equipment_ids,
    '기기명': equipment_names,
    '기기유형': np.random.choice(equipment_types, 300),
    '설치위치': np.random.choice(locations, 300),
    '제조사': np.random.choice(manufacturers, 300),
    '모델명': [f'MOD-{np.random.randint(100, 9999)}' for _ in range(300)],
    '설치일자': [f'2020-{np.random.randint(1,13):02d}-{np.random.randint(1,29):02d}' for _ in range(300)],
    '정격용량': [round(x, 2) for x in np.random.uniform(50, 500, 300)],
    '기기상태': np.random.choice(['정상', '주의', '경고', '부분결함'], 300, p=[0.6, 0.2, 0.1, 0.1])
})

master_data.to_csv('data/기기마스터.csv', index=False, encoding='utf-8-sig')
print(f"✓ 기기마스터.csv 생성 ({len(master_data)} 행)")

# 2. 점검기록 데이터
print("2. 점검기록 데이터 생성 중...")
inspection_records = []
start_date = datetime(2023, 1, 1)

for eq_id in equipment_ids:
    # 각 기기별로 5~15회 점검 기록 생성
    num_inspections = np.random.randint(5, 16)
    for j in range(num_inspections):
        inspection_date = start_date + timedelta(days=np.random.randint(0, 600))

        inspection_records.append({
            '기기ID': eq_id,
            '점검일자': inspection_date.strftime('%Y-%m-%d'),
            '점검항목': np.random.choice(['외관검사', '소음진동', '온도측정', '유량측정', '압력검사', '절연저항', '전류측정'], 1)[0],
            '측정값': round(np.random.uniform(10, 100), 2),
            '측정단위': np.random.choice(['°C', 'dB', 'A', 'L/min', 'bar', 'MΩ'], 1)[0],
            '점검결과': np.random.choice(['정상', '주의', '경고', '불량'], 1, p=[0.7, 0.15, 0.1, 0.05])[0],
            '담당자': np.random.choice(['김철수', '이영희', '박준호', '최민준', '정수현'], 1)[0],
            '비고': np.random.choice(['', '부품교체필요', '윤활유 추가', '청소완료', '조정완료'], 1)[0]
        })

inspection_df = pd.DataFrame(inspection_records)
inspection_df = inspection_df.sort_values(['기기ID', '점검일자']).reset_index(drop=True)
inspection_df.to_csv('data/점검기록.csv', index=False, encoding='utf-8-sig')
print(f"✓ 점검기록.csv 생성 ({len(inspection_df)} 행)")

# 3. 유지보수기록 데이터
print("3. 유지보수기록 데이터 생성 중...")
maintenance_records = []

for eq_id in equipment_ids:
    # 각 기기별로 2~8회 유지보수 기록 생성
    num_maintenance = np.random.randint(2, 9)
    for j in range(num_maintenance):
        maintenance_date = start_date + timedelta(days=np.random.randint(0, 600))

        maintenance_records.append({
            '기기ID': eq_id,
            '유지보수일자': maintenance_date.strftime('%Y-%m-%d'),
            '유지보수유형': np.random.choice(['예방정비', '사후정비', '개선정비', '응급정비'], 1)[0],
            '작업내용': np.random.choice(['청소 및 점검', '윤활유 교체', '부품 교체', '조정 및 수리', '전기 점검'], 1)[0],
            '소요시간(시간)': np.random.randint(1, 8),
            '비용(원)': np.random.randint(50000, 500000),
            '담당자': np.random.choice(['김철수', '이영희', '박준호', '최민준', '정수현'], 1)[0],
            '완료상태': np.random.choice(['완료', '진행중', '예정'], 1, p=[0.85, 0.1, 0.05])[0]
        })

maintenance_df = pd.DataFrame(maintenance_records)
maintenance_df = maintenance_df.sort_values(['기기ID', '유지보수일자']).reset_index(drop=True)
maintenance_df.to_csv('data/유지보수기록.csv', index=False, encoding='utf-8-sig')
print(f"✓ 유지보수기록.csv 생성 ({len(maintenance_df)} 행)")

# 4. 부품교체이력 데이터
print("4. 부품교체이력 데이터 생성 중...")
parts = ['베어링', '씰', '임펠러', '권선', '케이싱', '밸브시트', '피스톤', '로드', '필터', '스프링']
replacement_records = []

for eq_id in equipment_ids:
    # 각 기기별로 1~5회 부품교체 기록 생성
    num_replacements = np.random.randint(1, 6)
    for j in range(num_replacements):
        replacement_date = start_date + timedelta(days=np.random.randint(0, 600))

        replacement_records.append({
            '기기ID': eq_id,
            '교체일자': replacement_date.strftime('%Y-%m-%d'),
            '부품명': np.random.choice(parts, 1)[0],
            '부품규격': f'{np.random.randint(10, 100)}mm',
            '교체수량': np.random.randint(1, 5),
            '부품비(원)': np.random.randint(10000, 200000),
            '공임(원)': np.random.randint(20000, 100000),
            '교체사유': np.random.choice(['노후', '손상', '마모', '성능저하', '정기교체'], 1)[0],
            '담당자': np.random.choice(['김철수', '이영희', '박준호', '최민준', '정수현'], 1)[0]
        })

replacement_df = pd.DataFrame(replacement_records)
replacement_df = replacement_df.sort_values(['기기ID', '교체일자']).reset_index(drop=True)
replacement_df.to_csv('data/부품교체이력.csv', index=False, encoding='utf-8-sig')
print(f"✓ 부품교체이력.csv 생성 ({len(replacement_df)} 행)")

# 5. 월별기기상태 데이터 (대시보드 시계열 분석용)
print("5. 월별기기상태 데이터 생성 중...")
status_records = []
months = pd.date_range(start='2023-01-01', end='2025-12-31', freq='ME')

for month in months:
    for eq_id in np.random.choice(equipment_ids, 150, replace=False):
        status_records.append({
            '연월': month.strftime('%Y-%m'),
            '기기ID': eq_id,
            '가동시간(시간)': round(np.random.uniform(200, 800), 2),
            '평균온도(℃)': round(np.random.uniform(20, 60), 1),
            '평균압력(bar)': round(np.random.uniform(1, 10), 2),
            '에러발생횟수': np.random.randint(0, 5),
            '종합상태': np.random.choice(['정상', '주의', '경고'], 1, p=[0.7, 0.2, 0.1])[0]
        })

status_df = pd.DataFrame(status_records)
status_df = status_df.sort_values(['연월', '기기ID']).reset_index(drop=True)
status_df.to_csv('data/월별기기상태.csv', index=False, encoding='utf-8-sig')
print(f"✓ 월별기기상태.csv 생성 ({len(status_df)} 행)")

# 6. 기기이력카드 통합 (각 기기별 최신 정보)
print("6. 기기이력카드 통합 데이터 생성 중...")
history_card = master_data.copy()

# 최근 점검 정보 추가
latest_inspection = inspection_df.sort_values('점검일자').groupby('기기ID').tail(1)
latest_inspection = latest_inspection[['기기ID', '점검일자', '점검항목', '점검결과']].rename(
    columns={'점검일자': '최근점검일자', '점검항목': '최근점검항목', '점검결과': '최근점검결과'}
)
history_card = history_card.merge(latest_inspection, on='기기ID', how='left')

# 최근 유지보수 정보 추가
latest_maintenance = maintenance_df.sort_values('유지보수일자').groupby('기기ID').tail(1)
latest_maintenance = latest_maintenance[['기기ID', '유지보수일자', '유지보수유형']].rename(
    columns={'유지보수일자': '최근유지보수일자', '유지보수유형': '최근유지보수유형'}
)
history_card = history_card.merge(latest_maintenance, on='기기ID', how='left')

# 총 유지보수비용
total_cost = maintenance_df.copy()
total_cost['총비용'] = total_cost['비용(원)']
total_cost = total_cost.groupby('기기ID')['총비용'].sum().reset_index()
history_card = history_card.merge(total_cost, on='기기ID', how='left').fillna(0)

history_card.to_csv('data/기기이력카드.csv', index=False, encoding='utf-8-sig')
print(f"✓ 기기이력카드.csv 생성 ({len(history_card)} 행)")

print("\n" + "="*50)
print("✅ 모든 데이터 생성 완료!")
print("="*50)
print("\n생성된 파일:")
print("  📄 기기마스터.csv - 기기 기본정보 (300개)")
print("  📄 점검기록.csv - 점검 이력 (2,700+ 행)")
print("  📄 유지보수기록.csv - 유지보수 이력 (1,500+ 행)")
print("  📄 부품교체이력.csv - 부품 교체 기록 (900+ 행)")
print("  📄 월별기기상태.csv - 월별 상태 추이 (5,400+ 행)")
print("  📄 기기이력카드.csv - 통합 현황 카드 (300개)")
print("\n위치: ./data/ 폴더")
