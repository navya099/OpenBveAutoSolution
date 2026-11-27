from bveauto.xref.decats.file_io.basedata_processor import safe_loader, parse_curve, parse_structure, parse_pitch, parse_polyline
import os
import pickle

def load_structure_data(file_path):
    return safe_loader(parse_structure, file_path, "구조물 데이터 로드 실패")

def load_curve_data(file_path):
    return safe_loader(parse_curve, file_path, "곡선 데이터 로드 실패")

def load_pitch_data(file_path):
    return safe_loader(parse_pitch, file_path, "기울기 데이터 로드 실패")

def load_coordinates(file_path):
    return safe_loader(parse_polyline, file_path, "좌표 데이터 로드 실패")

def write_to_file(filename, lines):
    """리스트 데이터를 파일에 저장하는 함수"""
    try:
        # 디렉토리 자동 생성
        dirname = os.path.dirname(filename)
        if dirname:  # 파일명만 주어진 경우 makedirs('') 에러 방지
            os.makedirs(dirname, exist_ok=True)

        with open(filename, "w", encoding="utf-8") as f:
            f.writelines(lines)  # 리스트 데이터를 한 번에 파일에 작성

        print(f"✅ 파일 저장 완료: {filename}")
    except Exception as e:
        print(f"⚠️ 파일 저장 중 오류 발생: {e}")

def save_poles(poles, filename="poles.dat"):
    with open(filename, "wb") as f:
        pickle.dump(poles, f)

def load_poles(filename="poles.dat"):
    with open(filename, "rb") as f:
        return pickle.load(f)

def save_runner(runner, filename="runner.dat", version=1):
    # runner 객체 자체를 저장 (tk 위젯은 pickle 불가하므로 저장 중에만 분리 후 복원)
    log_widget = getattr(runner, "log_widget", None)
    runner.log_widget = None
    try:
        with open(filename, "wb") as f:
            pickle.dump({
                "version": version,
                "runner": runner
            }, f)
    finally:
        runner.log_widget = log_widget

def load_runner(filename="runner.dat"):
    with open(filename, "rb") as f:
        data = pickle.load(f)
    return data["runner"]

