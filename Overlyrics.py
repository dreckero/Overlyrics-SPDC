# -*- coding: utf-8 -*-

import tkinter as tk
import tkinter.font as font
from tkinter import messagebox, OptionMenu
from tkinter import simpledialog
from tkinter import colorchooser
from tkinter import Scale
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
import math
from lrc_adjuster import *
from config_loader import *

# Global queue to handle Tkinter updates in the main thread
update_queue = queue.Queue()
pyglet.options['win32_gdi_font'] = True
# Main global variables
# Font global variables
#----------------
#creates the config file just in case, as a treat
createInitConfig()
selected_theme = getConfigValue("selected_theme") # Default selected theme
main_color = getConfigValue("main_color") # Default selected color for the actual verse that is playing
theme_color = getConfigValue("theme_color")
used_font = getConfigValue("used_font")
used_font_size = getConfigValue("used_font_size")
font_weight = getConfigValue("font_weight")
lines_per_lyrics = getConfigValue("lines_per_lyrics") # Lines to show per lyrics (make sure that is always an odd number and not more than 15 or it'll be 3 as default)
transparency = getConfigValue("transparency") # Default transparency for the whole windows
show_player = getConfigValue("show_player")
show_volume_variable = True
dont_cut_title = True

light_color = "#BBBBBB" # Default selected color for light theme
dark_color = "#404040" # Default selected color for dark theme
transparent_color = "#010311"
font_tuple = (used_font, used_font_size, font_weight)
button_canvas = None
canvas2 = None
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
    global main_color, selected_theme, lines_per_lyrics, font_tuple, button_canvas, canvas2, show_player, show_volume_variable
    
    if lines_per_lyrics not in [1, 3, 5, 7, 9, 11, 13, 15]:
        lines_per_lyrics = 3
        configure("lines_per_lyrics", lines_per_lyrics)
    
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.attributes("-alpha", transparency)
    root.overrideredirect(True)
    root.configure(bg=transparent_color)
    root.title("Overlyrics")
    root.wm_attributes('-transparentcolor', root['bg'])

    # Set minimum width and height
    min_width = 46
    min_height = 20
    root.minsize(min_width, min_height)

    artist_song_font = font.Font(family=used_font, size="12", weight="normal")
    artist_song_label = tk.Label(root, text="", fg=theme_color, bg=transparent_color, font=artist_song_font)
    artist_song_label.place(x=50, y=0)
    # artist_song_label.pack(side='top')
    
    # Set an upper indentation based in the font size between the top left canvases and the lyrics
    custom_bar_font = font.Font(family="Arial", size="12", weight="normal")
    upper_bar = tk.Label(root, text="", font=custom_bar_font, fg=theme_color, bg=transparent_color)
    upper_bar.pack(side='top')
    
    # Create labels dynamically based on lines_per_lyric
    text_labels = []
    middle_index = lines_per_lyrics // 2  # Calculate middle index
    
    slider = Scale(root, from_=100, to=0, orient='vertical', bg=theme_color, bd=0, showvalue=0, troughcolor=transparent_color, highlightbackground=theme_color, length=120)
    slider.bind("<ButtonRelease-1>", set_volume)
    if show_volume_variable:
        slider.pack(side='left', padx=14)
    
    for i in range(lines_per_lyrics):
        fg_color = main_color if i == middle_index else theme_color
        text_label = tk.Label(root, text="", fg=fg_color, bg=transparent_color, font=font_tuple)
        #text_label.configure(font=font_tuple)
        text_label.pack()
        text_labels.append(text_label)
    
    if show_player:
        # Create canvas for buttons
        init_player_canvas(root)
    else:
        init_generic_canvas(root)

    # root.bind("<ButtonPress-1>", lambda event: on_drag_start(event, root))
    # root.bind("<B1-Motion>", on_dragging)
    # root.bind("<ButtonRelease-1>", lambda event: on_window_move_end(event, root))
    # root.bind("<Button-3>", on_right_click)
    
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename='D:\\temp\\Log.txt', encoding='utf-8', level=logging.DEBUG)
    logger.debug(FONT_FOLDER)
    
    return root, text_labels, artist_song_label, slider

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
def init_generic_canvas(root):
    global canvas2, overlay_root
    canvas2 = tk.Canvas(root, width=20, height=15, bg=theme_color, highlightthickness=0) #width=root.winfo_screenwidth()
    bind_click_conditions(canvas2, root)
    canvas2.place(x=0, y=3)

