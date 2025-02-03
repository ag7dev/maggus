import json
import os
import sys
from pynput import keyboard
from colorama import init, Fore, Back, Style
import time

# Initialize colorama
init(autoreset=True)

def on_release(key):
    try:
        if key == keyboard.Key.f1:
            maggu.update_status_aimbot()
        if key == keyboard.Key.f2:
            maggu.clean_up()
    except NameError:
        pass

def main():
    global maggu
    maggu = Aimbot(collect_data="collect_data" in sys.argv)
    maggu.start()

def setup():
    print(Fore.YELLOW + "[INFO] " + Fore.WHITE + "In-game X and Y axis sensitivity should be the same")

    def prompt(str):
        valid_input = False
        while not valid_input:
            try:
                number = float(input(str))
                valid_input = True
            except ValueError:
                print(Fore.RED + "[!] " + Fore.WHITE + "Invalid Input. Make sure to enter only the number (e.g. 6.9)")
        return number

    xy_sens = prompt(Fore.CYAN + "X-Axis and Y-Axis Sensitivity (from in-game settings): " + Fore.WHITE)
    targeting_sens = prompt(Fore.CYAN + "Targeting Sensitivity (from in-game settings): " + Fore.WHITE)

    print(Fore.YELLOW + "[INFO] " + Fore.WHITE + "Your in-game targeting sensitivity must be the same as your scoping sensitivity")
    sensitivity_settings = {"xy_sens": xy_sens, "targeting_sens": targeting_sens, "xy_scale": 10/xy_sens, "targeting_scale": 1000/(targeting_sens * xy_sens)}

    # Ensure the config directory exists
    config_dir = 'lib/config'
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    # Write the settings to the config.json file
    with open(os.path.join(config_dir, 'config.json'), 'w') as outfile:
        json.dump(sensitivity_settings, outfile)
    print(Fore.GREEN + "[INFO] " + Fore.WHITE + "Sensitivity configuration complete")

if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

    print(Fore.GREEN + '''
███╗   ███╗ █████╗  ██████╗  ██████╗ ██╗   ██╗
████╗ ████║██╔══██╗██╔════╝ ██╔════╝ ██║   ██║
██╔████╔██║███████║██║  ███╗██║  ███╗██║   ██║
██║╚██╔╝██║██╔══██║██║   ██║██║   ██║██║   ██║
██║ ╚═╝ ██║██║  ██║╚██████╔╝╚██████╔╝╚██████╔╝
╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝  ╚═════╝ 
                                              
(Neural Network Aimbot)
''')

    path_exists = os.path.exists("lib/config/config.json")
    if not path_exists or ("setup" in sys.argv):
        if not path_exists:
            print(Fore.RED + "[!] " + Fore.WHITE + "Sensitivity configuration is not set")
        setup()

    path_exists = os.path.exists("lib/data")
    if "collect_data" in sys.argv and not path_exists:
        os.makedirs("lib/data")

    from lib.aimbot import Aimbot
    listener = keyboard.Listener(on_release=on_release)
    listener.start()

    print(Fore.GREEN + "[STATUS] " + Fore.WHITE + "Starting Maggu Aimbot...")
    main()
