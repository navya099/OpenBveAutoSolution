# bveauto/utils.py
from pathlib import Path
import math

def get_block_index(current_track_position, block_interval = 25):
    """현재 트랙 위치를 블록 인덱스로 변환"""
    return math.floor(current_track_position / block_interval + 0.001) * block_interval

def create_txt(output_file, data):
    with open(output_file, 'w', encoding='utf-8') as file:
        for line in data:
            file.write(line + "\n")

def copy_post_assets(ctx, work: Path, source: Path, target: Path,
                     index_names: list[str]):
    """route에 index/post 복사 + target에 이미지/결과물 복사."""
    files = [work / n for n in index_names]
    copy_files(files, ctx.paths.route)

    copy_all_files(
        source, target,
        ['.jpg', '.jpeg'],
        ['.csv', '.png', '.txt'],
        delete_source=False, delete_target=False,
    )
    copy_all_files(
        work, target,
        ['.csv', '.png', '.txt', '.jpg', '.jpeg'],
        ['.dxf', '.ai'],
    )