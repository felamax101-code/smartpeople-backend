# import cloudinary.uploader

# def upload_image(file, folder="post"):
#     result = cloudinary.uploader.upload(
#         file,
#         folder=folder,
#         quality="auto",
#         fetch_format="auto"
#     )
#     return result["secure_url"]

# def upload_video(file, folder="post/videos"):
#     result = cloudinary.uploader.upload(
#         file,
#         resource_type="video",
#         folder=folder
#     )
#     return result["secure_url"]
    
    
    
    
import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

def upload_image(file, folder="post/images"):
    # Save locally for now
    path = f"{folder}/{file.name}"
    saved_path = default_storage.save(path, file)
    url = default_storage.url(saved_path)
    return url

def upload_video(file, folder="post/videos"):
    path = f"{folder}/{file.name}"
    saved_path = default_storage.save(path, file)
    url = default_storage.url(saved_path)
    
    return url
    
    