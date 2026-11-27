# 오브젝트 파일 인코딩: UTF-8(BOM 포함) 먼저, 안 되면 한국어 윈도 기본(CP949)
ENCODINGS = ('utf-8-sig', 'cp949')


class FileController:
    def __init__(self, path: str | None = None):
        self.path = path
        self.lines: list[str] = []
        self.encoding = None

    def set_path(self, path: str):
        self.path = path

    def load(self):
        if not self.path:
            raise ValueError("파일 경로가 설정되지 않았습니다.")
        with open(self.path, 'rb') as f:
            raw = f.read()
        for encoding in ENCODINGS:
            try:
                text = raw.decode(encoding)
            except UnicodeDecodeError:
                continue
            self.encoding = encoding
            self.lines = text.splitlines(True)
            return
        raise UnicodeDecodeError('utf-8/cp949', raw, 0, len(raw), f'{self.path}: 인코딩을 알 수 없습니다')

    def get_lines(self) -> list[str]:
        return self.lines
