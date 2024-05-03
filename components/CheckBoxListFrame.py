import customtkinter as ctk
from tkinter import BooleanVar
from typing import List, Dict

class CheckBoxListFrame(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk, name: str, fields: List[str]):
        super().__init__(master)
        self.fields = fields
        self.checkbox_vars: Dict[str, BooleanVar] = {}
        self.label = ctk.CTkLabel(self, text=name)
        self.label.grid(row=0, column=0, sticky="w", padx=10)
        self.create_checkboxes()

    def create_checkboxes(self) -> None:
        for (i, name) in enumerate(self.fields):
            var = BooleanVar(self, value=False)
            checkbox = ctk.CTkCheckBox(self, text=name, variable=var)
            self.checkbox_vars[name] = var
            checkbox.grid(row=i+1, column=0, sticky="w", pady=(2, 10 if i == len(self.fields)-1 else 2), padx=10)

    def get_checkbox_values(self) -> Dict[str, bool]:
        ans = {}
        for name in self.checkbox_vars:
            ans[name] = self.checkbox_vars[name].get()
        return ans

    def set_checkbox_values(self, config: Dict[str, bool]):
        for name in config:
            self.checkbox_vars[name].set(config[name])