import os
import shutil
import youtube_dl
from flask import Flask, render_template, redirect, request, escape
from pydal import DAL, Field

app = Flask(__name__)
app.config["SECRET_KEY"] = "PUT_YOUR_OWN_SECURE_KEY_HERE"
app.config["SONGS_PATH"] = "static/music/"

db = DAL("sqlite://data.db")
db.define_table("songs", Field("name"), Field("video_id"))


@app.route("/")
def index():
    """ Renders viewport for main player home page. """
    return render_template("index.html", songs_path=app.config["SONGS_PATH"], songs=get_songs())


@app.route("/add", methods=["GET", "POST"])
def add():
    """ Renders viewport for download page. """
    if request.method == "GET":
        return render_template("add.html", space=get_free_space())

    elif request.method == "POST":
        results = download(request.form["link"])

        if results[0] == True:
            add_song_to_database(results[1], results[2], results[3])
            return redirect("/")

        elif results[0] == False:
            # TODO: Add error message flash here.
            return(str(results[1]))


@app.route("/manage")
def manage():
    """ Renders viewport for song management. """
    return render_template("manage.html", songs=get_songs())


@app.route("/remove/<string:video_id>")
def remove(video_id):
    """ 
    Endpoint to receive song removal requests on.
  
    Parameters: 
    video_id (str): ID of song to be removed
  
    Returns: 
    str+response: HTTP 200 if the song was successfully removed 
    str+response: HTTP 500 if an error occurred while removing the song
    """
    results = remove_song(video_id)
    if results:
        return "Song successfully removed", 200
    else:
        return "Failed to remove song", 500


@app.route("/rename/<string:video_id>", methods=["POST"])
def rename(video_id):
    """ 
    Endpoint to receive song rename requests on.
  
    Parameters: 
    video_id (str): ID of song to be removed
  
    Returns: 
    str+response: HTTP 200 if the song was successfully removed 
    str+response: HTTP 500 if an error occurred while removing the song
    """
    name = request.form.get('name')
    results = rename_song(video_id, name)
    if results:
        return "Song successfully renamed to: " + name, 200
    else:
        return "Failed to rename song", 500


def download(link):
    """ 
    Downloads YouTube video, saves as audio file, and adds record to DB.
  
    Parameters: 
    link (str): URL of YouTube video to download
  
    Returns: 
    tuple: True, video title, song file system path, and video ID on success. 
    tuple: False, error string on failed download.
    """
    options = {
        'format': 'bestaudio/best',
        'outtmpl': app.config["SONGS_PATH"] + "%(id)s.mp3",
        'nocheckcertificate': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    }

    # Extracts info from video URL to dictionary and downloads video.
    with youtube_dl.YoutubeDL(options) as ydl:
        try:
            video_info = ydl.extract_info(link) 
        except Exception as error:
            return (False, str(error))

        # Returns True with video title, file system location, and video ID on success.
        return (True, video_info["title"], app.config["SONGS_PATH"] + video_info["id"] + ".mp3", video_info["id"])


def add_song_to_database(name, path, video_id):
    """ Saves song metadata to the database. """
    db.songs.insert(name=name, 
                    path=path, 
                    video_id=video_id)
    db.commit()


def get_songs():
    """ Converts songs row data into video_id: video_name dictionary and returns it. """
    rows = db().select(db.songs.ALL)
    songs = {}
    for row in rows:
        songs.update({row["video_id"]: row["name"]})
    return songs


def rename_song(video_id, name):
    """ 
    Attempts to rename song in database.

    Parameters: 
    video_id (str): ID of song stored in database
    name     (str): new name to be stored in database
  
    Returns: 
    bool: True if song was successfully renamed
    bool: False if an error occurred while renaming the song
    """
    results = db(db.songs.video_id == video_id)
    if results:
        db(db.songs.video_id == video_id).update(name=name)
        db.commit()
        return True
    return False


def remove_song(video_id):
    """ 
    Attempts to remove song from file system and database.

    Parameters: 
    video_id (str): ID of song stored in database
  
    Returns: 
    bool: True if song was successfully removed
    bool: False if an error occurred while removing the song
    """
    if does_song_exist(video_id):  # In case the file gets deleted but the DB entry remains.
        os.remove(app.config["SONGS_PATH"] + video_id + ".mp3")
    
    results = db(db.songs.video_id == video_id).delete()
    if results:
        db.commit()
        return True
    return False


def does_song_exist(video_id):
    """ 
    Checks if song exists on the file system.

    Parameters: 
    video_id (str): ID of song stored in database
  
    Returns: 
    bool: True if song was found
    bool: False if the song was not found
    """
    return True if os.path.exists(app.config["SONGS_PATH"] + video_id + ".mp3") else False


def get_free_space():
    """ Returns the amount of free space on the drive as a float rounded 1 place. """
    return round(shutil.disk_usage("/")[2] / (1024.0 ** 3), 1)


if __name__ == "__main__":
    app.run(debug=True)
