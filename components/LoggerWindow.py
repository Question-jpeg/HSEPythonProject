import customtkinter as ctk
from tkinter import END

from multiprocessing import Queue

class Logger:
    def __init__(self, queue: Queue) -> None:
        self.queue = queue

    def println(self, text):
        self.queue.put(str(text))

class LoggerWindow(ctk.CTkToplevel):
    def __init__(self, master: ctk.CTk, queue: Queue):
        super().__init__(master)
        self.queue = queue

        self.geometry("800x800")

        self.log_textbox = ctk.CTkTextbox(self)              
        self.log_textbox.configure(state='disabled')

        self.log_textbox.grid(row=0, column=0, sticky='nsew')          
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.update_log()

    def update_log(self):
        while not self.queue.empty():
            text = self.queue.get_nowait()
            self.println(text)
        self.after(300, self.update_log)

    def println(self, text: str):
        self.log_textbox.configure(state='normal') 
        self.log_textbox.insert(END, text + "\n")   
        self.log_textbox.configure(state='disabled')
        
        current_lines = int(self.log_textbox.index('end-1c').split('.')[0])
        diff = current_lines*(1 - self.log_textbox.yview()[1])
        if diff < 5: 
            self.log_textbox.see(END)