"""사용자(PC)별 설정 — 저장소 밖 ~/.decatsbve/settings.json

PC마다 다른 경로(예: BVE Object 폴더)를 코드에 고정하지 않고 여기에 저장한다.
환경변수 DECATSBVE_SETTINGS 로 파일 위치를 바꿀 수 있다 (테스트용).
"""
import json
import os

DEFAULTS = {
    # 미리보기·도면 저장에 쓰는 BVE Object 폴더 (이전 코드에 고정돼 있던 경로)
    'bve_object_root': r'D:\BVE\루트\Railway\Object',
}


def settings_path():
    return os.environ.get('DECATSBVE_SETTINGS') or os.path.join(os.path.expanduser('~'), '.decatsbve',
                                                                'settings.json')


def load():
    """설정 전체 (파일이 없거나 깨졌으면 기본값)"""
    data = dict(DEFAULTS)
    try:
        with open(settings_path(), encoding='utf-8') as f:
            stored = json.load(f)
        if isinstance(stored, dict):
            data.update(stored)
    except (OSError, ValueError):
        pass
    return data


def get(key):
    return load().get(key, DEFAULTS.get(key))


def set(key, value):  # noqa: A001 - settings.set(key, value)
    data = load()
    data[key] = value
    path = settings_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
