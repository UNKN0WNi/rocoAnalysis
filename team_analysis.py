import tkinter as tk
from tkinter import ttk

# 属性克制关系数据 (攻击方属性 -> 效果)
# weak: 被克制(0.5倍), strong: 克制(2倍), resist: 抵抗(1.0倍, 显示为"其他")

ATTRIBUTES = ['普通', '草', '火', '水', '光', '地', '冰', '龙', '电', '毒', '虫', '武', '翼', '萌', '幽', '恶', '机械', '幻']

RELATIONS = {
    '普通': {'weak': [], 'strong': [], 'resist': '全属性'},
    '草': {'weak': ['火', '冰', '虫', '翼', '龙'], 'strong': ['水', '岩石', '地面', '毒'], 'resist': '其他'},
    '火': {'weak': ['水', '地面'], 'strong': ['草', '冰', '虫', '机械'], 'resist': '其他'},
    '水': {'weak': ['草', '电'], 'strong': ['火', '岩石', '地面', '机械'], 'resist': '其他'},
    '光': {'weak': ['幽', '恶'], 'strong': [], 'resist': '其他'},
    '地': {'weak': ['火', '电', '毒', '机械'], 'strong': ['草', '武'], 'resist': '其他'},
    '冰': {'weak': ['火', '地面', '武', '机械'], 'strong': ['草', '龙', '地面', '翼'], 'resist': '其他'},
    '龙': {'weak': ['草', '火', '水', '电', '翼'], 'strong': ['龙', '冰', '妖精'], 'resist': '其他'},
    '电': {'weak': ['地面'], 'strong': ['水', '翼'], 'resist': '其他'},
    '毒': {'weak': ['地', '恶', '幻'], 'strong': ['草', '萌'], 'resist': '其他'},
    '虫': {'weak': ['翼', '火'], 'strong': ['草', '恶', '幻'], 'resist': '其他'},
    '武': {'weak': ['毒', '虫', '翼', '萌', '幽', '幻'], 'strong': ['普通', '地', '冰', '恶', '机械'], 'resist': '其他'},
    '翼': {'weak': ['电', '冰', '岩石'], 'strong': ['草', '虫', '武'], 'resist': '其他'},
    '萌': {'weak': ['毒', '恶', '机械', '火', '龙'], 'strong': ['龙', '武', '恶'], 'resist': '水, 火, 草'},
    '幽': {'weak': ['光', '幽', '幻'], 'strong': ['普通', '毒', '虫', '武'], 'resist': '其他'},
    '恶': {'weak': ['光', '虫', '武', '萌'], 'strong': ['毒', '萌', '幽'], 'resist': '其他'},
    '机械': {'weak': ['火', '水', '电', '武'], 'strong': ['地', '冰', '萌'], 'resist': '普通, 草, 毒, 龙, 幽, 虫, 翼, 幻'},
    '幻': {'weak': ['光', '机械', '幻'], 'strong': ['虫', '幽'], 'resist': '其他'},
}


