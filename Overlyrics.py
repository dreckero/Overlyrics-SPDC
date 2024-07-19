# -*- coding: utf-8 -*-

import tkinter as tk
import tkinter.font as font
from tkinter import messagebox, OptionMenu
from tkinter import simpledialog
from tkinter import colorchooser
import time
from datetime import datetime
import re
import threading
import queue
import sys
from spotify import *
import queue
from apicallspotify import *
from lyricsSaver import *
import pyglet
from os import listdir
from os.path import isfile, join
from fontTools import ttLib
import logging

# Global queue to handle Tkinter updates in the main thread
update_queue = queue.Queue()
pyglet.options['win32_gdi_font'] = True
# Main global variables
# Font global variables
#----------------
#TODO: change this variables to read them from a config file saving latest options used.
selected_theme = "LIGHT" # Default selected theme
main_color = "#00FFFF" # Default selected color for the actual verse that is playing
used_font = 'Circular SP Vietnamese'
used_font_size = 22
font_weight = 'bold'
lines_per_lyrics = 3 # Lines to show per lyrics (make sure that is always an odd number and not more than 15 or it'll be 3 as default)
transparency = 1.0 # Default transparency for the whole windows
display_offset_ms = 200 # Offset in milliseconds to show the actual lyrics
#END TODO

light_color = "#BBBBBB" # Default selected color for light theme
dark_color = "#404040" # Default selected color for dark theme
font_tuple = (used_font, used_font_size, font_weight)
button_canvas = None
canvas2 = None
show_player = True
root = None
#----------------
update_track_info_condition = True # Use to stop the main loop
drag_start_x = False
drag_start_y = None
dragging = None

# Constants:
VERBOSE_MODE = False  # If true, prints specific logs in the code (for debugging)
CUSTOM_EXCEPT_HOOK = True  # If active, errors appear in customized window
PERIOD_TO_UPDATE_TRACK_INFO = 0.1  # Updates the displaying verses every PERIOD_TO_UPDATE_TRACK_INFO seconds
PROGRESS_UPDATE_PERIOD = 0.1  # seconds
PROGRESS_UPDATE_INTERVAL = 1  # seconds
FONT_FOLDER = str(pathlib.Path(__file__).parent.resolve()) + "\\fonts"

def create_overlay_text():
    global main_color, selected_theme, lines_per_lyrics, font_tuple, button_canvas, canvas2, show_player, root
    
    if lines_per_lyrics not in [1, 3, 5, 7, 9, 11, 13, 15]:
        lines_per_lyrics = 3
    
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.attributes("-alpha", transparency)
    root.overrideredirect(True)
    root.configure(bg="#010311")
    root.title("Overlyrics")
    root.wm_attributes('-transparentcolor', root['bg'])

    # Set minimum width and height
    min_width = 300
    min_height = 100
    root.minsize(min_width, min_height)

    # Set an upper indentation based in the font size between the top left canvases and the lyrics
    custom_bar_font = font.Font(family="Arial", size="12", weight="normal")
    upper_bar = tk.Label(root, text="", font=custom_bar_font, fg="#dfe0eb", bg="#010311")
    upper_bar.pack()
    
    # Create labels dynamically based on lines_per_lyric
    text_labels = []
    middle_index = lines_per_lyrics // 2  # Calculate middle index
    
    for i in range(lines_per_lyrics):
        fg_color = main_color if i == middle_index else "#dfe0eb"
        text_label = tk.Label(root, text="", fg=fg_color, bg="#010311", font=font_tuple)
        #text_label.configure(font=font_tuple)
        text_label.pack()
        text_labels.append(text_label)
    
    if show_player:
        # Create canvas for buttons
        init_player_canvas()
    else:
        init_generic_canvas()

    root.bind("<ButtonPress-1>", lambda event: on_drag_start(event, root))
    root.bind("<B1-Motion>", on_dragging)
    root.bind("<ButtonRelease-1>", lambda event: on_window_move_end(event, root))
    root.bind("<Button-3>", on_right_click)
    
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename='D:\\temp\\Log.txt', encoding='utf-8', level=logging.DEBUG)
    logger.debug(FONT_FOLDER)
    
    return root, text_labels

