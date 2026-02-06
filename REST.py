from flask import Flask, request, jsonify
from influxdb_client import InfluxDBClient, Point, WritePrecision
from dateutil import parser as dtparser
import os

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "home")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "health")

app = Flask(__name__)

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api()

@app.post("/data")
def ingest():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    payload = request.get_json()
    #print(f"Received payload: {payload}")

    # Expected shape: {"data":{"metrics":[{"name","units","data":[{"date","qty","source"}, ...]}]}}
    metrics = (((payload or {}).get("data") or {}).get("metrics")) or []
    points = []
    dropped = 0

    for m in metrics:
        metric_name = m.get("name")
        unit = m.get("units")
        entries = m.get("data") or []

        for e in entries:
            try:
                ts = dtparser.parse(e["date"])      # timezone aware
                value = float(e["qty"])
                source = e.get("source", "unknown")

                p = (
                    Point("healthkit")
                    .tag("metric", metric_name or "unknown")
                    .tag("source", source)
                    .tag("unit", unit or "unknown")
                    .field("value", value)
                    .time(ts, WritePrecision.NS)
                )
                points.append(p)
            except Exception:
                dropped += 1

    if points:
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
        print(f"Wrote {len(points)} points, dropped {dropped} points.")

    return jsonify({"ok": True, "written": len(points), "dropped": dropped}), 200


@app.get("/data")
def healthcheck():
    return jsonify({"ok": True}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5055, debug=True)