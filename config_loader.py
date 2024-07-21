import json
import os.path

def getAllConfig():
    if(os.path.isfile('config.json')):
        with open('config.json', 'r') as f:
            config = json.load(f)
        f.close()
        return config
    else:
        print('Json config file doesnt exists')
        return ''

def getConfigValue(key):
    if(os.path.isfile('config.json')):
        with open('config.json', 'r') as f:
            config = json.load(f)
        f.close()
        if key in config:
            return config[key]
        else:
            print("key doesnt exists in config file")
            return ''
    else:
        print('Json config file doesnt exists')
        return ''

def configure(key, value):
    if(os.path.isfile('config.json')):
        with open('config.json', 'r') as f:
            config = json.load(f)
            f.close()
        if key in config:
            config[key] = value
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=2)
            f.close()
            return True
        else:
            print("key doesnt exists in config file")
            return False
    else:
        print('Json config file doesnt exists')
        return False
    
#method for creating the base config file if necessary
def createInitConfig():
    if(os.path.isfile('config.json') == False):
        with open('config.json', 'w') as f:
            config = {
                "selected_theme": "LIGHT",
                "main_color": "#00FFFF",
                "theme_color": "#BBBBBB",
                "used_font": "Circular SP Vietnamese",
                "used_font_size": 22,
                "font_weight": "bold",
                "lines_per_lyrics": 3,
                "transparency": 1.0,
                "show_player": True
            }
            json.dump(config, f, indent=2)
            f.close()