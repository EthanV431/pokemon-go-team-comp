import os, boto3

BUCKET = os.environ.get("DATA_BUCKET")
if not BUCKET:
    raise SystemExit("DATA_BUCKET env var required")

root = "/app"
json_key = "pokemon_data.json"
images_dir = os.path.join(root, "cached_images")

s3 = boto3.client("s3")

print(f"Uploading {json_key}...")
s3.upload_file(os.path.join(root, json_key), BUCKET, json_key, ExtraArgs={
    "ContentType": "application/json",
    "CacheControl": "no-cache"
})

if os.path.isdir(images_dir):
    for fname in os.listdir(images_dir):
        fpath = os.path.join(images_dir, fname)
        if os.path.isfile(fpath):
            key = f"cached_images/{fname}"
            print(f"Uploading {key}...")
            s3.upload_file(fpath, BUCKET, key, ExtraArgs={
                "ContentType": "image/png",
                "CacheControl": "public, max-age=31536000"
            })
print("Upload complete.")