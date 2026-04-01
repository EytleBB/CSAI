import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

# === 文件配置 ===
ZONES_FILE = "mirage_zones.json"  # 读取区域名字
WEIGHTS_FILE = "zone_weights.json"  # 保存优先级配置

# === 战术等级定义 ===
LEVELS = {
    1: {"label": "🛡️ 常规防守 (Level 1)", "color": "black", "desc": "普通站位，除非高频出现，否则不报。"},
    2: {"label": "⚔️ 关键控图 (Level 2)", "color": "#e6b800", "desc": "中路、B小等交火区，值得关注。"},
    3: {"label": "🚨 高危前压 (Level 3)", "color": "red", "desc": "CT不该在的地方，出现即警报！"}
}


class PriorityManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CS2 Zone Priority Manager")
        self.root.geometry("600x450")

        # 数据容器
        self.zone_names = []
        self.current_weights = {}  # { "A_Triple": 1, ... }

        # 加载数据
        self.load_data()

        # === 界面布局 ===
        # 左侧：列表框
        left_frame = tk.Frame(self.root, padx=10, pady=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left_frame, text="已定义区域列表:", font=("Arial", 10, "bold")).pack(anchor="w")

        # 带滚动条的列表
        scrollbar = tk.Scrollbar(left_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(left_frame, height=20, font=("Consolas", 11), yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)

        self.listbox.bind('<<ListboxSelect>>', self.on_select)

        # 右侧：控制区
        right_frame = tk.Frame(self.root, padx=20, pady=20, bg="#f0f0f0")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, ipadx=20)

        tk.Label(right_frame, text="设置优先级", bg="#f0f0f0", font=("Arial", 12, "bold")).pack(pady=10)

        self.selected_zone_var = tk.StringVar(value="请选择区域")
        tk.Label(right_frame, textvariable=self.selected_zone_var, bg="#f0f0f0", fg="blue").pack(pady=5)

        # 单选按钮变量
        self.priority_var = tk.IntVar(value=1)

        # 生成三个等级的选项
        for level, info in LEVELS.items():
            frame = tk.Frame(right_frame, bg="#f0f0f0")
            frame.pack(fill=tk.X, pady=5)

            rb = tk.Radiobutton(
                frame,
                text=info["label"],
                variable=self.priority_var,
                value=level,
                bg="#f0f0f0",
                font=("Arial", 10),
                command=self.update_current_selection
            )
            rb.pack(anchor="w")

            # 描述文字
            tk.Label(frame, text=info["desc"], bg="#f0f0f0", fg="gray", font=("Arial", 8)).pack(anchor="w", padx=22)

        # 保存按钮
        tk.Button(
            right_frame,
            text="💾 保存配置 (Save JSON)",
            command=self.save_weights,
            bg="#4CAF50", fg="white", font=("Arial", 10, "bold"),
            height=2
        ).pack(side=tk.BOTTOM, fill=tk.X, pady=20)

        # 刷新列表显示
        self.refresh_list()
        self.root.mainloop()

    def load_data(self):
        # 1. 读取区域名
        if os.path.exists(ZONES_FILE):
            with open(ZONES_FILE, 'r', encoding='utf-8') as f:
                self.zone_names = sorted(list(json.load(f).keys()))
        else:
            messagebox.showerror("错误", f"找不到 {ZONES_FILE}，请先运行 map_zone_editor 画图！")
            self.root.destroy()
            return

        # 2. 读取已有权重
        if os.path.exists(WEIGHTS_FILE):
            try:
                with open(WEIGHTS_FILE, 'r', encoding='utf-8') as f:
                    self.current_weights = json.load(f)
            except:
                self.current_weights = {}

        # 确保所有区域都有默认值
        for name in self.zone_names:
            if name not in self.current_weights:
                self.current_weights[name] = 1

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for name in self.zone_names:
            weight = self.current_weights.get(name, 1)
            # 根据权重加前缀图标
            prefix = "🛡️"
            fg_color = "black"

            if weight == 3:
                prefix = "🚨"
                fg_color = "red"
            elif weight == 2:
                prefix = "⚔️"
                fg_color = "#CC9900"  # 深黄色

            self.listbox.insert(tk.END, f"{prefix} {name}")
            # 给这一行上色
            self.listbox.itemconfig(tk.END, {'fg': fg_color})

    def on_select(self, event):
        # 获取选中的索引
        if not self.listbox.curselection(): return

        index = self.listbox.curselection()[0]
        full_text = self.listbox.get(index)
        # 去掉前缀图标获取纯名字
        zone_name = full_text.split(" ", 1)[1]

        self.selected_zone_var.set(zone_name)

        # 更新单选框状态
        weight = self.current_weights.get(zone_name, 1)
        self.priority_var.set(weight)

    def update_current_selection(self):
        # 当点击单选框时，更新内存数据
        zone_name = self.selected_zone_var.get()
        if zone_name == "请选择区域": return

        new_weight = self.priority_var.get()
        self.current_weights[zone_name] = new_weight

        # 刷新列表颜色的最快方法：记录当前选中的位置，刷新，再选回去
        cur_sel = self.listbox.curselection()
        self.refresh_list()
        if cur_sel:
            self.listbox.select_set(cur_sel[0])

    def save_weights(self):
        try:
            with open(WEIGHTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.current_weights, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("成功", f"配置已保存至 {WEIGHTS_FILE}")
        except Exception as e:
            messagebox.showerror("错误", str(e))


if __name__ == "__main__":
    PriorityManager()