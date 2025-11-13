import tkinter as tk
from tkinter import messagebox
import random

# ===== 預設設定（可用老師設定視窗調整） =====

DEFAULT_MAX_PER_GROUP = 100  # 預設每組 100 人

DEFAULT_GROUPS = [
    {"emoji": "🎄", "name": "聖誕樹學院"},
    {"emoji": "🦌", "name": "馴鹿學院"},
    {"emoji": "⭐", "name": "星光學院"},
]

WINDOW_TITLE = "聖誕分類帽分組系統"
TITLE_FONT = ("Microsoft JhengHei", 22, "bold")
MAIN_FONT = ("Microsoft JhengHei", 18)
LABEL_FONT = ("Microsoft JhengHei", 14)
SMALL_FONT = ("Microsoft JhengHei", 12)


class SortingHatApp:
    def __init__(self, master):
        self.master = master
        master.title(WINDOW_TITLE)
        master.geometry("950x550")

        # 狀態變數
        self.max_per_group = DEFAULT_MAX_PER_GROUP
        self.groups_info = [g.copy() for g in DEFAULT_GROUPS]  # list of dict
        self.groups_members = []  # list[list[str]]
        self.group_labels = []    # label 顯示每組成員

        # ===== 上方標題 + 設定按鈕 =====
        top_frame = tk.Frame(master)
        top_frame.pack(fill=tk.X, pady=5)

        self.title_label = tk.Label(
            top_frame,
            text="聖誕數位分類帽 · 現場分組",
            font=TITLE_FONT
        )
        self.title_label.pack(side=tk.LEFT, padx=10, pady=5)

        self.settings_button = tk.Button(
            top_frame,
            text="老師設定 ⚙",
            font=("Microsoft JhengHei", 12),
            command=self.open_settings_window
        )
        self.settings_button.pack(side=tk.RIGHT, padx=10)

        # ===== 輸入名字區 =====
        input_frame = tk.Frame(master)
        input_frame.pack(pady=5)

        self.name_label = tk.Label(
            input_frame,
            text="請輸入你的名字：",
            font=LABEL_FONT
        )
        self.name_label.pack(side=tk.LEFT, padx=5)

        self.name_entry = tk.Entry(
            input_frame,
            font=LABEL_FONT,
            width=18
        )
        self.name_entry.pack(side=tk.LEFT, padx=5)

        self.sort_button = tk.Button(
            master,
            text="我要被分類！",
            font=("Microsoft JhengHei", 16, "bold"),
            command=self.assign_group
        )
        self.sort_button.pack(pady=10)

        # ===== 顯示結果（大字） =====
        self.result_label = tk.Label(
            master,
            text="等待下一位勇者上前…",
            font=MAIN_FONT,
            fg="#333333"
        )
        self.result_label.pack(pady=10)

        # 分隔線
        separator = tk.Frame(master, height=2, bg="#cccccc")
        separator.pack(fill=tk.X, pady=5)

        # ===== 下方各組成員區 =====
        self.groups_frame = tk.Frame(master)
        self.groups_frame.pack(pady=5, fill=tk.BOTH, expand=True)

        # 初始化分組資料與畫面
        self.reset_groups()

        # 讓 Enter 也可以觸發分類
        master.bind("<Return>", lambda event: self.assign_group())

    # ========= 分組核心邏輯 =========

    def reset_groups(self):
        """依照目前 groups_info & max_per_group 重建分組狀態與畫面。"""
        # 清空成員資料
        self.groups_members = [[] for _ in self.groups_info]

        # 先清掉舊的 group 顯示
        for widget in self.groups_frame.winfo_children():
            widget.destroy()

        self.group_labels = []

        # 重新畫每一組的框
        for idx, group in enumerate(self.groups_info):
            frame = tk.Frame(
                self.groups_frame,
                bd=1,
                relief=tk.SOLID,
                padx=6,
                pady=6
            )
            frame.grid(row=0, column=idx, padx=8, pady=5, sticky="n")

            title_text = f"{group.get('emoji', '')} {group.get('name', '未命名學院')}"
            title = tk.Label(
                frame,
                text=title_text.strip(),
                font=LABEL_FONT
            )
            title.pack()

            subtitle = tk.Label(
                frame,
                text=f"(上限 {self.max_per_group} 人)",
                font=SMALL_FONT,
                fg="#555555"
            )
            subtitle.pack()

            members_label = tk.Label(
                frame,
                text="（尚未有人）",
                font=SMALL_FONT,
                justify=tk.LEFT
            )
            members_label.pack(anchor="w", pady=5)

            self.group_labels.append(members_label)

    def assign_group(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showinfo("提醒", "請先輸入名字再讓分類帽工作喔。")
            return

        # 檢查是否所有組都已滿
        available_indices = []
        counts = []
        for i, members in enumerate(self.groups_members):
            if len(members) < self.max_per_group:
                available_indices.append(i)
                counts.append(len(members))

        if not available_indices:
            messagebox.showinfo("完成", "所有聖誕學院都已經滿座了！")
            return

        # 在還沒滿的組當中，挑「目前人數最少」的那些，再隨機選一組
        min_count = min(counts)
        candidate_indices = [
            idx for idx in available_indices
            if len(self.groups_members[idx]) == min_count
        ]
        chosen_index = random.choice(candidate_indices)

        # 加入該組
        self.groups_members[chosen_index].append(name)
        group_info = self.groups_info[chosen_index]
        group_name = group_info.get("name", "未命名學院")
        group_emoji = group_info.get("emoji", "")

        # 更新結果顯示
        show_text = f"{name} 被分配到：{group_emoji}《{group_name}》！"
        self.result_label.config(text=show_text)

        # 清空輸入框
        self.name_entry.delete(0, tk.END)
        self.name_entry.focus()

        # 更新下方名單
        self.refresh_group_labels()

    def refresh_group_labels(self):
        for i, members in enumerate(self.groups_members):
            if members:
                text = "\n".join(f"{idx + 1}. {name}" for idx, name in enumerate(members))
            else:
                text = "（尚未有人）"
            self.group_labels[i].config(text=text)

    # ========= 老師設定視窗 =========

    def open_settings_window(self):
        settings = tk.Toplevel(self.master)
        settings.title("老師設定")
        settings.geometry("500x420")

        info_label = tk.Label(
            settings,
            text="※ 調整完後按「套用設定並重設分組」\n（會清空目前所有已分配的學生）",
            font=SMALL_FONT,
            justify=tk.LEFT,
            fg="#444444"
        )
        info_label.pack(pady=10)

        # 每組上限設定
        max_frame = tk.Frame(settings)
        max_frame.pack(pady=5, fill=tk.X, padx=15)

        max_label = tk.Label(
            max_frame,
            text="每組人數上限：",
            font=LABEL_FONT
        )
        max_label.pack(side=tk.LEFT)

        self.max_entry_var = tk.StringVar(value=str(self.max_per_group))
        max_entry = tk.Entry(
            max_frame,
            textvariable=self.max_entry_var,
            font=LABEL_FONT,
            width=6
        )
        max_entry.pack(side=tk.LEFT, padx=5)

        # 組別設定說明
        groups_label = tk.Label(
            settings,
            text="學院設定（每行一組：表情符號 + 空格 + 名稱）",
            font=LABEL_FONT
        )
        groups_label.pack(pady=(15, 5))

        # 預設文字：把目前 groups_info 展開
        lines = []
        for g in self.groups_info:
            emoji = g.get("emoji", "")
            name = g.get("name", "")
            line = (emoji + " " + name).strip()
            if line:
                lines.append(line)
        default_text = "\n".join(lines) if lines else "🎄 聖誕樹學院\n🦌 馴鹿學院\n⭐ 星光學院"

        self.groups_text = tk.Text(
            settings,
            font=SMALL_FONT,
            height=10,
        )
        self.groups_text.pack(padx=15, pady=5, fill=tk.BOTH, expand=True)
        self.groups_text.insert("1.0", default_text)

        # 套用設定按鈕
        apply_button = tk.Button(
            settings,
            text="套用設定並重設分組",
            font=LABEL_FONT,
            command=lambda: self.apply_settings(settings)
        )
        apply_button.pack(pady=10)

    def apply_settings(self, settings_window):
        # 讀取每組上限
        max_str = self.max_entry_var.get().strip()
        try:
            new_max = int(max_str)
            if new_max <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("錯誤", "每組人數上限請輸入正整數。")
            return

        # 讀取學院行
        raw_text = self.groups_text.get("1.0", tk.END).strip()
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        new_groups = []
        for line in lines:
            # 解析：第一個「空白」前當作 emoji，後面當作名字
            parts = line.split(None, 1)  # 以空白切成最多兩段
            if len(parts) == 1:
                emoji = ""
                name = parts[0]
            else:
                emoji, name = parts
            if not name:
                continue
            new_groups.append({"emoji": emoji, "name": name})

        if not new_groups:
            messagebox.showerror("錯誤", "至少需要設定一個學院。")
            return

        # 確認要重設
        if not messagebox.askyesno(
            "確認",
            "套用新設定會清空目前所有分組結果，確定要繼續嗎？"
        ):
            return

        # 套用新設定
        self.max_per_group = new_max
        self.groups_info = new_groups

        # 重建分組狀態與畫面
        self.reset_groups()

        # 更新主畫面提示
        self.result_label.config(text="設定已更新，等待下一位勇者上前…")

        # 關閉設定視窗
        settings_window.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = SortingHatApp(root)
    root.mainloop()
