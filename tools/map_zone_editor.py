import matplotlib.pyplot as plt
import json
import os
import tkinter as tk
from tkinter import simpledialog, messagebox, Toplevel, Listbox, END, SINGLE
from matplotlib.patches import Polygon
from matplotlib.widgets import Button

# === 配置 ===
MAP_IMG_PATH = "de_mirage_radar.png"
OUTPUT_JSON = "mirage_zones.json"
CONFIG_FILE = "map_config.json"  # 读取校准参数

# 默认参数 (如果没有校准文件则用这个)
MAP_CONFIG = {
    "pos_x": -3230,
    "pos_y": 1713,
    "scale": 5.0
}

# 🔄 尝试加载校准参数
if os.path.exists(CONFIG_FILE):
    print(f"📥 正在加载校准参数: {CONFIG_FILE}")
    try:
        with open(CONFIG_FILE, 'r') as f:
            MAP_CONFIG = json.load(f)
    except:
        print("⚠️ 校准文件损坏，使用默认参数")
else:
    print("⚠️ 未找到 map_config.json，使用默认参数 (可能不准！)")


class ZoneEditorV5:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.fig, self.ax = plt.subplots(figsize=(12, 12))
        self.fig.canvas.manager.set_window_title('CS2 Zone Editor V5 (Calibrated)')

        # 加载地图
        if os.path.exists(MAP_IMG_PATH):
            img = plt.imread(MAP_IMG_PATH)
            self.ax.imshow(img)
        else:
            print("❌ 找不到图片")
            return

        self.current_points = []
        self.all_zones = {}
        self.zone_patches = {}
        self.zone_texts = {}
        self.temp_line = None
        self.panning = False
        self.pan_start = None

        # 加载旧数据
        if os.path.exists(OUTPUT_JSON):
            try:
                with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
                    self.all_zones = json.load(f)
                self.redraw_all_zones()
            except:
                pass

        # 事件绑定
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_drag)
        self.fig.canvas.mpl_connect('key_press_event', self.on_key)

        # 按钮
        ax_save = plt.axes([0.8, 0.01, 0.1, 0.04])
        self.btn_save = Button(ax_save, 'Save JSON')
        self.btn_save.on_clicked(self.save_json)

        ax_undo = plt.axes([0.65, 0.01, 0.1, 0.04])
        self.btn_undo = Button(ax_undo, 'Undo (Z)')
        self.btn_undo.on_clicked(self.undo_last_point)

        ax_manage = plt.axes([0.45, 0.01, 0.15, 0.04])
        self.btn_manage = Button(ax_manage, 'Manage/Delete')
        self.btn_manage.on_clicked(self.open_manager)

        print("\n=== ⚠️ 重要提示 ===")
        print("如果你刚刚更新了 map_config.json，你之前的画的圈位置肯定是错的！")
        print("请点击 [Manage/Delete] -> 删除所有旧区域 -> 【重新画】！")

        plt.show()

    def pixel_to_game(self, x_pix, y_pix):
        gx = MAP_CONFIG["pos_x"] + (x_pix * MAP_CONFIG["scale"])
        gy = MAP_CONFIG["pos_y"] - (y_pix * MAP_CONFIG["scale"])
        return gx, gy

    def game_to_pixel(self, gx, gy):
        x_pix = (gx - MAP_CONFIG["pos_x"]) / MAP_CONFIG["scale"]
        y_pix = (MAP_CONFIG["pos_y"] - gy) / MAP_CONFIG["scale"]
        return x_pix, y_pix

    def redraw_all_zones(self):
        for p in self.zone_patches.values(): p.remove()
        for t in self.zone_texts.values(): t.remove()
        self.zone_patches.clear()
        self.zone_texts.clear()

        for name, coords in self.all_zones.items():
            pixel_poly = [self.game_to_pixel(p[0], p[1]) for p in coords]
            poly = Polygon(pixel_poly, closed=True, alpha=0.3, color='cyan', edgecolor='white')
            self.ax.add_patch(poly)
            self.zone_patches[name] = poly

            cx = sum(p[0] for p in pixel_poly) / len(pixel_poly)
            cy = sum(p[1] for p in pixel_poly) / len(pixel_poly)
            text = self.ax.text(cx, cy, name, color='yellow', fontsize=8, ha='center', weight='bold')
            self.zone_texts[name] = text
        self.fig.canvas.draw_idle()

    def update_temp_line(self):
        if self.temp_line is None:
            self.temp_line, = self.ax.plot([], [], 'r+-', markersize=8)
        if self.current_points:
            xs, ys = zip(*self.current_points)
            self.temp_line.set_data(xs, ys)
        else:
            self.temp_line.set_data([], [])
        self.fig.canvas.draw_idle()

    def on_key(self, event):
        if event.key == 'z': self.undo_last_point(None)

    def undo_last_point(self, event):
        if self.current_points:
            self.current_points.pop()
            self.update_temp_line()

    def on_scroll(self, event):
        if event.inaxes != self.ax: return
        base_scale = 1.2
        scale_factor = 1 / base_scale if event.button == 'up' else base_scale
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()
        xdata, ydata = event.xdata, event.ydata
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])
        self.ax.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
        self.ax.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * rely])
        self.fig.canvas.draw_idle()

    def on_press(self, event):
        if event.inaxes != self.ax: return
        if event.button == 2:
            self.panning = True
            self.pan_start = (event.x, event.y)
        if event.button == 1:
            self.current_points.append((event.xdata, event.ydata))
            self.update_temp_line()
        elif event.button == 3 and len(self.current_points) >= 3:
            self.finish_polygon()

    def on_release(self, event):
        if event.button == 2:
            self.panning = False
            self.pan_start = None

    def on_drag(self, event):
        if self.panning and self.pan_start:
            dx = event.x - self.pan_start[0]
            dy = event.y - self.pan_start[1]
            self.pan_start = (event.x, event.y)
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            width, height = self.fig.canvas.get_width_height()
            dx_data = dx * (xlim[1] - xlim[0]) / width
            dy_data = dy * (ylim[1] - ylim[0]) / height
            self.ax.set_xlim(xlim[0] - dx_data, xlim[1] - dx_data)
            self.ax.set_ylim(ylim[0] - dy_data, ylim[1] - dy_data)
            self.fig.canvas.draw_idle()

    def finish_polygon(self):
        zone_name = simpledialog.askstring("区域命名", "请输入区域名称 (如 A_Default):", parent=self.root)
        if zone_name:
            game_coords = [self.pixel_to_game(p[0], p[1]) for p in self.current_points]
            self.all_zones[zone_name] = game_coords
            self.current_points = []
            self.update_temp_line()
            self.redraw_all_zones()

    def open_manager(self, event):
        top = Toplevel(self.root)
        top.title("Manage Zones")
        top.geometry("300x400")
        listbox = Listbox(top, selectmode=SINGLE)
        listbox.pack(fill=tk.BOTH, expand=True)
        for name in sorted(self.all_zones.keys()): listbox.insert(END, name)

        def delete_selected():
            sel = listbox.curselection()
            if not sel: return
            name = listbox.get(sel[0])
            del self.all_zones[name]
            listbox.delete(sel[0])
            self.redraw_all_zones()

        tk.Button(top, text="删除选中 (Delete)", command=delete_selected, bg="#ffdddd").pack()

    def save_json(self, event):
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(self.all_zones, f, indent=4, ensure_ascii=False)
        tk.messagebox.showinfo("成功", f"文件已保存至:\n{os.path.abspath(OUTPUT_JSON)}")


if __name__ == "__main__":
    ZoneEditorV5()