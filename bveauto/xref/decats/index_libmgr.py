class IndexLibrary:
    def __init__(self, df):
        self.df = df

    def get_index(self, filename):
        row = self.df[self.df["파일명"] == filename]
        if row.empty:
            return None
        return int(row.iloc[0]["인덱스"])

    def get_path(self, filename):
        row = self.df[self.df["파일명"] == filename]
        if row.empty:
            return None
        return row.iloc[0]["경로"]

    def search(self, keyword):
        return self.df[self.df["파일명"].str.contains(keyword, na=False)]

    def get_name(self, index):
        row = self.df[self.df["인덱스"] == index]
        if row.empty:
            return None
        return row.iloc[0]["파일명"]
    def get_path_by_index(self, index):
        """인덱스 → 오브젝트 경로 (BVE Object 폴더 기준). 없으면 None"""
        if index is None:
            return None
        row = self.df[self.df["인덱스"] == index]
        if row.empty:
            return None
        path = row.iloc[0]["경로"]
        return path if isinstance(path, str) and path else None
