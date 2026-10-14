import mutagen
def get_duration(fileobj):
    audio = mutagen.File(fileobj)
    if audio is None or audio.info is None:
        raise ValueError("Not a valid audio file")
    return audio.info.length