def get_fonts_from_folder():
    fonts = []
    if(os.path.isdir(FONT_FOLDER) == False):
        #No folder for fonts found
        return fonts
    files = [f for f in listdir(FONT_FOLDER) if isfile(join(FONT_FOLDER, f))]
    for file in files:
        if file.endswith('.ttf'):
            fonts.append(file)
    return fonts
# -------------------------------------
# Menu functions
# -------------------------------------
def init_generic_canvas():
    global canvas2, root
    canvas2 = tk.Canvas(root, width=20, height=15, bg="#AAAAAA", highlightthickness=0) #width=root.winfo_screenwidth()
    canvas2.place(x=0, y=0)

def init_player_canvas():
    global button_canvas, root
    button_canvas = tk.Canvas(root, width=100, height=20, bg="#010311", highlightthickness=0)
    button_canvas.place(x=0, y=0)

    # Create left arrow button
    left_arrow_points = [0, 10, 10, 0, 10, 20]
    left_arrow = button_canvas.create_polygon(left_arrow_points, fill="#AAAAAA")
    button_canvas.tag_bind(left_arrow, "<ButtonPress-1>", lambda event: on_drag_start(event, root))
    button_canvas.tag_bind(left_arrow, "<B1-Motion>", on_dragging)
    button_canvas.tag_bind(left_arrow, "<ButtonRelease-1>", lambda event: on_back_click(event, root))
    # Create play/pause button (circle)
    play_pause_button = button_canvas.create_oval(15, 2, 31, 18, fill="#AAAAAA")
    button_canvas.tag_bind(play_pause_button, "<ButtonPress-1>", lambda event: on_drag_start(event, root))
    button_canvas.tag_bind(play_pause_button, "<B1-Motion>", on_dragging)
    button_canvas.tag_bind(play_pause_button, "<ButtonRelease-1>", lambda event: on_play_pause_click(event, root))

    # Create right arrow button
    right_arrow_points = [36, 0, 46, 10, 36, 20]
    right_arrow = button_canvas.create_polygon(right_arrow_points, fill="#AAAAAA")
    button_canvas.tag_bind(right_arrow, "<ButtonPress-1>", lambda event: on_drag_start(event, root))
    button_canvas.tag_bind(right_arrow, "<B1-Motion>", on_dragging)
    button_canvas.tag_bind(right_arrow, "<ButtonRelease-1>", lambda event: on_next_click(event, root))

def on_back_click(event, root):
    global isPaused
    if dragging is False:
        back_playback()

def on_play_pause_click(event, root):
    if dragging is False:
        if isPaused:
            start_resume_playback()
        else:
            pause_playback()

def on_next_click(event, root):
    if dragging is False:
        next_playback()

def on_right_click(event):
    global selected_theme, main_color, overlay_root
    menu = tk.Menu(overlay_root, tearoff=0)
    
    menu.add_command(label="Choose Color", command=set_color)
    
    if selected_theme == "DARK":
        menu.add_command(label="Light Theme", command=switch_to_light_theme)
    else:
        menu.add_command(label="Dark Theme", command=switch_to_dark_theme)
    
    menu.add_command(label="Set Font Size", command=change_font_size)
    menu.add_command(label="Set lyrics offset", command=change_display_offset_ms)
    menu.add_command(label="Set transparency", command=change_transparency)
    menu.add_command(label="Set lines per lyrics", command=change_lines_per_lyrics)
    menu.add_command(label="Switch to player/square", command=switch_player_square)
    menu.add_command(label="Change Font", command=change_font)
    menu.add_separator()
    menu.add_command(label="Close", command=close_application)
    
    menu.post(event.x_root, event.y_root)

def switch_to_light_theme():
    global selected_theme, overlay_root, overlay_text_labels, main_color, light_color
    selected_theme = "LIGHT"
    middle_index = len(overlay_text_labels) // 2
    for i, label in enumerate(overlay_text_labels):
        if i != middle_index:
            label.config(fg=light_color)
        else:
            label.config(fg=main_color)
            
    overlay_root.update()

