import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import io

class TalentDashboardChatBot:
    def __init__(self, root):
        self.root = root
        self.root.title("Talent Dashboard ChatBot")
        self.root.geometry("1000x700")

        self.df = None

        self.create_widgets()

    def create_widgets(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Excel File:").pack(side=tk.LEFT)
        self.file_path = tk.StringVar()
        ttk.Entry(top, textvariable=self.file_path, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text="Browse", command=self.load_excel).pack(side=tk.LEFT)

        self.vis_frame = ttk.Frame(self.root)
        self.vis_frame.pack(fill=tk.BOTH, expand=True)

        self.chat_history = ScrolledText(self.root, wrap=tk.WORD, height=15, state='disabled')
        self.chat_history.pack(fill=tk.BOTH, expand=True)

        bottom = ttk.Frame(self.root, padding=10)
        bottom.pack(fill=tk.X)

        self.user_input = ttk.Entry(bottom)
        self.user_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.user_input.bind("<Return>", self.process_query)
        ttk.Button(bottom, text="Send", command=self.process_query).pack(side=tk.LEFT)

    def load_excel(self):
        filepath = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if filepath:
            try:
                self.df = pd.read_excel(filepath)
                self.df.columns = self.df.columns.str.strip().str.lower()
                self.file_path.set(filepath)
                msg = f"File loaded with {len(self.df)} entries.\nAvailable columns: {', '.join(self.df.columns)}"
                self.update_chat("System", msg)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {str(e)}")
                self.df = None

    def update_chat(self, sender, message):
        self.chat_history.config(state='normal')
        self.chat_history.insert(tk.END, f"{sender}: {message}\n\n")
        self.chat_history.config(state='disabled')
        self.chat_history.see(tk.END)

    def process_query(self, event=None):
        query = self.user_input.get().strip()
        if not query:
            return

        self.update_chat("You", query)
        self.user_input.delete(0, tk.END)

        if self.df is None:
            self.update_chat("Bot", "Please load an Excel file first.")
            return

        response = self.handle_query(query.lower())
        if response:
            self.update_chat("Bot", response)
        else:
            self.update_chat("Bot", "Sorry, I couldn't understand the question.")

    def handle_query(self, q):
        df = self.df

        synonyms = {
            "training in progress": ["training in progress", "ongoing training", "in training", "started training"],
            "completed seer training": ["completed seer", "finished training", "done with seer", "completed training"],
            "not started": ["not started", "training not started", "pending training"],
            "on bench": ["on bench", "not deployed", "idle", "sitting free"],
            "deployed in project": ["deployed", "in project", "currently deployed", "working"],
            "rolling off": ["rolling off", "exiting project", "getting free soon"],
            "batch distribution": ["batch distribution", "batch chart", "batch-wise chart", "chart for batch", "batch wise talents", "chart for batch wise talents"]
        }

        def match_phrase(q, key):
            return any(variant in q for variant in synonyms.get(key, []))

        if match_phrase(q, "training in progress"):
            result = df[df['training status'].str.lower() == "training in progress"]
            return self.display_list(result, "talent name", "Talents in training")

        if match_phrase(q, "completed seer training"):
            result = df[df['training status'].str.lower() == "completed seer training"]
            return self.display_list(result, "talent name", "Talents who completed SEER training")

        if match_phrase(q, "not started"):
            result = df[df['training status'].str.lower() == "not started"]
            return self.display_list(result, "talent name", "Talents who haven't started training")

        if match_phrase(q, "on bench"):
            result = df[df['deployment status'].str.lower() == "on bench"]
            return self.display_list(result, "talent name", "Talents currently on bench")

        if match_phrase(q, "deployed in project"):
            result = df[df['deployment status'].str.lower() == "deployed in project"]
            return self.display_list(result, "talent name", "Talents deployed in project")

        if match_phrase(q, "rolling off"):
            result = df[df['deployment status'].str.lower() == "rolling off"]
            return self.display_list(result, "talent name", "Talents rolling off")

        if "pie" in q and "training" in q:
            self.plot_chart(df['training status'], "pie", "Training Status Distribution")
            return "Showing pie chart for training status."

        if "bar" in q and "training" in q:
            self.plot_chart(df['training status'], "bar", "Training Status Bar Chart")
            return "Showing bar chart for training status."

        if "pie" in q and "deployment" in q:
            self.plot_chart(df['deployment status'], "pie", "Deployment Status Distribution")
            return "Showing pie chart for deployment status."

        if "bar" in q and "deployment" in q:
            self.plot_chart(df['deployment status'], "bar", "Deployment Status Bar Chart")
            return "Showing bar chart for deployment status."

        # if match_phrase(q, "batch distribution"):
        #     self.plot_chart(df['batch'], "bar", "Batch-wise Talent Distribution")
        #     return "Showing batch-wise talent distribution."

        return None

    def display_list(self, df_filtered, name_col, title):
        if df_filtered.empty:
            return f"No records found for {title.lower()}."
        names = "\n".join(df_filtered[name_col].tolist())
        return f"{title}:\n{names}"

    def plot_chart(self, series, chart_type="bar", title="Chart"):
        self.clear_visualization()

        fig, ax = plt.subplots(figsize=(6, 4))
        if chart_type == "bar":
            series.value_counts().plot(kind="bar", ax=ax)
        elif chart_type == "pie":
            series.value_counts().plot(kind="pie", ax=ax, autopct='%1.1f%%')

        ax.set_title(title)
        buf = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buf, format='png')
        buf.seek(0)
        img = Image.open(buf)
        img = ImageTk.PhotoImage(img)

        label = ttk.Label(self.vis_frame, image=img)
        label.image = img
        label.pack()
        plt.close(fig)

    def clear_visualization(self):
        for widget in self.vis_frame.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = TalentDashboardChatBot(root)
    root.mainloop()
