from http.server import BaseHTTPRequestHandler
import json
import subprocess
import re


def extract_info(url):
    """Use yt-dlp to extract video/image info from URL."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--no-download", "--dump-json", url],
            capture_output=True, text=True, timeout=25
        )
        if result.returncode != 0:
            return {"error": result.stderr.strip() or "解析失败"}

        data = json.loads(result.stdout)
        media_type = "video"
        urls = []

        # Check if it's a video
        if data.get("url"):
            urls.append({
                "url": data["url"],
                "type": "video",
                "title": data.get("title", ""),
                "thumbnail": data.get("thumbnail", ""),
            })
        elif data.get("formats"):
            # Pick best mp4 format
            mp4_formats = [f for f in data["formats"] if f.get("ext") == "mp4" and f.get("url")]
            if mp4_formats:
                best = max(mp4_formats, key=lambda f: (f.get("height") or 0))
                urls.append({
                    "url": best["url"],
                    "type": "video",
                    "title": data.get("title", ""),
                    "thumbnail": data.get("thumbnail", ""),
                })

        if not urls:
            return {"error": "未找到可下载的媒体"}

        return {"media": urls, "title": data.get("title", "")}

    except subprocess.TimeoutExpired:
        return {"error": "解析超时，请稍后重试"}
    except Exception as e:
        return {"error": str(e)}


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors()
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
            url = data.get("url", "").strip()
        except Exception:
            self._respond(400, {"error": "无效的请求"})
            return

        if not url:
            self._respond(400, {"error": "请提供链接"})
            return

        # Basic URL validation
        if not re.match(r'https?://', url):
            url = "https://" + url

        result = extract_info(url)
        if "error" in result:
            self._respond(400, result)
        else:
            self._respond(200, result)

    def _respond(self, status, data):
        self.send_response(status)
        self._set_cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _set_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
