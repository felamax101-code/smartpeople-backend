    
import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

def upload_verification_document(file, folder="verification/documents"):
    # Save locally for now
    path = f"{folder}/{file.name}"
    saved_path = default_storage.save(path, file)
    url = default_storage.url(saved_path)
    return url

def upload_selfie(file, folder="verification/selfies"):
    path = f"{folder}/{file.name}"
    saved_path = default_storage.save(path, file)
    url = default_storage.url(saved_path)
    
    return url