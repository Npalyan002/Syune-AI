"""Local bounded media inspection with no semantic interpretation."""
from io import BytesIO
from pathlib import Path
import struct,wave
from .errors import PerceptionError,PerceptionErrorCode
from .model import MediaMetadata,PerceptionLimits,SourceKind

FORMATS={".png":(SourceKind.IMAGE,"image/png"),".jpg":(SourceKind.IMAGE,"image/jpeg"),".jpeg":(SourceKind.IMAGE,"image/jpeg"),".webp":(SourceKind.IMAGE,"image/webp"),".wav":(SourceKind.AUDIO,"audio/wav"),".mp3":(SourceKind.AUDIO,"audio/mpeg"),".m4a":(SourceKind.AUDIO,"audio/mp4"),".flac":(SourceKind.AUDIO,"audio/flac"),".mp4":(SourceKind.VIDEO,"video/mp4"),".mov":(SourceKind.VIDEO,"video/quicktime"),".mkv":(SourceKind.VIDEO,"video/x-matroska"),".webm":(SourceKind.VIDEO,"video/webm")}
class MediaInspector:
    def inspect(self,path:Path,data:bytes,limits:PerceptionLimits=PerceptionLimits()):
        if len(data)>limits.max_source_bytes:raise PerceptionError(PerceptionErrorCode.MEDIA_TOO_LARGE,"source byte limit exceeded")
        definition=FORMATS.get(path.suffix.lower())
        if not definition:raise PerceptionError(PerceptionErrorCode.UNSUPPORTED_MEDIA,"unsupported media")
        kind,mime=definition;width=height=duration=rate=channels=None
        try:
            if path.suffix.lower()==".png":
                if len(data)<24 or data[:8]!=b"\x89PNG\r\n\x1a\n":raise ValueError
                width,height=struct.unpack(">II",data[16:24])
            elif path.suffix.lower() in (".jpg",".jpeg"):
                width,height=self._jpeg(data)
            elif path.suffix.lower()==".webp":
                if len(data)<16 or data[:4]!=b"RIFF" or data[8:12]!=b"WEBP":raise ValueError
            elif path.suffix.lower()==".wav":
                with wave.open(BytesIO(data),"rb") as item:
                    rate=item.getframerate();channels=item.getnchannels();duration=round(item.getnframes()*1000/rate)
            elif path.suffix.lower() in (".mp4",".mov",".m4a"):
                if len(data)<12 or data[4:8]!=b"ftyp":raise ValueError
            elif path.suffix.lower() in (".mkv",".webm"):
                if not data.startswith(b"\x1aE\xdf\xa3"):raise ValueError
            elif path.suffix.lower()==".flac":
                if not data.startswith(b"fLaC"):raise ValueError
            elif path.suffix.lower()==".mp3":
                if not (data.startswith(b"ID3") or data[:2] in (b"\xff\xfb",b"\xff\xf3",b"\xff\xf2")):raise ValueError
        except (ValueError,wave.Error,EOFError):raise PerceptionError(PerceptionErrorCode.MEDIA_CORRUPT,"invalid media container")
        if width and width*height>limits.max_image_pixels:raise PerceptionError(PerceptionErrorCode.PIXEL_LIMIT_EXCEEDED,"image pixel limit exceeded")
        if duration and kind is SourceKind.AUDIO and duration>limits.max_audio_duration_ms:raise PerceptionError(PerceptionErrorCode.DURATION_LIMIT_EXCEEDED,"audio duration limit exceeded")
        return MediaMetadata(kind,mime,len(data),width,height,duration,rate,channels)
    def _jpeg(self,data):
        if not data.startswith(b"\xff\xd8"):raise ValueError
        i=2
        while i+9<len(data):
            if data[i]!=255:i+=1;continue
            marker=data[i+1];length=int.from_bytes(data[i+2:i+4],"big")
            if marker in range(0xC0,0xC4):return int.from_bytes(data[i+7:i+9],"big"),int.from_bytes(data[i+5:i+7],"big")
            i+=2+length
        raise ValueError