def init_player_canvas(root):
    global button_canvas
    button_canvas = tk.Canvas(root, width=46, height=20, bg=transparent_color, highlightthickness=0)
    bind_click_conditions(button_canvas, root)
    button_canvas.place(x=0, y=3)

    # Create left arrow button
    left_arrow_points = [0, 10, 10, 0, 10, 20]
    left_arrow = button_canvas.create_polygon(left_arrow_points, fill=theme_color)
    button_canvas.tag_bind(left_arrow, "<ButtonPress-1>", lambda event: on_drag_start(event, root))
    button_canvas.tag_bind(left_arrow, "<B1-Motion>", on_dragging)
    button_canvas.tag_bind(left_arrow, "<ButtonRelease-1>", lambda event: on_back_click(event, root, left_arrow))
    # Create play/pause button (circle)
    play_pause_button = button_canvas.create_oval(15, 2, 31, 18, fill=theme_color)
    button_canvas.tag_bind(play_pause_button, "<ButtonPress-1>", lambda event: on_drag_start(event, root))
    button_canvas.tag_bind(play_pause_button, "<B1-Motion>", on_dragging)
    button_canvas.tag_bind(play_pause_button, "<ButtonRelease-1>", lambda event: on_play_pause_click(event, root, play_pause_button))

    # Create right arrow button
    right_arrow_points = [36, 0, 46, 10, 36, 20]
    right_arrow = button_canvas.create_polygon(right_arrow_points, fill=theme_color)
    button_canvas.tag_bind(right_arrow, "<ButtonPress-1>", lambda event: on_drag_start(event, root))
    button_canvas.tag_bind(right_arrow, "<B1-Motion>", on_dragging)
    button_canvas.tag_bind(right_arrow, "<ButtonRelease-1>", lambda event: on_next_click(event, root, right_arrow))

def bind_click_conditions(object, root):
    object.bind("<ButtonPress-1>", lambda event: on_drag_start(event, root))
    object.bind("<B1-Motion>", on_dragging)
    object.bind("<ButtonRelease-1>", lambda event: on_window_move_end(event, root))
    object.bind("<Button-3>", on_right_click)

def on_back_click(event, root, left_arrow):
    if dragging is False:
        paint_main_color(left_arrow)
        back_playback()
        pain_theme_color(left_arrow)

def on_play_pause_click(event, root, play_pause_button):
    if dragging is False:
        paint_main_color(play_pause_button)
        if isPaused:
            start_resume_playback()
        else:
            pause_playback()
        pain_theme_color(play_pause_button)

def on_next_click(event, root, right_arrow):
    if dragging is False:
        paint_main_color(right_arrow)
        next_playback()
        pain_theme_color(right_arrow)
        

def paint_main_color(button_id):
    button_canvas.itemconfig(button_id, fill=main_color)
    overlay_root.update()
    
def pain_theme_color(button_id):
    time.sleep(0.1) 
    button_canvas.itemconfig(button_id, fill=theme_color)
    overlay_root.update()

def on_right_click(event):
    global selected_theme, main_color, overlay_root
    menu = tk.Menu(overlay_root, tearoff=0)
    
    menu.add_command(label="Choose color", command=set_color)
    menu.add_command(label="Switch theme", command=switch_theme)
    menu.add_command(label="Set font size", command=change_font_size)
    menu.add_command(label="Set lyrics offset", command=change_display_offset_ms)
    menu.add_command(label="Set transparency", command=change_transparency)
    menu.add_command(label="Set lines per lyrics", command=change_lines_per_lyrics)
    menu.add_command(label="Switch to player/square", command=switch_player_square)
    menu.add_command(label="Change font", command=change_font)
    menu.add_command(label="Show volume", command=show_volume)
    menu.add_separator()
    menu.add_command(label="Close", command=close_application)
    
    menu.post(event.x_root, event.y_root)

def switch_theme():
    global selected_theme, overlay_root, overlay_text_labels, main_color, light_color, dark_color, theme_color, canvas2, button_canvas
    if selected_theme == 'DARK':
        selected_theme = 'LIGHT'
        configure("selected_theme", selected_theme)
        theme_color = light_color
        configure("theme_color", theme_color)
    else:
        selected_theme = 'DARK'
        configure("selected_theme", selected_theme)
        theme_color = dark_color
        configure("theme_color", theme_color)
        
    middle_index = len(overlay_text_labels) // 2
    for i, label in enumerate(overlay_text_labels):
        if i != middle_index:
            label.config(fg=theme_color)
        else:
            label.config(fg=main_color)
    
    artist_song_label.config(fg=theme_color)
    
    if show_player:
        items = button_canvas.find_all()
        for item in items:
            button_canvas.itemconfig(item, fill=theme_color)
    else:
        canvas2.config(bg=theme_color)
    
    
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
        configure("main_color", main_color)
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
        configure("used_font_size", used_font_size)
        font_tuple = (used_font, used_font_size, font_weight)
        overlay_root.update()
        
