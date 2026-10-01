from pathlib import Path
import struct,wave
from syune.core import SourceId,SourceVersionId
from syune.perception import MediaInspector,PerceptionError,PerceptionErrorCode,PerceptionLimits,SourceKind

def png(width=3,height=2):return b"\x89PNG\r\n\x1a\n"+b"\0"*8+struct.pack(">II",width,height)+b"fixture"
def wav_bytes(path):
    with wave.open(str(path),"wb") as item:item.setnchannels(1);item.setsampwidth(2);item.setframerate(8000);item.writeframes(b"\0\0"*800)
    return path.read_bytes()
def test_inspection_types_limits_and_corruption(tmp_path):
    inspector=MediaInspector();image=inspector.inspect(Path("x.png"),png())
    assert image.kind is SourceKind.IMAGE and (image.width,image.height)==(3,2)
    audio_path=tmp_path/"x.wav";audio=inspector.inspect(audio_path,wav_bytes(audio_path));assert audio.duration_ms==100
    try:inspector.inspect(Path("bad.png"),b"bad")
    except PerceptionError as error:assert error.code is PerceptionErrorCode.MEDIA_CORRUPT
    else:raise AssertionError("corrupt image accepted")
    try:inspector.inspect(Path("x.png"),png(),PerceptionLimits(max_image_pixels=1))
    except PerceptionError as error:assert error.code is PerceptionErrorCode.PIXEL_LIMIT_EXCEEDED
    else:raise AssertionError("pixel limit bypassed")
