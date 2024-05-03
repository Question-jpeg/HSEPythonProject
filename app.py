import json
import customtkinter as ctk
from typing import Dict, Tuple
from tkinter import StringVar

from datetime import date
import configparser

from components.CTkRangeSlider import CTkRangeSlider
from components.CheckBoxListFrame import CheckBoxListFrame
from components.LoggerWindow import LoggerWindow, Logger

from main import Service
from multiprocessing import Process, Queue

class App(ctk.CTk):
    def __init__(self, form_config, config_path: str):
        super().__init__()
        self.form_config = form_config
        self.config_path = config_path
        self.sliders: Dict[str, CTkRangeSlider] = {}
        self.checkbox_frames: Dict[str, CheckBoxListFrame] = {}

        self.load_settings()
        self.init_frames()

    def init_frames(self) -> None: 
        self.create_sliders()
        cur_row = self.create_list_frames()
        self.save_button = ctk.CTkButton(self, text='Начать серию запросов', command=self.save_button_callback)
        self.save_button.grid(row=cur_row, column=0, columnspan=999, sticky='ew', padx=(0, 5))

    def create_sliders(self):
        for (i, slider) in enumerate(self.form_config["sliders"]):
            name = slider["title"]
            minn = slider["min"]
            maxx = slider["max"]
            get_label = slider["get_label"]
            
            fromm = minn
            to = maxx

            if self.settings:
                setting = self.settings["sliders"][name]
                fromm = setting["min"]
                to = setting["max"]

            label_string = get_label([fromm, to])            

            label_var = StringVar(self, value=label_string)
            label_component = ctk.CTkLabel(self, textvariable=label_var)

            slider_component = CTkRangeSlider(
                self, from_=minn, to=maxx, 
                number_of_steps=maxx - minn, 
                command=lambda x, label_var=label_var, get_label=get_label: label_var.set(get_label(x))
            )
            self.sliders[name] = slider_component
            
            slider_component.set((fromm, to))

            slider_component.grid(row=i*2, column=0, columnspan=999, sticky='ew', padx=5, pady=(30 if i == 0 else 0, 0))
            label_component.grid(row=i*2+1, column=0, columnspan=999, sticky='ew', pady=(0, 10))

    def create_list_frames(self) -> int:        
        rowPlacementInfo = [4, 5, 2, 3]
        def getRowCol(c: int) -> Tuple[int, int]:            
            summ = 0
            for i in range(len(rowPlacementInfo)):
                offset = summ
                summ += rowPlacementInfo[i]
                if c < summ:
                    return (i+4, c-offset)
         
        for (c, frame) in enumerate(self.form_config["checkbox_frames"]):
            name = frame["title"]
            fields = frame["fields"]
            list_frame = CheckBoxListFrame(self, name, fields)
            self.checkbox_frames[name] = list_frame
            
            if self.settings:
                list_frame.set_checkbox_values(self.settings["checkbox_frames"][name])

            (row, col) = getRowCol(c)
            list_frame.grid(row=row, column=col, sticky='nswe', padx=5, pady=5)

        return row+1

    def destroy_logger_window(self):
        self.p.terminate()
        self.logger_component.destroy()

    def save_button_callback(self):
        self.save_parsing_configs()

        queue = Queue()        
        logger = Logger(queue)

        self.p = Process(target=Service(logger=logger).main)        
                    
        self.logger_component = LoggerWindow(self, queue)
        self.logger_component.grab_set()
        self.logger_component.protocol("WM_DELETE_WINDOW", self.destroy_logger_window)

        self.p.start()

    def save_parsing_configs(self):
        settings = {
            "sliders": {},
            "checkbox_frames": {}
        }
        for name in self.checkbox_frames:
            settings["checkbox_frames"][name] = self.checkbox_frames[name].get_checkbox_values()
        for name in self.sliders:
            data = self.sliders[name].get()
            settings["sliders"][name] = {
                "min": int(data[0]),
                "max": int(data[1])
            }
        with open(self.config_path, 'w') as f:
            s = json.dumps(settings, ensure_ascii=False, indent=4)
            f.write(s)
        
        self.updateIni(settings)

    def updateIni(self, settings):
        config = configparser.ConfigParser()        
        config.read("cache.ini")

        sliders = settings['sliders']
        cur_section = 'ОБЩИЕ'
        for name in sliders:
            slider = sliders[name]
            if name == 'Год постройки дома':
                config.set(cur_section, "граница старых домов (год)", str(slider["min"]))
                config.set(cur_section, "граница новых домов (год)", str(slider["max"]))
            else:
                config.set(cur_section, "площади", f'{slider["min"]}-{slider["max"]}')

        mapping = {
            "ОБЩИЕ--ПЕРИОДЫ": {
                "старые дома": "выполнить запросы по старым домам",
                "средние дома": "выполнить запросы по средним домам",
                "новые дома": "выполнить запросы по новым домам",
                "неважно": "выполнить запросы по всем домам"
            }
        }

        metro_mapping = {
            "близко к метро": "10",
            "неважно": '""'
        }

        checkbox_frames: Dict[str, any] = settings['checkbox_frames']
        for name in checkbox_frames:
            cur_section = name.replace("-ТИП ОБЪЯВЛЕНИЙ", "ШАГИ").replace("--МЕТРО", "")
            frame = checkbox_frames[name]
            combined = []
            combined_name = ""
            for check_name in frame:
                if cur_section in ["МОСКВА", "ПЕТЕРБУРГ"]:
                    if frame[check_name]:
                        combined.append(metro_mapping[check_name])                        
                        combined_name = "до метро (мин)"
                else:       
                    value = frame[check_name]          
                    if mapping.get(cur_section):
                        if mapping[cur_section].get(check_name):
                            check_name = mapping[cur_section][check_name]

                    config.set(cur_section, check_name, "да" if value else "")

            if len(combined) != 0:
                config.set(cur_section, combined_name, ' '.join(combined))

        with open("cache.ini", 'w') as file:
            config.write(file)

    def load_settings(self):
        settings = None
        try:
            with open(self.config_path) as f:
                s = f.read()
                settings = json.loads(s)
        except FileNotFoundError:
            pass
        self.settings = settings


