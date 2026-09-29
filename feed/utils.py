
import os

def save_temp_upload(uploaded_file, identifier):
    ext = os.path.splitext(uploaded_file.name)[1]
    tmp_dir = "/tmp/post_uploads"
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, f"{identifier}_raw{ext}")
    with open(tmp_path, "wb+") as dest:
        for chunk in uploaded_file.chunks():
            dest.write(chunk)
    return tmp_path
