import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import pandas as pd
import os


# ============================================================
#                    CONFIGURATION
# ============================================================

CSV_FILE = "D:/My Projects/Car Rental Recommendation System/Car details v3.csv"
DB_FILE = "car_rental.db"


# ============================================================
#                  GRADIENT BACKGROUND
# ============================================================

class GradientFrame(tk.Canvas):

    def __init__(self, parent, color1="#101828", color2="#344054", **kwargs):
        super().__init__(parent, highlightthickness=0, **kwargs)

        self.color1 = color1
        self.color2 = color2

        self.bind("<Configure>", self.draw_gradient)

    def draw_gradient(self, event=None):

        self.delete("gradient")

        width = self.winfo_width()
        height = self.winfo_height()

        if width <= 0 or height <= 0:
            return

        r1, g1, b1 = self.winfo_rgb(self.color1)
        r2, g2, b2 = self.winfo_rgb(self.color2)

        r1 //= 256
        g1 //= 256
        b1 //= 256

        r2 //= 256
        g2 //= 256
        b2 //= 256

        for i in range(height):

            ratio = i / height

            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)

            color = f"#{r:02x}{g:02x}{b:02x}"

            self.create_line(
                0,
                i,
                width,
                i,
                fill=color,
                tags="gradient"
            )

        self.tag_lower("gradient")


# ============================================================
#                  DATABASE MANAGEMENT
# ============================================================

class Database:

    def __init__(self):

        self.conn = sqlite3.connect(DB_FILE)

        self.cursor = self.conn.cursor()

        self.create_table()

        self.import_kaggle_data()

    # --------------------------------------------------------

    def create_table(self):

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS cars (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT,

                year INTEGER,

                selling_price REAL,

                km_driven INTEGER,

                fuel TEXT,

                seller_type TEXT,

                transmission TEXT,

                owner TEXT,

                status TEXT DEFAULT 'Available'

            )
        """)

        self.conn.commit()

    # --------------------------------------------------------

    def import_kaggle_data(self):

        # Don't import again if database already contains cars
        self.cursor.execute("SELECT COUNT(*) FROM cars")

        count = self.cursor.fetchone()[0]

        if count > 0:
            return

        if not os.path.exists(CSV_FILE):

            messagebox.showerror(
                "Dataset Missing",
                f"Could not find '{CSV_FILE}'.\n\n"
                "Please download the Kaggle dataset and place "
                "the CSV file beside this Python program."
            )

            return

        try:

            df = pd.read_csv(CSV_FILE)

            # Convert column names to lowercase
            df.columns = [
                str(column).strip().lower().replace(" ", "_")
                for column in df.columns
            ]

            required_columns = [
                "name",
                "year",
                "selling_price",
                "km_driven",
                "fuel",
                "seller_type",
                "transmission",
                "owner"
            ]

            missing = [
                column
                for column in required_columns
                if column not in df.columns
            ]

            if missing:

                messagebox.showerror(
                    "Invalid Dataset",
                    "The CSV file is missing these columns:\n\n"
                    + "\n".join(missing)
                )

                return

            # Keep only useful columns
            df = df[required_columns].copy()

            # Remove rows with missing names
            df = df.dropna(subset=["name"])

            # Convert numeric fields
            df["year"] = pd.to_numeric(
                df["year"],
                errors="coerce"
            )

            df["selling_price"] = pd.to_numeric(
                df["selling_price"],
                errors="coerce"
            )

            df["km_driven"] = pd.to_numeric(
                df["km_driven"],
                errors="coerce"
            )

            df = df.dropna(
                subset=[
                    "year",
                    "selling_price",
                    "km_driven"
                ]
            )

            # Insert into SQLite
            for _, row in df.iterrows():

                self.cursor.execute("""
                    INSERT INTO cars
                    (
                        name,
                        year,
                        selling_price,
                        km_driven,
                        fuel,
                        seller_type,
                        transmission,
                        owner,
                        status
                    )

                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (

                    str(row["name"]),
                    int(row["year"]),
                    float(row["selling_price"]),
                    int(row["km_driven"]),
                    str(row["fuel"]),
                    str(row["seller_type"]),
                    str(row["transmission"]),
                    str(row["owner"]),
                    "Available"

                ))

            self.conn.commit()

        except Exception as e:

            messagebox.showerror(
                "Database Error",
                f"Could not import Kaggle dataset.\n\n{e}"
            )

    # --------------------------------------------------------

    def get_all_cars(self):

        self.cursor.execute("""
            SELECT *
            FROM cars
            ORDER BY id
        """)

        return self.cursor.fetchall()

    # --------------------------------------------------------

    def search_cars(self, text):

        text = f"%{text}%"

        self.cursor.execute("""
            SELECT *
            FROM cars
            WHERE
                name LIKE ?
                OR fuel LIKE ?
                OR transmission LIKE ?
                OR owner LIKE ?
            ORDER BY id
        """, (
            text,
            text,
            text,
            text
        ))

        return self.cursor.fetchall()

    # --------------------------------------------------------

    def get_available(self):

        self.cursor.execute("""
            SELECT *
            FROM cars
            WHERE status = 'Available'
            ORDER BY id
        """)

        return self.cursor.fetchall()

    # --------------------------------------------------------

    def rent_car(self, car_id):

        self.cursor.execute("""
            UPDATE cars
            SET status = 'Rented'
            WHERE id = ?
            AND status = 'Available'
        """, (car_id,))

        self.conn.commit()

        return self.cursor.rowcount > 0

    # --------------------------------------------------------

    def return_car(self, car_id):

        self.cursor.execute("""
            UPDATE cars
            SET status = 'Available'
            WHERE id = ?
            AND status = 'Rented'
        """, (car_id,))

        self.conn.commit()

        return self.cursor.rowcount > 0

    # --------------------------------------------------------

    def statistics(self):

        self.cursor.execute(
            "SELECT COUNT(*) FROM cars"
        )

        total = self.cursor.fetchone()[0]

        self.cursor.execute(
            "SELECT COUNT(*) FROM cars WHERE status='Available'"
        )

        available = self.cursor.fetchone()[0]

        self.cursor.execute(
            "SELECT COUNT(*) FROM cars WHERE status='Rented'"
        )

        rented = self.cursor.fetchone()[0]

        return total, available, rented