def switch_to_dark_theme():
    global selected_theme, overlay_root, overlay_text_labels, main_color, dark_color
    selected_theme = "DARK"
    middle_index = len(overlay_text_labels) // 2
    for i, label in enumerate(overlay_text_labels):
        if i != middle_index:
            label.config(fg=dark_color)
        else:
            label.config(fg=main_color)
    overlay_root.update()

def on_drag_start(event, root):
    global drag_start_x, drag_start_y
    drag_start_x = event.x
    drag_start_y = event.y

def on_dragging(event):
    global drag_start_x, drag_start_y, overlay_root, dragging
    dragging = True
    root_x = overlay_root.winfo_x() + (event.x - drag_start_x)
    root_y = overlay_root.winfo_y() + (event.y - drag_start_y)
    overlay_root.geometry(f"+{root_x}+{root_y}")

def on_window_move_end(event, root):
    global dragging
    dragging = False
    # This is to handle any cleanup after dragging ends, if needed
    pass
    
def set_color():
    global main_color, overlay_text_labels
    
    color_code = colorchooser.askcolor(title="Choose color")[1]
    if color_code:
        main_color = color_code
        middle_index = len(overlay_text_labels) // 2
        for i, label in enumerate(overlay_text_labels):
            if i == middle_index:
                label.config(fg=main_color)
        overlay_root.update()

def open_integer_input(text, min, max):
    value = simpledialog.askinteger(" ", text, minvalue=min, maxvalue=max)
    return value

def open_float_input(text, min, max):
    value = simpledialog.askfloat(" ", text, minvalue=min, maxvalue=max)
    return value

def change_font_size():
    global used_font_size, font_tuple
    value = open_integer_input("Enter font size:", 8, 72)
    if value:
        used_font_size = value
        font_tuple = (used_font, used_font_size, font_weight)
        overlay_root.update()
        
def change_display_offset_ms():
    global display_offset_ms
    value = open_integer_input("Enter offset:", -5000, 5000)
    if value:
        display_offset_ms = value
        overlay_root.update()
        
def change_transparency():
    global transparency, overlay_root
    value = open_float_input("Enter offset:", 0.1, 1.0)
    if value:
        transparency = value
        overlay_root.attributes("-alpha", transparency)
        overlay_root.update()
        
def change_lines_per_lyrics():
    global lines_per_lyrics, overlay_text_labels, overlay_root
    
    value = open_integer_input("Enter offset:", 1, 15)
    if value:
        if value not in [1, 3, 5, 7, 9, 11, 13, 15]:
            lines_per_lyrics = 3
        else:
            lines_per_lyrics = value
    
    for label in overlay_text_labels:
        label.destroy()  # Remove existing labels
    overlay_text_labels.clear()
    
    middle_index = lines_per_lyrics // 2  # Calculate middle index
    
    for i in range(lines_per_lyrics):
        fg_color = main_color if i == middle_index else "#dfe0eb"
        text_label = tk.Label(overlay_root, text="", fg=fg_color, bg="#010311")
        text_label.pack()
        overlay_text_labels.append(text_label)
    
    overlay_root.update()

def switch_player_square():
    global canvas2, button_canvas, show_player
    
    if show_player:
        button_canvas.place_forget()
        init_generic_canvas()
        show_player = False
    else:
        canvas2.place_forget()
        init_player_canvas()
        show_player = True
    
    overlay_root.update()

#open windows with font selector
def change_font():
    global root
    win = tk.Toplevel()
    win.wm_title("Change Font")

    #calculates geometry of screen to appear in middle
    w = 200 # width for the Tk root
    h = 100 # height for the Tk root
    # get screen width and height
    ws = win.winfo_screenwidth() # width of the screen
    hs = win.winfo_screenheight() # height of the screen   
    # calculate x and y coordinates for the Tk root window
    x = (ws/2) - (w/2)
    y = (hs/2) - (h/2)
    win.geometry('%dx%d+%d+%d' % (w, h, x, y))
    
    #searches and fills list of fonts obtained from folder
    fonts = get_fonts_from_folder()
    valor = tk.StringVar(win, value='Select Font...')
    drop = OptionMenu(win , valor , *fonts ) 
    drop.grid(row=0, column=0)
    b = tk.Button(win, text="Confirm", command= lambda: font_change_confirm(win, valor.get()))
    b.grid(row=1, column=0)

    win.grid_rowconfigure(0, weight=1)
    win.grid_columnconfigure(0, weight=1)
    overlay_root.update()