class TeamAnalysisApp:
    def __init__(self, root):
        self.root = root
        self.root.title("洛克王国队伍属性分析")
        self.root.geometry("800x700")

        self.selected_attrs = set()

        # Title
        tk.Label(root, text="洛克王国队伍属性分析", font=("Arial", 16, "bold")).pack(pady=10)

        # Team selection frame
        select_frame = tk.LabelFrame(root, text="选择队伍属性(可多选)", padx=15, pady=10)
        select_frame.pack(fill="x", padx=20, pady=5)

        self.var_dict = {}
        for i, attr in enumerate(ATTRIBUTES):
            var = tk.BooleanVar()
            self.var_dict[attr] = var
            cb = tk.Checkbutton(select_frame, text=attr, variable=var, font=("Arial", 11),
                               command=lambda a=attr: self.on_attr_toggle(a))
            cb.grid(row=i // 6, column=i % 6, sticky="w", padx=8, pady=3)

        # Selected team display
        self.team_label = tk.Label(root, text="已选队伍: 无", font=("Arial", 12))
        self.team_label.pack(pady=3)

        # Analyze button
        tk.Button(root, text="分析克制关系", font=("Arial", 13), command=self.analyze, bg="#4CAF50", fg="white", padx=15, pady=5).pack(pady=5)

        # Results frame - takes remaining space
        self.results_frame = tk.Frame(root, bg="#f5f5f5", relief="sunken", bd=2)
        self.results_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Scrollbar for results
        scroll_y = tk.Scrollbar(self.results_frame)
        scroll_y.pack(side="right", fill="y")

        self.canvas = tk.Canvas(self.results_frame, yscrollcommand=scroll_y.set,
                                bg="white", highlightthickness=1)
        self.canvas.pack(side="left", fill="both", expand=True)
        scroll_y.config(command=self.canvas.yview)

        self.results_inner = tk.Frame(self.canvas, bg="#f5f5f5")
        self.canvas.create_window((0, 0), window=self.results_inner, anchor="nw")

        # Update scroll region when inner frame size changes
        self.results_inner.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_frame_configure)

        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

    def on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_attr_toggle(self, attr):
        if self.var_dict[attr].get():
            self.selected_attrs.add(attr)
        else:
            self.selected_attrs.discard(attr)

        if self.selected_attrs:
            self.team_label.config(text=f"已选队伍: {', '.join(sorted(self.selected_attrs))}")
        else:
            self.team_label.config(text="已选队伍: 无")

    def analyze(self):
        # Clear previous results
        for widget in self.results_inner.winfo_children():
            widget.destroy()

        if not self.selected_attrs:
            tk.Label(self.results_inner, text="请先选择至少一个属性", font=("Arial", 14), bg="#f5f5f5").pack(pady=20)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            return

        # Calculate team advantages vs each attribute type
        # team_deals_2x[attr] = team deals 2x to attr
        # team_takes_2x[attr] = team takes 2x from attr
        team_deals_2x = set()
        team_takes_2x = set()

        for team_attr in self.selected_attrs:
            relations = RELATIONS[team_attr]
            # Team deals 2x to attrs in team's 克制 list
            team_deals_2x.update(relations['strong'])
            # Team takes 2x from attrs that have team_attr in their 克制 list (i.e., team is in their weak list)
            for other_attr in ATTRIBUTES:
                if team_attr in RELATIONS[other_attr]['strong']:
                    team_takes_2x.add(other_attr)

        # Categorize: only_strong (only deals 2x), only_weak (only takes 2x), both
        only_strong = team_deals_2x - team_takes_2x  # team deals 2x, takes 0.5x or 1x
        only_weak = team_takes_2x - team_deals_2x    # team takes 2x, deals 0.5x or 1x
        both = team_deals_2x & team_takes_2x          # both deal 2x to each other

        # Display results
        tk.Label(self.results_inner, text="队伍分析结果", font=("Arial", 16, "bold")).pack(pady=(10, 5))

        # Overall summary - three categories
        summary_frame = tk.LabelFrame(self.results_inner, text="综合克制情况", font=("Arial", 12, "bold"), padx=15, pady=10)
        summary_frame.pack(fill="x", pady=5, padx=10)

        if only_strong:
            tk.Label(summary_frame, text=f"✅ 只克制: {', '.join(sorted(only_strong))}",
                    font=("Arial", 13), fg="green", pady=4).pack(anchor="w")
        else:
            tk.Label(summary_frame, text="✅ 只克制: 无", font=("Arial", 13), pady=4).pack(anchor="w")

        if only_weak:
            tk.Label(summary_frame, text=f"❌ 只被克制: {', '.join(sorted(only_weak))}",
                    font=("Arial", 13), fg="red", pady=4).pack(anchor="w")
        else:
            tk.Label(summary_frame, text="❌ 只被克制: 无", font=("Arial", 13), pady=4).pack(anchor="w")

        if both:
            tk.Label(summary_frame, text=f"🔄 同时克制和被克制: {', '.join(sorted(both))}",
                    font=("Arial", 13), fg="darkorange", pady=4).pack(anchor="w")
        else:
            tk.Label(summary_frame, text="🔄 同时克制和被克制: 无", font=("Arial", 13), pady=4).pack(anchor="w")

        self.canvas.configure(scrollregion=self.canvas.bbox("all"))


if __name__ == "__main__":
    root = tk.Tk()
    app = TeamAnalysisApp(root)
    root.mainloop()