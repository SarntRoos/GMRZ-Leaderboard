import tkinter as tk
from tkinter import ttk, messagebox
import json
import logging
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from threading import Thread
from PIL import Image, ImageTk

# Set up logging
logging.basicConfig(filename="leaderboard.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class Player:
    def __init__(self, name, team=None, wins=0, losses=0, kills=0, deaths=0):
        self.name = name
        self.team = team
        self.wins = wins
        self.losses = losses
        self.kills = kills
        self.deaths = deaths

    @property
    def score(self):
        return self.wins * 10 - self.losses * 2.5

    @property
    def kd_ratio(self):
        return self.kills / self.deaths if self.deaths > 0 else self.kills

class Team:
    def __init__(self, name):
        self.name = name
        self.players = []

class InputDialog(tk.Toplevel):
    def __init__(self, parent, title, fields):
        super().__init__(parent)
        self.title(title)
        self.result = None
        self.fields = fields
        self.entries = {}

        for i, (field, value) in enumerate(fields.items()):
            tk.Label(self, text=field).grid(row=i, column=0, padx=5, pady=5)
            entry = tk.Entry(self)
            entry.insert(0, str(value))
            entry.grid(row=i, column=1, padx=5, pady=5)
            self.entries[field] = entry

        tk.Button(self, text="OK", command=self.on_ok).grid(row=len(fields), column=0, padx=5, pady=5)
        tk.Button(self, text="Cancel", command=self.on_cancel).grid(row=len(fields), column=1, padx=5, pady=5)

        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.transient(parent)
        self.wait_visibility()
        self.grab_set()
        self.wait_window(self)

    def on_ok(self):
        self.result = {field: entry.get() for field, entry in self.entries.items()}
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()

class LeaderboardApp:
    def __init__(self, master):
        self.master = master
        self.master.title("GMRZ Leaderboard")
        self.master.geometry("800x600")

        # Load and set the custom logo
        self.logo_path = "C:/Users/sarnt/Desktop/GMRZ App/GMRZ.png"  # This should ideally be configurable or relative
        try:
            self.logo_image = Image.open(self.logo_path)
            self.logo_photo = ImageTk.PhotoImage(self.logo_image)
            self.master.iconphoto(False, self.logo_photo)
        except Exception as e:
            logging.error(f"Error loading logo image: {e}")
            messagebox.showerror("Error", "Could not load the logo image.")

        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Configure the application's style
        self.configure_styles()

        self.players = {}
        self.teams = []
        self.load_data()

        self.create_widgets()
        self.update_leaderboard()

    def configure_styles(self):
        self.style.configure("TFrame", background="#202020")
        self.style.configure("TNotebook", background="#202020", tabmargins=[2, 5, 2, 0])
        self.style.configure("TNotebook.Tab", background="#1c1c1c", foreground="white", padding=[10, 2])
        self.style.map("TNotebook.Tab", background=[("selected", "#ff0000")])
        self.style.configure("Treeview", background="#ffffff", foreground="#202020", rowheight=25, fieldbackground="#ffffff")
        self.style.map("Treeview", background=[("selected", "#ff0000")])
        self.style.configure("Treeview.Heading", background="#1c1c1c", foreground="white", relief="flat")
        self.style.map("Treeview.Heading", background=[("active", "#DE070A")])
        self.style.configure("TButton", background="#DE070A", foreground="white", padding=10)
        self.style.map("TButton", background=[("active", "#DE070A")])

    def create_widgets(self):
        self.master.configure(bg="#202020")
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        players_frame = ttk.Frame(self.notebook)
        self.notebook.add(players_frame, text="Leaderboard")

        teams_frame = ttk.Frame(self.notebook)
        self.notebook.add(teams_frame, text="Teams")

        onevone_frame = ttk.Frame(self.notebook)
        self.notebook.add(onevone_frame, text="1v1")

        self.style.configure('TNotebook.Tab', padding=[10, 2], anchor='w')

        columns = ("Rank", "Name", "Team", "Score", "Wins", "Losses", "Kills", "Deaths", "K/D")
        self.player_tree = ttk.Treeview(players_frame, columns=columns, show="headings")

        for col in columns:
            self.player_tree.heading(col, text=col, anchor="w")
            self.player_tree.column(col, width=self.get_column_width(col), anchor="w")

        self.player_tree.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        team_columns = ("Name", "Players")
        self.team_tree = ttk.Treeview(teams_frame, columns=team_columns, show="headings")
        for col in team_columns:
            self.team_tree.heading(col, text=col)
            self.team_tree.column(col, width=self.get_column_width(col, is_team=True))
        self.team_tree.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # Creating 1v1 Tab Widgets
        self.create_1v1_widgets(onevone_frame)

        # Button Frame
        self.create_button_frame()

    def create_1v1_widgets(self, parent_frame):
        label_width = 24
        entry_width = 24

        container_frame = ttk.Frame(parent_frame)
        container_frame.grid(row=0, column=0, padx=20, pady=30, sticky="nsew")
        container_frame.grid_columnconfigure(0, weight=1)
        container_frame.grid_columnconfigure(1, weight=1)

        player1_frame = ttk.Frame(container_frame)
        player1_frame.grid(row=0, column=0, padx=20, pady=10, sticky="n")

        ttk.Label(player1_frame, text="Select Player 1:", width=25, anchor="e").grid(row=0, column=0, padx=5, pady=5)
        self.player1_var = tk.StringVar()
        self.player1_dropdown = ttk.Combobox(player1_frame, textvariable=self.player1_var, width=entry_width)
        self.player1_dropdown['values'] = list(self.players.keys())
        self.player1_dropdown.grid(row=0, column=1, padx=5, pady=8)

        ttk.Label(player1_frame, text="Player 1 Kills:", width=25, anchor="e").grid(row=1, column=0, padx=5, pady=8)
        self.player1_kills = tk.Entry(player1_frame, width=entry_width)
        self.player1_kills.grid(row=1, column=1, padx=5, pady=8)

        ttk.Label(player1_frame, text="Player 1 Deaths:", width=25, anchor="e").grid(row=2, column=0, padx=5, pady=8)
        self.player1_deaths = tk.Entry(player1_frame, width=entry_width)
        self.player1_deaths.grid(row=2, column=1, padx=5, pady=8)

        self.player1_win_var = tk.BooleanVar()
        ttk.Checkbutton(player1_frame, text="Win", variable=self.player1_win_var).grid(row=3, column=0, padx=5, pady=8, sticky="w")

        self.player1_loss_var = tk.BooleanVar()
        ttk.Checkbutton(player1_frame, text="Loss", variable=self.player1_loss_var).grid(row=3, column=1, padx=5, pady=8, sticky="w")

        player2_frame = ttk.Frame(container_frame)
        player2_frame.grid(row=0, column=1, padx=20, pady=10, sticky="n")

        ttk.Label(player2_frame, text="Select Player 2:", width=25, anchor="e").grid(row=0, column=0, padx=5, pady=8)
        self.player2_var = tk.StringVar()
        self.player2_dropdown = ttk.Combobox(player2_frame, textvariable=self.player2_var, width=entry_width)
        self.player2_dropdown['values'] = list(self.players.keys())
        self.player2_dropdown.grid(row=0, column=1, padx=5, pady=8)

        ttk.Label(player2_frame, text="Player 2 Kills:", width=25, anchor="e").grid(row=1, column=0, padx=5, pady=8)
        self.player2_kills = tk.Entry(player2_frame, width=entry_width)
        self.player2_kills.grid(row=1, column=1, padx=5, pady=8)

        ttk.Label(player2_frame, text="Player 2 Deaths:", width=25, anchor="e").grid(row=2, column=0, padx=5, pady=8)
        self.player2_deaths = tk.Entry(player2_frame, width=entry_width)
        self.player2_deaths.grid(row=2, column=1, padx=5, pady=8)

        self.player2_win_var = tk.BooleanVar()
        ttk.Checkbutton(player2_frame, text="Win", variable=self.player2_win_var).grid(row=3, column=0, padx=5, pady=8, sticky="w")

        self.player2_loss_var = tk.BooleanVar()
        ttk.Checkbutton(player2_frame, text="Loss", variable=self.player2_loss_var).grid(row=3, column=1, padx=5, pady=8, sticky="w")

        submit_button = ttk.Button(parent_frame, text="Submit 1v1", command=self.add_1v1)
        submit_button.grid(row=1, column=0, columnspan=2, pady=20)

    def create_button_frame(self):
        button_frame = ttk.Frame(self.master)
        button_frame.pack(pady=10, padx=10, fill=tk.X)

        for i in range(6):
            button_frame.columnconfigure(i, weight=1)

        ttk.Button(button_frame, text="Add Player", command=self.add_player).grid(row=0, column=0, padx=5, sticky='ew')
        ttk.Button(button_frame, text="Add Team", command=self.add_team).grid(row=0, column=1, padx=5, sticky='ew')
        ttk.Button(button_frame, text="Add Player to Team", command=self.add_player_to_team).grid(row=0, column=2, padx=5, sticky='ew')
        ttk.Button(button_frame, text="Update Player Stats", command=self.update_player_stats).grid(row=0, column=3, padx=5, sticky='ew')
        ttk.Button(button_frame, text="Print Leaderboard", command=self.print_leaderboard).grid(row=0, column=4, padx=5, sticky='ew')
        ttk.Button(button_frame, text="Clear Leaderboard", command=self.clear_leaderboard).grid(row=0, column=5, padx=5, sticky='ew')

    def clear_leaderboard(self):
        if messagebox.askyesno("Clear Leaderboard", "Are you sure you want to clear the leaderboard? This action cannot be undone."):
            self.players.clear()
            self.teams.clear()
            self.save_data()
            self.update_leaderboard()
            logging.info("Leaderboard cleared.")
            messagebox.showinfo("Clear Leaderboard", "The leaderboard has been cleared.")

    def get_column_width(self, column, is_team=False):
        if is_team:
            return 200 if column == "Players" else 100
        widths = {
            "Rank": 70,
            "Name": 70,
            "Team": 70,
            "Score": 70,
            "Wins": 70,
            "Losses": 70,
            "Kills": 70,
            "Deaths": 70,
            "K/D": 70
        }
        return widths.get(column, 100)

    def load_data(self):
        try:
            with open("leaderboard_data.json", "r") as f:
                data = json.load(f)
                self.players = {p['name']: Player(**p) for p in data["players"]}
                self.teams = [Team(t["name"]) for t in data["teams"]]
                for team in self.teams:
                    team.players = [self.players[p] for p in self.players if self.players[p].team == team.name]
            logging.info("Data loaded successfully.")
        except FileNotFoundError:
            self.players = {}
            self.teams = []
            logging.warning("No data file found. Starting with empty leaderboard.")
        except Exception as e:
            logging.error(f"Error loading data: {e}")
            messagebox.showerror("Error", f"Error loading data: {e}")

    def save_data(self):
        try:
            data = {
                "players": [vars(p) for p in self.players.values()],
                "teams": [{"name": t.name, "players": [p.name for p in t.players]} for t in self.teams]
            }
            with open("leaderboard_data.json", "w") as f:
                json.dump(data, f)
            logging.info("Data saved successfully.")
        except Exception as e:
            logging.error(f"Failed to save data: {e}")
            messagebox.showerror("Error", "Failed to save data.")

    def update_leaderboard(self):
        self.player_tree.delete(*self.player_tree.get_children())
        sorted_players = sorted(self.players.values(), key=lambda x: x.score, reverse=True)
        for i, player in enumerate(sorted_players, start=1):
            self.player_tree.insert("", "end", values=(i, player.name, player.team, player.score, player.wins, player.losses, player.kills, player.deaths, f"{player.kd_ratio:.2f}"))

        self.team_tree.delete(*self.team_tree.get_children())
        for team in self.teams:
            self.team_tree.insert("", "end", values=(team.name, ", ".join([p.name for p in team.players])))

    def add_player(self):
        fields = {"Name": "", "Team": "", "Wins": 0, "Losses": 0, "Kills": 0, "Deaths": 0}
        dialog = InputDialog(self.master, "Add Player", fields)
        if dialog.result:
            name = dialog.result["Name"]
            if any(p.name == name for p in self.players.values()):
                messagebox.showerror("Error", "Player with this name already exists.")
                return
            try:
                wins = int(dialog.result["Wins"])
                losses = int(dialog.result["Losses"])
                kills = int(dialog.result["Kills"])
                deaths = int(dialog.result["Deaths"])
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers for Wins, Losses, Kills, and Deaths.")
                return
            team = dialog.result["Team"] if dialog.result["Team"] else None
            self.players[name] = Player(name, team, wins, losses, kills, deaths)
            self.save_data()
            self.update_leaderboard()

    def add_team(self):
        fields = {"Team Name": ""}
        dialog = InputDialog(self.master, "Add Team", fields)
        if dialog.result:
            name = dialog.result["Team Name"]
            if any(t.name == name for t in self.teams):
                messagebox.showerror("Error", "Team with this name already exists.")
                return
            self.teams.append(Team(name))
            self.save_data()
            self.update_leaderboard()

    def add_player_to_team(self):
        fields = {"Player Name": "", "Team Name": ""}
        dialog = InputDialog(self.master, "Add Player to Team", fields)
        if dialog.result:
            player_name = dialog.result["Player Name"]
            team_name = dialog.result["Team Name"]
            player = self.players.get(player_name)
            team = next((t for t in self.teams if t.name == team_name), None)
            if player and team:
                player.team = team.name
                team.players.append(player)
                self.save_data()
                self.update_leaderboard()
            else:
                messagebox.showerror("Error", "Player or team not found")

    def update_player_stats(self):
        fields = {"Player Name": "", "Wins": 0, "Losses": 0, "Kills": 0, "Deaths": 0}
        dialog = InputDialog(self.master, "Update Player Stats", fields)
        if dialog.result:
            player_name = dialog.result["Player Name"]
            player = self.players.get(player_name)
            if player:
                try:
                    player.wins = int(dialog.result["Wins"])
                    player.losses = int(dialog.result["Losses"])
                    player.kills = int(dialog.result["Kills"])
                    player.deaths = int(dialog.result["Deaths"])
                except ValueError:
                    messagebox.showerror("Error", "Please enter valid numbers for Wins, Losses, Kills, and Deaths.")
                    return
                self.save_data()
                self.update_leaderboard()
            else:
                messagebox.showerror("Error", "Player not found")

    def add_1v1(self):
        player1_name = self.player1_var.get()
        player2_name = self.player2_var.get()
        if not player1_name or not player2_name:
            messagebox.showerror("Error", "Both players must be selected.")
            return

        player1 = self.players.get(player1_name)
        player2 = self.players.get(player2_name)

        if not player1 or not player2:
            messagebox.showerror("Error", "One or both players not found.")
            return

        try:
            player1_kills = int(self.player1_kills.get())
            player1_deaths = int(self.player1_deaths.get())
            player2_kills = int(self.player2_kills.get())
            player2_deaths = int(self.player2_deaths.get())
        except ValueError:
            messagebox.showerror("Error", "Kills and deaths must be valid numbers.")
            return

        player1.kills += player1_kills
        player1.deaths += player1_deaths
        player2.kills += player2_kills
        player2.deaths += player2_deaths

        if self.player1_win_var.get():
            player1.wins += 1
            player2.losses += 1
        elif self.player2_win_var.get():
            player2.wins += 1
            player1.losses += 1

        self.save_data()
        self.update_leaderboard()

    def print_leaderboard(self):
        Thread(target=self._generate_leaderboard_pdf).start()

    def _generate_leaderboard_pdf(self):
        pdf_file = "leaderboard.pdf"
        doc = SimpleDocTemplate(pdf_file, pagesize=letter)
        elements = []

        player_data = [["Rank", "Name", "Team", "Score", "Wins", "Losses", "Kills", "Deaths", "K/D"]]
        sorted_players = sorted(self.players.values(), key=lambda x: x.score, reverse=True)
        for i, player in enumerate(sorted_players, start=1):
            player_data.append([i, player.name, player.team or "", f"{player.score:.1f}", player.wins, player.losses, player.kills, player.deaths, f"{player.kd_ratio:.2f}"])

        table = Table(player_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.black),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.red),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 18),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 18),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        elements.append(table)
        doc.build(elements)
        self.master.after(0, lambda: messagebox.showinfo("Print Leaderboard", f"Leaderboard has been saved as {pdf_file}"))
        logging.info("Leaderboard PDF generated and saved.")

if __name__ == "__main__":
    root = tk.Tk()
    app = LeaderboardApp(root)
    root.mainloop()
