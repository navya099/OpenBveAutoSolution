# bveauto/gui.py
import tkinter as tk

from .runner import DEFAULT_INFO_STEP, SolutionRunner


def launch():
    root = tk.Tk()
    root.title("SolutionRunner GUI")

    log_box = tk.Text(root, height=15, width=70)
    log_box.pack()

    def log(msg: str):
        log_box.insert(tk.END, msg + "\n")
        log_box.see(tk.END)

    runner = SolutionRunner(log=log)

    # 입력 필드
    tk.Label(root, text="설계속도").pack()
    entry_speed = tk.Entry(root, width=20)
    entry_speed.insert(0, "150")
    entry_speed.pack()

    tk.Label(root, text="선로갯수").pack()
    entry_linecount = tk.Entry(root, width=20)
    entry_linecount.insert(0, "1")
    entry_linecount.pack()

    def safe_run(fn):
        # 입력 파싱 오류 시 스텝을 실행하지 않고 즉시 중단
        try:
            runner.configure(entry_speed.get(), entry_linecount.get())
        except ValueError as e:
            log(f"⚠️ {e}")
            return

        try:
            fn()
        except Exception as e:
            log(f"[중단] {e}")

    # 버튼
    tk.Button(
        root,
        text="전체실행",
        command=lambda: safe_run(runner.run_all),
    ).pack()

    tk.Button(
        root,
        text="기본정보 로드",
        command=lambda: safe_run(lambda: runner.run_step(DEFAULT_INFO_STEP)),
    ).pack()

    # 개별 단계 버튼 자동 생성
    for name in runner.step_names()[1:]:
        tk.Button(
            root,
            text=name,
            command=lambda n=name: safe_run(lambda: runner.run_step(n)),
        ).pack()

    tk.Button(
        root,
        text="로그 클리어",
        command=lambda: log_box.delete("1.0", tk.END),
    ).pack()
    tk.Button(root, text="종료", command=root.destroy).pack()

    root.mainloop()