if __name__ == "__main__":
    checkbox_frames = [
        {
            "title": "ОБЩИЕ--ПЕРИОДЫ",
            "fields": [
                "старые дома",
                "средние дома",
                "новые дома",
                "неважно"
            ]
        },
        {
            "title": "ОБЩИЕ--СОБСТВЕННИК",
            "fields": [
                "от собственника",
                "неважно"
            ]
        },
        {
            "title": "ОБЩИЕ--РЕМОНТ",
            "fields": [
                "дизайнерский",
                "евро",
                "косметический",
                "без ремонта",
                "неважно"
            ]
        },
        {
            "title": "ОБЩИЕ--ЛИФТ",
            "fields": [
                "есть любой",
                "есть грузовой",
                "неважно"
            ]
        },
        {
            "title": "МОСКВА--ТИП ОБЪЯВЛЕНИЙ",
            "fields": [
                "москва продажа",
                "москва аренда"
            ]
        },
        {
            "title": "ПЕТЕРБУРГ--ТИП ОБЪЯВЛЕНИЙ",
            "fields": [
                "петербург продажа",
                "петербург аренда"
            ]
        },
        {
            "title": "СОЧИ--ТИП ОБЪЯВЛЕНИЙ",
            "fields": [
                "сочи продажа",
                "сочи аренда"
            ]
        },        
        {
            "title": "КРАСНОДАР--ТИП ОБЪЯВЛЕНИЙ",
            "fields": [
                "краснодар продажа",
                "краснодар аренда"
            ]
        },
        {
            "title": "ИРКУТСК--ТИП ОБЪЯВЛЕНИЙ",
            "fields": [
                "иркутск продажа",
                "иркутск аренда"
            ]
        },
        {
            "title": "МОСКВА--МЕТРО",
            "fields": [
                "близко к метро",
                "неважно"
            ]
        },
        {
            "title": "ПЕТЕРБУРГ--МЕТРО",
            "fields": [
                "близко к метро",
                "неважно"
            ]
        },
        {
            "title": "СОЧИ--РАЙОНЫ",
            "fields": [
                "адлерский",
                "хостинский",
                "центральный",
                "неважно"
            ]
        },        
        {
            "title": "КРАСНОДАР--РАЙОНЫ",
            "fields": [
                "западный",
                "центральный",
                "карасунский",
                "прикубанский",
                "неважно"
            ]
        },
        {
            "title": "ИРКУТСК--РАЙОНЫ",
            "fields": [
                "ленинский",
                "октябрьский",
                "правобережный",
                "свердловский",
                "неважно"
            ]
        }
    ]

    sliders = [
        {
            "title": "Год постройки дома",
            "min": 1980,
            "max": date.today().year,
            "get_label": lambda x: f'Год постройки дома\nСтарые: до {int(x[0])} года | Новые: от {int(x[1])} года'
        },
        {
            "title": "Площадь квартиры",
            "min": 0,
            "max": 200,
            "get_label": lambda x: f'Площадь квартиры\nот: {int(x[0])} до: {int(x[1])} (m2)'
        }
    ]

    form = {
        "sliders": sliders,
        "checkbox_frames": checkbox_frames
    }

    App(form, 'config.json').mainloop()