def font_change_confirm(win, value):
    global used_font, font_tuple, used_font_size, font_weight
    print(value)
    font_file = ttLib.TTFont(FONT_FOLDER + "\\" + value)
    fontFamilyName = font_file['name'].getDebugName(4)
    used_font = fontFamilyName
    font_tuple = (used_font, used_font_size, font_weight)
    #create_overlay_text()
    win.destroy()
    
def close_application():
    global update_track_info_condition
    update_track_info_condition = False
    overlay_root.quit()
    update_thread.join()  # Wait for the update_track_info thread to finish
    update_display_thread.join()  # Wait for the update_display thread to finish
    overlay_root.destroy()
    sys.exit()

# -------------------------------------
# End Menu functions
# -------------------------------------

def update_overlay_text():
    global actualTrackLyrics, actualVerse, parsed_lyrics, time_str, timestampsInSeconds, lines_per_lyrics

    def find_nearest_time(currentProgress, timestampsInSeconds, parsed_lyrics):
        keys_list = list(parsed_lyrics.keys())
        # Find the verse that is closest in time before the current progress + offset
        filtered_keys = list(filter(lambda x: timestampsInSeconds[keys_list.index(x)] <= currentProgress + (display_offset_ms / 1000), keys_list))

        if not filtered_keys:
            verse = keys_list[0]  # If no previous verse, show the first one
        else:
            verse = max(filtered_keys, key=lambda x: timestampsInSeconds[keys_list.index(x)])  # Show the closest previous verse
        return verse

    if parsing_in_progress_event.is_set():
        return
    elif time_str == "TypeError" or time_str == [] or parsed_lyrics == {}:
        update_queue.put(([""] * lines_per_lyrics, -1))  # Put empty lines for each lyric line
    else:
        currentLyricTime = find_nearest_time(currentProgress, timestampsInSeconds, parsed_lyrics)
        actualVerse = parsed_lyrics[currentLyricTime]

        keys_list = list(parsed_lyrics.keys())
        current_index = keys_list.index(currentLyricTime)

        # Prepare verses to put in the queue based on lines_per_lyric
        previous_verses = []
        next_verses = []
        half_lines = lines_per_lyrics // 2

        for i in range(half_lines):
            previous_verse = parsed_lyrics[keys_list[current_index - i - 1]] if current_index - i - 1 >= 0 else ""
            previous_verses.insert(0, previous_verse)  # Insert at the beginning to maintain order
            next_verse = parsed_lyrics[keys_list[current_index + i + 1]] if current_index + i + 1 < len(keys_list) else ""
            next_verses.append(next_verse)
        
        print(f"Previous verse: {previous_verses}\nActual verse: {actualVerse}\nNext verse: {next_verses}") if VERBOSE_MODE else None
        
        verses_to_queue = previous_verses + [actualVerse] + next_verses
        update_queue.put((verses_to_queue, half_lines))

        lyrics_verse_event.set()


def update_gui_texts(verses_data):
    global overlay_text_labels
    
    verses, actual_index = verses_data
    print(f"Updating GUI: {verses}") if VERBOSE_MODE else None
    for i, verse in enumerate(verses):
        if i < len(overlay_text_labels):
            overlay_text_labels[i].config(text=verse, font=font_tuple)
    overlay_root.update()

def process_queue():
    try:
        while True:
            verses = update_queue.get_nowait()
            update_gui_texts(verses)
    except queue.Empty:
        pass
    overlay_root.after(100, process_queue)  # Check the queue every 100 ms


