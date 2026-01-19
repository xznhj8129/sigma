import os, json
from pathlib import Path
from aiohttp import web

try:
    from aiohttp_middlewares import cors_middleware
    CORS_MIDDLEWARE = [cors_middleware(allow_all=True)]
except ImportError:
    CORS_MIDDLEWARE = []

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack  # type: ignore
    import cv2  # type: ignore
    import av  # type: ignore
    MEDIA_AVAILABLE = True
except ImportError:
    MEDIA_AVAILABLE = False

ROOT = Path(__file__).resolve().parent
SOURCES_PATH = ROOT / "sources.json"
with SOURCES_PATH.open("r", encoding="utf-8") as f:
    obs_sources = json.load(f)

FILES_ROOT = Path(obs_sources["files"]["path"]).resolve()
VIDEO_DIR = FILES_ROOT / "video"
IMAGE_DIR = FILES_ROOT / "image"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
mediafiles = os.listdir(VIDEO_DIR) if MEDIA_AVAILABLE else []

def resolve_path(name):
    if name in obs_sources:
        return obs_sources[name]["video_addr"]
    if name in mediafiles:
        return os.path.join(VIDEO_DIR, name)
    return None

if MEDIA_AVAILABLE:
    class VideoTrack(VideoStreamTrack):
        def __init__(self, path):
            super().__init__()
            self.cap = cv2.VideoCapture(path)

        async def recv(self):
            pts, time_base = await self.next_timestamp()
            ret, frame = self.cap.read()
            if not ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
            video_frame = av.VideoFrame.from_ndarray(frame, format="bgr24")
            video_frame.pts = pts
            video_frame.time_base = time_base
            return video_frame

async def offer(request):
    if not MEDIA_AVAILABLE:
        return web.Response(status=500, text="Media dependencies (cv2/av) not installed")
    name = request.query.get("path")
    source = resolve_path(name)
    if not source:
        return web.Response(status=404, text="Unknown source")

    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    pc = RTCPeerConnection()

    @pc.on("iceconnectionstatechange")
    async def on_state():
        if pc.iceConnectionState == "failed":
            await pc.close()

    await pc.setRemoteDescription(offer)
    pc.addTrack(VideoTrack(source))
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(content_type="application/json", text=json.dumps({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    }))

def create_aiohttp_app():
    app = web.Application(middlewares=CORS_MIDDLEWARE)
    if MEDIA_AVAILABLE:
        app.router.add_post("/offer", offer)
    else:
        async def unavailable(request):
            return web.Response(status=501, text="Media dependencies (aiortc/cv2/av) not installed")
        app.router.add_post("/offer", unavailable)
    return app
