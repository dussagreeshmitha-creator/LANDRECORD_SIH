import json
from pathlib import Path
from urllib.request import Request, urlopen

boundary = "----LandSecureBoundary"
sample = Path("data/sample-land-record.txt").read_bytes()
fields = {
    "owner_name": "R. Selvam",
    "survey_number": "142/3B",
    "patta_number": "TN-CHN-88421",
    "land_area": "1.24",
    "land_classification": "Dry agricultural",
    "record_date": "04-09-2026",
    "north": "Odai",
    "south": "Cart track",
    "east": "Survey 142/4",
    "west": "Survey 142/2",
    "lat": "13.1436",
    "lng": "79.9082",
}
parts = []
for key, value in fields.items():
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode()
    )
parts.append(
    f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"sample-land-record.txt\"\r\nContent-Type: text/plain\r\n\r\n".encode()
    + sample
    + b"\r\n"
)
parts.append(f"--{boundary}--\r\n".encode())
req = Request(
    "http://127.0.0.1:8000/api/records",
    data=b"".join(parts),
    method="POST",
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
)
res = json.loads(urlopen(req).read())
print(res["validation"]["overall"], res["validation"]["mismatch_count"])
print(json.dumps(res["extracted"], indent=2))