def change_display_offset_ms():
    global actualTrackLyrics
    value = open_integer_input("Enter offset:", -5000, 5000)
    if value:
        lyr = SearchLyricsOnFolder(song_id)
        if lyr['result']:
            adjust_file(lyr['route'], value)
            actualTrackLyrics = lyr['lyrics']
            update_track_event.set()
            display_lyrics(trackName, artistName, currentProgress, isPaused, item)
        overlay_root.update()
        
def change_transparency():
    global transparency, overlay_root
    value = open_float_input("Enter offset:", 0.1, 1.0)
    if value:
        transparency = value
        configure("transparency", transparency)
        overlay_root.attributes("-alpha", transparency)
        overlay_root.update()
        
def change_lines_per_lyrics():
    global lines_per_lyrics, overlay_text_labels, overlay_root
    
    value = open_integer_input("Enter offset:", 1, 15)
    if value:
        if value not in [1, 3, 5, 7, 9, 11, 13, 15]:
            lines_per_lyrics = 3
            configure("lines_per_lyrics", lines_per_lyrics)
        else:
            lines_per_lyrics = value
            configure("lines_per_lyrics", lines_per_lyrics)
    
    for label in overlay_text_labels:
        label.destroy()  # Remove existing labels
    overlay_text_labels.clear()
    
    middle_index = lines_per_lyrics // 2  # Calculate middle index
    
    for i in range(lines_per_lyrics):
        fg_color = main_color if i == middle_index else theme_color
        text_label = tk.Label(overlay_root, text="", fg=fg_color, bg=transparent_color)
        text_label.pack()
        overlay_text_labels.append(text_label)
    
    overlay_root.update()

def switch_player_square():
    global canvas2, button_canvas, show_player, overlay_root
    
    if show_player:
        button_canvas.place_forget()
        init_generic_canvas(overlay_root)
        show_player = False
    else:
        canvas2.place_forget()
        init_player_canvas(overlay_root)
        show_player = True
    configure("show_player", show_player)
    
    overlay_root.update()

#open windows with font selector
def change_font():
    global overlay_root
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
    global used_font, font_tuple, used_font_size, font_weight, artist_song_label, overlay_root
    print(value)
    font_file = ttLib.TTFont(FONT_FOLDER + "\\" + value)
    fontFamilyName = font_file['name'].getDebugName(4)
    used_font = fontFamilyName
    configure("used_font", used_font)
    artist_song_font = font.Font(family=used_font, size="12", weight="normal")
    artist_song_label.config(font=artist_song_font)
    font_tuple = (used_font, used_font_size, font_weight)
    #create_overlay_text()
    win.destroy()
    overlay_root.update()

def show_volume():
    global volume_slider, show_volume_variable
    if show_volume_variable == True:
        volume_slider.pack_forget()
        show_volume_variable = False
    else:
        for label in overlay_text_labels:
            label.pack_forget()
        
        volume_slider.pack(side='left', padx=14)
        for label in overlay_text_labels:
            label.pack()
        show_volume_variable = True

def set_volume(event):
    global overlay_root, volume_slider
    value = volume_slider.get()
    if value:
        set_refresh_volume(False)
        volume_playback(value)
        overlay_root.update()
        time.sleep(PROGRESS_UPDATE_INTERVAL *2)
        set_refresh_volume(True)
    
def close_application():
    global update_track_info_condition, overlay_root
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
        filtered_keys = list(filter(lambda x: timestampsInSeconds[keys_list.index(x)] <= currentProgress, keys_list))

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
    global overlay_text_labels, artist_song_label, overlay_root
    
    verses, actual_index = verses_data
    print(f"Updating GUI: {verses}") if VERBOSE_MODE else None
    for i, verse in enumerate(verses):
        if i < len(overlay_text_labels):
            overlay_text_labels[i].config(text=verse, font=font_tuple)
            overlay_text_labels[0].config(text="No lyrics found.", font=font_tuple) if actual_index == -1 else None
    artist_song_label.config(text=artist_song_text)
    artist_song_label.tkraise()
    overlay_root.minsize(math.ceil(len(artist_song_text) * 10.3), 20) if dont_cut_title else None
    overlay_root.update()

def process_queue():
    try:
        global overlay_root
        while True:
            verses = update_queue.get_nowait()
            update_gui_texts(verses)
    except queue.Empty:
        pass
    overlay_root.after(100, process_queue)  # Check the queue every 100 ms


def getCurrentTrackInfo(update_from_spotify):
    global trackName, artistName, currentProgress, isPaused, item, song_id, artist_song_text, volume_slider
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
            artist_song_text = artist + " - " + track_name
            # volume_percent = current_track['device']['volume_percent']
            volume_slider.set(get_volume_percent())
            
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
artist_song_text = ""
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

overlay_root, overlay_text_labels, artist_song_label, volume_slider = create_overlay_text()
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