# ============================================================
#                     MAIN APPLICATION
# ============================================================

class CarRentalApp:

    def __init__(self, root):

        self.root = root

        self.root.title("ZaBir • Car Rental Management")

        self.root.geometry("1350x780")

        self.root.minsize(1100, 650)

        self.db = Database()

        self.selected_car = None

        self.build_style()

        self.build_interface()

        self.load_cars()

        self.update_statistics()

    # ========================================================
    #                    STYLE
    # ========================================================

    def build_style(self):

        style = ttk.Style()

        style.theme_use("clam")

        style.configure(
            "Treeview",
            background="#1D2939",
            foreground="white",
            rowheight=42,
            fieldbackground="#1D2939",
            font=("Segoe UI", 11)
        )

        style.configure(
            "Treeview.Heading",
            background="#475467",
            foreground="white",
            font=("Segoe UI", 11, "bold"),
            padding=10
        )

        style.map(
            "Treeview",
            background=[
                ("selected", "#12B76A")
            ]
        )

    # ========================================================
    #                  BUILD INTERFACE
    # ========================================================

    def build_interface(self):

        self.background = GradientFrame(
            self.root,
            "#0B1220",
            "#344054"
        )

        self.background.pack(
            fill="both",
            expand=True
        )

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        header = tk.Frame(
            self.background,
            bg="#101828"
        )

        header.place(
            x=25,
            y=20,
            relwidth=0.96,
            height=80
        )

        title = tk.Label(
            header,
            text="🚘  ZaBir HaSan",
            bg="#101828",
            fg="#FFFFFF",
            font=("Segoe UI", 28, "bold")
        )

        title.pack(
            side="left",
            padx=25,
            pady=18
        )

        subtitle = tk.Label(
            header,
            text="CAR RENTAL MANAGEMENT SYSTEM",
            bg="#101828",
            fg="#98A2B3",
            font=("Segoe UI", 11, "bold")
        )

        subtitle.pack(
            side="left",
            padx=10
        )

        # ----------------------------------------------------
        # Statistics cards
        # ----------------------------------------------------

        self.total_label = self.create_card(
            "TOTAL CARS",
            "0",
            "#1570EF",
            25
        )

        self.available_label = self.create_card(
            "AVAILABLE",
            "0",
            "#12B76A",
            240
        )

        self.rented_label = self.create_card(
            "RENTED",
            "0",
            "#F79009",
            455
        )

        # ----------------------------------------------------
        # Search
        # ----------------------------------------------------

        search_frame = tk.Frame(
            self.background,
            bg="#101828"
        )

        search_frame.place(
            x=700,
            y=120,
            width=610,
            height=65
        )

        tk.Label(
            search_frame,
            text="🔎",
            bg="#101828",
            fg="white",
            font=("Segoe UI", 18)
        ).pack(
            side="left",
            padx=(15, 5)
        )

        self.search_entry = tk.Entry(
            search_frame,
            bg="#1D2939",
            fg="white",
            insertbackground="white",
            relief="flat",
            font=("Segoe UI", 13)
        )

        self.search_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=10,
            pady=12
        )

        self.search_entry.bind(
            "<KeyRelease>",
            self.search
        )

        # ----------------------------------------------------
        # Buttons
        # ----------------------------------------------------

        button_frame = tk.Frame(
            self.background,
            bg="#101828"
        )

        button_frame.place(
            x=25,
            y=205,
            relwidth=0.96,
            height=65
        )

        self.make_button(
            button_frame,
            "🚗  RENT CAR",
            self.rent_car,
            "#12B76A"
        ).pack(
            side="left",
            padx=10,
            pady=10
        )

        self.make_button(
            button_frame,
            "↩  RETURN CAR",
            self.return_car,
            "#F79009"
        ).pack(
            side="left",
            padx=10,
            pady=10
        )

        self.make_button(
            button_frame,
            "🔄  REFRESH",
            self.refresh,
            "#1570EF"
        ).pack(
            side="left",
            padx=10,
            pady=10
        )

        self.make_button(
            button_frame,
            "❌  EXIT",
            self.root.destroy,
            "#D92D20"
        ).pack(
            side="right",
            padx=10,
            pady=10
        )

        # ----------------------------------------------------
        # Table
        # ----------------------------------------------------

        table_frame = tk.Frame(
            self.background,
            bg="#101828"
        )

        table_frame.place(
            x=25,
            y=285,
            relwidth=0.96,
            relheight=0.64
        )

        columns = (
            "id",
            "name",
            "year",
            "price",
            "km",
            "fuel",
            "transmission",
            "owner",
            "status"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings"
        )

        headings = {
            "id": "ID",
            "name": "CAR",
            "year": "YEAR",
            "price": "PRICE",
            "km": "KM DRIVEN",
            "fuel": "FUEL",
            "transmission": "TRANSMISSION",
            "owner": "OWNER",
            "status": "STATUS"
        }

        widths = {
            "id": 60,
            "name": 230,
            "year": 80,
            "price": 120,
            "km": 120,
            "fuel": 100,
            "transmission": 120,
            "owner": 150,
            "status": 110
        }

        for column in columns:

            self.tree.heading(
                column,
                text=headings[column]
            )

            self.tree.column(
                column,
                width=widths[column],
                anchor="center"
            )

        self.tree.column(
            "name",
            anchor="w"
        )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview
        )

        self.tree.configure(
            yscrollcommand=scrollbar.set
        )

        self.tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.select_car
        )

        # Status colors
        self.tree.tag_configure(
            "available",
            foreground="#32D583"
        )

        self.tree.tag_configure(
            "rented",
            foreground="#FDB022"
        )

    # ========================================================
    #                    CARD
    # ========================================================

    def create_card(
        self,
        title,
        value,
        color,
        x
    ):

        frame = tk.Frame(
            self.background,
            bg="#101828",
            highlightbackground=color,
            highlightthickness=2
        )

        frame.place(
            x=x,
            y=120,
            width=190,
            height=65
        )

        label = tk.Label(
            frame,
            text=f"{title}   {value}",
            bg="#101828",
            fg="white",
            font=("Segoe UI", 12, "bold")
        )

        label.pack(
            expand=True
        )

        return label

    # ========================================================
    #                  BUTTON
    # ========================================================

    def make_button(
        self,
        parent,
        text,
        command,
        color
    ):

        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg="white",
            activebackground=color,
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=18,
            pady=8,
            font=("Segoe UI", 11, "bold"),
            cursor="hand2"
        )

    # ========================================================
    #                  LOAD CARS
    # ========================================================

    def load_cars(
        self,
        data=None
    ):

        for item in self.tree.get_children():

            self.tree.delete(item)

        if data is None:

            data = self.db.get_all_cars()

        for row in data:

            car_id = row[0]
            name = row[1]
            year = row[2]
            price = row[3]
            km = row[4]
            fuel = row[5]
            transmission = row[7]
            owner = row[8]
            status = row[9]

            # Display price in a readable format
            price_text = f"৳ {price:,.0f}"

            tag = (
                "available"
                if status == "Available"
                else "rented"
            )

            self.tree.insert(
                "",
                "end",
                values=(
                    car_id,
                    name,
                    year,
                    price_text,
                    f"{km:,}",
                    fuel,
                    transmission,
                    owner,
                    status
                ),
                tags=(tag,)
            )

    # ========================================================
    #                    SEARCH
    # ========================================================

    def search(self, event=None):

        text = self.search_entry.get().strip()

        if text == "":

            self.load_cars()

        else:

            data = self.db.search_cars(text)

            self.load_cars(data)

    # ========================================================
    #                  SELECT CAR
    # ========================================================

    def select_car(self, event=None):

        selection = self.tree.selection()

        if not selection:

            self.selected_car = None

            return

        values = self.tree.item(
            selection[0],
            "values"
        )

        self.selected_car = int(values[0])

    # ========================================================
    #                    RENT CAR
    # ========================================================

    def rent_car(self):

        if self.selected_car is None:

            messagebox.showwarning(
                "No Car Selected",
                "Please select a car first."
            )

            return

        car_id = self.selected_car

        # Find car
        self.db.cursor.execute(
            "SELECT * FROM cars WHERE id=?",
            (car_id,)
        )

        car = self.db.cursor.fetchone()

        if not car:

            messagebox.showerror(
                "Error",
                "Car not found."
            )

            return

        if car[9] == "Rented":

            messagebox.showwarning(
                "Unavailable",
                "This car is already rented."
            )

            return

        # Rental dialog
        dialog = tk.Toplevel(self.root)

        dialog.title("Rent Car")

        dialog.geometry("430x360")

        dialog.configure(
            bg="#101828"
        )

        dialog.resizable(
            False,
            False
        )

        tk.Label(
            dialog,
            text="🚗 RENT CAR",
            bg="#101828",
            fg="white",
            font=("Segoe UI", 22, "bold")
        ).pack(
            pady=20
        )

        tk.Label(
            dialog,
            text=car[1],
            bg="#101828",
            fg="#32D583",
            font=("Segoe UI", 15, "bold")
        ).pack()

        tk.Label(
            dialog,
            text="Number of rental days",
            bg="#101828",
            fg="#D0D5DD",
            font=("Segoe UI", 11)
        ).pack(
            pady=(25, 5)
        )

        days_entry = tk.Entry(
            dialog,
            bg="#1D2939",
            fg="white",
            insertbackground="white",
            relief="flat",
            justify="center",
            font=("Segoe UI", 15)
        )

        days_entry.pack(
            ipady=8
        )

        def confirm():

            try:

                days = int(
                    days_entry.get()
                )

                if days <= 0:

                    raise ValueError

            except ValueError:

                messagebox.showerror(
                    "Invalid Input",
                    "Please enter a valid number of days."
                )

                return

            # We use 5% of selling price as a demo
            # daily rental rate.
            daily_rate = car[3] * 0.05

            total = daily_rate * days

            success = self.db.rent_car(
                car_id
            )

            if success:

                messagebox.showinfo(
                    "Rental Confirmed",
                    f"Car: {car[1]}\n\n"
                    f"Rental days: {days}\n"
                    f"Daily rate: ৳ {daily_rate:,.0f}\n"
                    f"Total: ৳ {total:,.0f}"
                )

                dialog.destroy()

                self.refresh()

            else:

                messagebox.showerror(
                    "Error",
                    "Unable to rent this car."
                )

        tk.Button(
            dialog,
            text="CONFIRM RENTAL",
            command=confirm,
            bg="#12B76A",
            fg="white",
            activebackground="#12B76A",
            relief="flat",
            font=("Segoe UI", 12, "bold"),
            padx=20,
            pady=10,
            cursor="hand2"
        ).pack(
            pady=30
        )

    # ========================================================
    #                  RETURN CAR
    # ========================================================

    def return_car(self):

        if self.selected_car is None:

            messagebox.showwarning(
                "No Car Selected",
                "Please select a car first."
            )

            return

        car_id = self.selected_car

        self.db.cursor.execute(
            "SELECT name, status FROM cars WHERE id=?",
            (car_id,)
        )

        car = self.db.cursor.fetchone()

        if not car:

            messagebox.showerror(
                "Error",
                "Car not found."
            )

            return

        if car[1] == "Available":

            messagebox.showinfo(
                "Already Available",
                "This car is already available."
            )

            return

        answer = messagebox.askyesno(
            "Return Car",
            f"Return '{car[0]}'?"
        )

        if answer:

            success = self.db.return_car(
                car_id
            )

            if success:

                messagebox.showinfo(
                    "Success",
                    "Car returned successfully."
                )

                self.refresh()

    # ========================================================
    #                  REFRESH
    # ========================================================

    def refresh(self):

        self.search_entry.delete(
            0,
            tk.END
        )

        self.selected_car = None

        self.load_cars()

        self.update_statistics()

    # ========================================================
    #                STATISTICS
    # ========================================================

    def update_statistics(self):

        total, available, rented = (
            self.db.statistics()
        )

        self.total_label.config(
            text=f"TOTAL CARS   {total}"
        )

        self.available_label.config(
            text=f"AVAILABLE   {available}"
        )

        self.rented_label.config(
            text=f"RENTED   {rented}"
        )


# ============================================================
#                       RUN APP
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = CarRentalApp(root)

    root.mainloop()