def getCurrentTrackInfo(update_from_spotify):
    global trackName, artistName, currentProgress, isPaused, item, song_id
    try:
        if update_from_spotify:
            current_track = get_currently_playing()  # Get the information of the music being listened to, through the API

            # Check if there is music playing
            if current_track is None or (current_track['item'] is None):
                return None  # No track is currently playing

            # Extract relevant information from the track
            artist = current_track['item']['artists'][0]['name']
            track_name = current_track['item']['name']
            is_playing = current_track['is_playing']
            progress_ms = current_track['progress_ms']
            song_id = current_track['item']['id']

            # Convert progress_ms to minutes and seconds
            progress_sec = progress_ms // 1000
            progress_min = progress_sec // 60
            progress_sec %= 60

            # Return
            return {
                'artist': artist,
                'trackName': track_name,
                'progressMin': progress_min,
                'progressSec': progress_sec,
                'isPlaying': is_playing,
                'item': current_track['item'],
                'song_id': song_id
            }
        else:
            return {
                'artist': artistName,
                'trackName': trackName,
                'progressMin': currentProgress // 60,
                'progressSec': currentProgress % 60,
                'isPlaying': not isPaused,
                'item': item,
                'song_id': song_id
            }
    except Exception as e:
        refresh_access_token()
        return getCurrentTrackInfo(update_from_spotify)

# Function to update song information
def update_track_info():
    global trackName, artistName, currentProgress, isPaused, item, song_id, get_current_first_time

    last_update_time = time.time()
    next_spotify_update = time.time() + PROGRESS_UPDATE_INTERVAL

    while update_track_info_condition:
        current_time = time.time()

        # Update progress internally
        if current_time - last_update_time >= PROGRESS_UPDATE_PERIOD:
            if isPaused:
                currentProgress = currentProgress # Keep the same if paused
            else:
                currentProgress = currentProgress + PROGRESS_UPDATE_PERIOD if currentProgress is not None else 0 # Simulate progress

            trackName, artistName, currentProgress, isPaused, item, song_id = get_track_info(get_current_first_time)
            if get_current_first_time:
                get_current_first_time = False
            last_update_time = current_time

        # Update from Spotify periodically
        if current_time >= next_spotify_update:
            trackName, artistName, currentProgress, isPaused, item, song_id = get_track_info(True)
            next_spotify_update = current_time + PROGRESS_UPDATE_INTERVAL

        time.sleep(PERIOD_TO_UPDATE_TRACK_INFO)  # Wait before the next loop iteration

# Function to get the useful song information
def get_track_info(consumeSpotifyAPI):
    global trackName, artistName, currentProgress, isPaused, item, song_id

    trackInfo = getCurrentTrackInfo(consumeSpotifyAPI)

    if(trackInfo is None):
        trackName = artistName = currentProgress = isPaused = song_id = None
    else:    
        previousTrackName = trackName

        trackName = trackInfo['trackName']
        artistName = trackInfo['artist']
        currentProgress = trackInfo['progressMin'] * 60 + trackInfo['progressSec']
        isPaused = not trackInfo['isPlaying']
        item = trackInfo['item']
        song_id = trackInfo['song_id']

        print("get_track_info(): ", trackName) if VERBOSE_MODE else None
        if((previousTrackName != trackName) and (trackName != None) and (trackName != " ")):
            print("get_track_info() - nova musica: " + trackName) if VERBOSE_MODE else None
            update_track_event.set()
            parsing_in_progress_event.set()


    update_event.set()  # Flag that variables have been updated

    return trackName, artistName, currentProgress, isPaused, item, song_id

def update_display():
    while update_track_info_condition:
        display_lyrics(trackName, artistName, currentProgress, isPaused, item)
        
        if trackName is None:
            noMusicIsPlayingOnSpotify()
        else:
            update_overlay_text()
        time.sleep(0.1)  # Add a small sleep to avoid busy-waiting

