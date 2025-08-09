import json, os, boto3
from urllib.parse import unquote

s3 = boto3.client("s3")
BUCKET = os.environ["DATA_BUCKET"]

def _load_data():
    obj = s3.get_object(Bucket=BUCKET, Key="pokemon_data.json")
    return json.loads(obj["Body"].read().decode("utf-8"))

def _resp(code, body=None, headers=None):
    h = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
    if headers: h.update(headers)
    return {"statusCode": code, "headers": h, "body": "" if body is None else (json.dumps(body) if isinstance(body, (dict, list)) else body)}

def handler(event, _ctx):
    path = (event.get("rawPath") or event.get("path") or "").rstrip("/")
    if path.startswith("/api/images/"):
        filename = unquote(path.split("/api/images/", 1)[1])
        url = f"https://{BUCKET}.s3.amazonaws.com/cached_images/{filename}"
        return _resp(302, "", {"Location": url})
    if path in ("/api/giovanniTeam","/api/arloTeam","/api/cliffTeam","/api/sierraTeam"):
        boss = path.replace("/api/","").replace("Team","")
        data = _load_data()
        return _resp(200, data.get(boss, {}))
    if path == "/api/status":
        data = _load_data()
        return _resp(200, {k: v.get("last_updated","") for k,v in data.items() if isinstance(v, dict)})
    return _resp(404, {"message":"Not found"})