import json, random, threading, urllib.request
from datetime import datetime
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar
RECIPES = {
    "Alface": {"soil_moisture_target_pct": 35, "ambient_temp_target_c": 20, "ambient_temp_min_c": 15, "ambient_temp_max_c": 22, "lighting_hours_per_day": 12},
    "Morango": {"soil_moisture_target_pct": 40, "ambient_temp_target_c": 20, "ambient_temp_min_c": 15, "ambient_temp_max_c": 25, "lighting_hours_per_day": 10},
    "Tomate": {"soil_moisture_target_pct": 40, "ambient_temp_target_c": 24, "ambient_temp_min_c": 18, "ambient_temp_max_c": 30, "lighting_hours_per_day": 12},
}

class HortaApp(App):
    def build(self):
        self.title = "Horta Inteligente"
        self.demo_mode = True
        self.demo = {"soil_moisture_pct": 36.0, "ambient_temp_c": 21.0, 
                     "pump_on": False, "light_on": False, "mode": "manual"}
        self.latest = dict(self.demo)
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10), size_hint_y=None)
        root.bind(minimum_height=root.setter("height"))
        root.add_widget(Label(text="[b]HORTA INTELIGENTE[/b]", markup=True, font_size="26sp", color=(0.2, 0.8, 0.3, 1),
                              size_hint_y=None, height=dp(48)))
        root.add_widget(Label(text="Monitoramento e controle • ESP32 via Wi-Fi",
                              font_size="13sp", size_hint_y=None, height=dp(24)))
        self.mode_label = Label(text="MODO DEMONSTRAÇÃO — dados simulados",
                                color=(0.65,0.35,0.05,1), size_hint_y=None, height=dp(28))
        root.add_widget(self.mode_label)
        row = GridLayout(cols=2, size_hint_y=None, height=dp(44), spacing=dp(6))
        self.ip = TextInput(text="192.168.1.100", hint_text="IP do ESP32", multiline=False)
        self.token = TextInput(hint_text="Token API (se configurado)", multiline=False, password=True)
        row.add_widget(self.ip); row.add_widget(self.token); root.add_widget(row)
        self.conn = Label(text="Demonstração local ativa", size_hint_y=None, height=dp(25))
        root.add_widget(self.conn)
        metrics = GridLayout(cols=2, spacing=dp(5), size_hint_y=None, height=dp(145))
        self.values = {}
        for key,title in [("soil_moisture_pct","Umidade do solo"),("ambient_temp_c","Temperatura ambiente"),
                          ("pump_on","Irrigação"),
                          ("light_on","Iluminação"),("mode","Modo")]:
            cell=BoxLayout(orientation="vertical", padding=dp(4))
            cell.add_widget(Label(text=title, font_size="12sp"))
            val=Label(text="—", font_size="22sp", bold=True)
            cell.add_widget(val); metrics.add_widget(cell); self.values[key]=val
     
        self.add_button(root, "Atualizar leituras", self.refresh)   
        root.add_widget(metrics)
        self.umidade_barra = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(40))
        root.add_widget(self.umidade_barra)
        self.add_button(root, "Alternar: demonstração / ESP32 real", self.toggle_connection_mode)
        controls=GridLayout(cols=2, spacing=dp(5), size_hint_y=None, height=dp(84))
        for title,dev,state in [("Ligar irrigação","pump",True),("Desligar irrigação","pump",False),
                                ("Ligar iluminação","light",True),("Desligar iluminação","light",False)]:
            b=Button(text=title)
            b.bind(on_release=lambda _b,d=dev,s=state:self.control(d,s))
            controls.add_widget(b)
        root.add_widget(controls)
        root.add_widget(Label(text="Receitas de cultivo", size_hint_y=None, height=dp(24)))
        self.recipe = Spinner(text="Alface", values=list(RECIPES), size_hint_y=None, height=dp(40))
        root.add_widget(self.recipe)
        self.recipe_info=Label(text=self.recipe_text("Alface"), size_hint_y=None, height=dp(75), font_size="12sp")
        root.add_widget(self.recipe_info)
        self.recipe.bind(text=lambda _s,n:setattr(self.recipe_info,"text",self.recipe_text(n)))
        self.add_button(root, "Aplicar receita (demonstração/local ou ESP32)", self.apply_recipe)
        self.add_button(root, "Alternar modo automático/manual", self.toggle_auto)
        self.log=Label(text="Demonstração pronta. Nenhum comando físico será enviado enquanto este modo estiver ativo.",
                       size_hint_y=None, height=dp(45), font_size="11sp")
        root.add_widget(self.log)
        self.render_values()
        Clock.schedule_interval(self.simulate_tick, 2.0)
        scroll = ScrollView()
        scroll.add_widget(root)
        return scroll

    def add_button(self, parent, text, callback):
        b=Button(text=text, size_hint_y=None, height=dp(48), background_normal="", background_color=(0.15, 0.6, 0.3, 1))
        b.bind(on_release=lambda *_:callback())
        parent.add_widget(b)

    def recipe_text(self,n):
        r=RECIPES[n]
        return (f"Umidade-alvo {r['soil_moisture_target_pct']}% • Temperatura-alvo {r['ambient_temp_target_c']} °C "
                f"({r['ambient_temp_min_c']}–{r['ambient_temp_max_c']} °C) • Luz {r['lighting_hours_per_day']} h/dia\\n"
                "Parâmetros demonstrativos: revisar para a variedade e o estágio de cultivo.")

    def toggle_connection_mode(self):
        self.demo_mode=not self.demo_mode
        if self.demo_mode:
            self.mode_label.text="MODO DEMONSTRAÇÃO — dados simulados"
            self.mode_label.color=(0.65,0.35,0.05,1)
            self.conn.text="Demonstração local ativa"
            self.log.text="Modo demonstração: comandos alteram apenas valores locais."
            self.render_values()
        else:
            self.mode_label.text="MODO ESP32 — aguardando resposta real"
            self.mode_label.color=(0.1,0.4,0.2,1)
            self.conn.text="Tentando conectar ao ESP32..."
            self.refresh()

    def simulate_tick(self, _dt):
        if self.demo_mode:
            self.demo["soil_moisture_pct"]=round(max(15,min(70,self.demo["soil_moisture_pct"]+random.uniform(-1.5,1.2))),1)
            self.demo["ambient_temp_c"]=round(max(16,min(31,self.demo["ambient_temp_c"]+random.uniform(-0.4,0.4))),1)
            
            self.latest=dict(self.demo)
            self.render_values()

    def render_values(self):
        d=self.latest 
        self.umidade_barra.value = float(d.get("soil_moisture_pct") or 0)
        for k,u in [("soil_moisture_pct"," %"),("ambient_temp_c"," °C")]:
            self.values[k].text="—" if d.get(k) is None else str(d[k])+u
        self.values["pump_on"].text="Ligada" if d.get("pump_on") else "Desligada"
        self.values["pump_on"].color = (0.2, 0.9, 0.3, 1) if d.get("pump_on") else (0.6, 0.6, 0.6, 1)
        self.values["light_on"].text="Ligada" if d.get("light_on") else "Desligada"
        self.values["light_on"].color = (0.2, 0.9, 0.3, 1) if d.get("light_on") else (0.6, 0.6, 0.6, 1)
        self.values["mode"].text=str(d.get("mode","manual")).capitalize()

    def request(self,path,method="GET",payload=None):
        ip=self.ip.text.strip().replace("http://","").replace("https://","").rstrip("/")
        if not ip: raise ValueError("Informe o IP do ESP32.")
        data=None if payload is None else json.dumps(payload).encode()
        headers={"Content-Type":"application/json"}
        if self.token.text.strip(): headers["X-API-Token"]=self.token.text.strip()
        req=urllib.request.Request("http://"+ip+path,data=data,headers=headers,method=method)
        with urllib.request.urlopen(req,timeout=4) as r: return json.loads(r.read().decode() or "{}")

    def async_call(self,fn,success):
        def worker():
            try:
                result=fn(); Clock.schedule_once(lambda _dt:success(result),0)
            except Exception as e:
                msg=str(e); Clock.schedule_once(lambda _dt:self.fail(msg),0)
        threading.Thread(target=worker,daemon=True).start()

    def fail(self,msg):
        self.conn.text="Sem conexão com ESP32"
        self.log.text="Falha de comunicação: "+msg[:130]

    def refresh(self):
        if self.demo_mode:
            self.latest=dict(self.demo); self.render_values()
            self.conn.text="Demonstração local ativa"
            self.log.text="Leituras simuladas atualizadas: "+datetime.now().strftime("%H:%M:%S")
        else:
            self.conn.text="Conectando..."
            self.async_call(lambda:self.request("/api/status"),self.show_status)

    def show_status(self,d):
        self.latest=d; self.conn.text="ESP32 conectado • resposta real recebida"
        self.render_values(); self.log.text="Dados reais atualizados: "+datetime.now().strftime("%H:%M:%S")

    def control(self,dev,state):
        if self.demo_mode:
            self.demo["pump_on" if dev=="pump" else "light_on"]=state
            self.latest=dict(self.demo); self.render_values()
            self.log.text="Simulação local: estado alterado, nenhum equipamento físico acionado."
            return
        self.log.text="Enviando comando e aguardando confirmação..."
        self.async_call(lambda:self.request("/api/control","POST",{"device":dev,"state":state}),self.command_result)

    def apply_recipe(self):
        name=self.recipe.text
        if self.demo_mode:
            self.log.text=f"Receita {name} selecionada na demonstração; ainda não aplicada a hardware real."
            return
        self.async_call(lambda:self.request("/api/recipe","POST",{"name":name,"params":RECIPES[name],"acknowledged":True}),self.command_result)

    def toggle_auto(self):
        current=self.latest.get("mode","manual")
        mode="manual" if current=="auto" else "auto"
        if self.demo_mode:
            self.demo["mode"]=mode; self.latest=dict(self.demo); self.render_values()
            self.log.text="Modo alterado apenas na simulação."
        else:
            self.async_call(lambda:self.request("/api/control","POST",{"device":"mode","state":mode}),self.command_result)

    def command_result(self,d):
        self.log.text="Comando confirmado pelo ESP32." if d.get("ok") else "Comando não confirmado: "+str(d)
        if d.get("ok"): self.refresh()

if __name__=="__main__":
    HortaApp().run()