# Function to display the synchronized lyrics
def display_lyrics(trackName, artistName, currentProgress, isPausedm, item):
        global actualTrackLyrics, parsed_lyrics, time_str, timestampsInSeconds

        def getParsedLyrics(lyrics): ## Returns a dict with the entire lyrics and the respectively timestamps
            lines = lyrics.split('\n')  # Divides the lyrics by the verses/lines
            parsed_lyrics = {}  # Dict to storage strings of timestaps and the text lyrics
            time_strs = []

            for line in lines:
                line = line.strip() # Removes the initial backspace
                if line and line.startswith("["):
                    parsed_line = parse_line(line)
                    if parsed_line:
                        time_str, verse_text = parsed_line
                        parsed_lyrics[time_str] = verse_text
                        time_strs.append(time_str)

            return parsed_lyrics, time_strs

        def parse_line(line): # Parses the timestamp and the verse in LRC (Lyric File Format)
            pattern = r'\[(\d{2}:\d{2}\.\d{2})\](.+)'
            match = re.match(pattern, line)

            if match:
                time_str = match.group(1)
                verse_text = match.group(2).strip()
                return time_str, verse_text

            else:
                print("Returning None in parse_line().") if VERBOSE_MODE else None
                return None

        def convert_to_seconds(time_strs):
            total_seconds = []
            for i, time_str in enumerate(time_strs):
                time_obj = datetime.strptime(time_str, "%M:%S.%f")
                seconds = (time_obj.minute * 60) + time_obj.second + (time_obj.microsecond / 1000000)
                total_seconds.append(seconds)
            return total_seconds


        print("trackName in display_lyrics: ", trackName) if VERBOSE_MODE else None

        if (update_track_event.is_set()):
            # If the track has changed, than the new lyrics will be searched and the windows will be updated
            update_track_event.clear()

            #searches for the song in the song folder, if it doesn't exists then it saves it.
            searchOnFolder = SearchLyricsOnFolder(song_id)
            if(searchOnFolder['result']):
                lyrics = searchOnFolder['lyrics']
            else:
                lyrics = GetLyricsOfCurrentSong(item)
                if lyrics:
                    SaveLyrics(song_id, lyrics)
                
            set_progress_ms(0)
            #print(lyrics)
            if (lyrics is None or lyrics.isspace()):
                print("Track not found.") if VERBOSE_MODE else None
                nolyricsfound()
            else:
                print("display_lyrics: >>", trackName, "<<") if VERBOSE_MODE else None
                
                actualTrackLyrics = lyrics
                parsed_lyrics, time_str = getParsedLyrics(actualTrackLyrics)             
                timestampsInSeconds = convert_to_seconds(time_str)

            parsing_in_progress_event.clear()

        update_event.wait()  # Waiting until the variables update
        update_event.clear()  # Clearing the update signal event

def nolyricsfound():
    global actualVerse, parsed_lyrics
    parsed_lyrics={}
    actualVerse='No lyrics found.'
    lyrics_verse_event.set()

def noMusicIsPlayingOnSpotify():
    global actualVerse
    actualVerse = "No song is being heard on Spotify."
    lyrics_verse_event.set()

def custom_excepthook(exctype, value, traceback): # If activated, execution time errors opens a windows to handle the error
    root = tk.Tk()
    root.withdraw()  # Hides the main window to show only the error window
    messagebox.showerror("Overlyrics: Error", f"The following error occurred: {value}")
    root.destroy()

def load_fonts_from_folder():
    fonts = get_fonts_from_folder()
    for f in fonts:
        font_dir = FONT_FOLDER + "\\" + f
        pyglet.font.add_file(font_dir)

# Custom excepthook if activated 
if CUSTOM_EXCEPT_HOOK == True:
    sys.excepthook = custom_excepthook

# Global variables
trackName = ""
artistName = ""
currentProgress = 0
isPaused = False
item = ''
actualVerse = ""
get_current_first_time = True

actualTrackLyrics = ""
parsed_lyrics = {}
time_str = ""
timestampsInSeconds = []

load_fonts_from_folder()
init()

overlay_root, overlay_text_labels = create_overlay_text()
overlay_root.update()

update_event = threading.Event() # Create an event to flag the variables update
update_track_event = threading.Event() # Create an event to flag the track update
lyrics_verse_event = threading.Event() # Create an event to flag the verse update
parsing_in_progress_event = threading.Event() # Create an event to flag the parsing in progress

# Updates the track infos in a separated thread, every PERIOD_TO_UPDATE_TRACK_INFO seconds
update_thread = threading.Thread(target=update_track_info)
update_thread.start()

# Updates the main window continuously, in a separate thread
update_display_thread = threading.Thread(target=update_display)
update_display_thread.start()

# Start processing the queue in the main loop
overlay_root.after(100, process_queue)

# Start the Tkinter main loop
overlay_root.mainloop()