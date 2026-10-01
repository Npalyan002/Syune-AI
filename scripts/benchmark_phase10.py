"""Deterministic local multimodal Study benchmark; no providers or network."""
from io import BytesIO
import json,math,statistics,struct,tempfile,wave
from pathlib import Path
from time import perf_counter
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject,DictionaryObject,NameObject
from syune.memory import InMemoryReferenceRepository
from syune.study import SqliteStudyRegistry,StudyService

def pdf_bytes(text):
    writer=PdfWriter();page=writer.add_blank_page(width=300,height=300);font=DictionaryObject({NameObject("/Type"):NameObject("/Font"),NameObject("/Subtype"):NameObject("/Type1"),NameObject("/BaseFont"):NameObject("/Helvetica")});page[NameObject("/Resources")]=DictionaryObject({NameObject("/Font"):DictionaryObject({NameObject("/F1"):writer._add_object(font)})});stream=DecodedStreamObject();stream.set_data(f"BT /F1 12 Tf 20 250 Td ({text}) Tj ET".encode());page[NameObject("/Contents")]=writer._add_object(stream);output=BytesIO();writer.write(output);return output.getvalue()
def fixtures(root):
    values={"text.txt":b"phase ten benchmark text","document.pdf":pdf_bytes("phase ten pdf"),"image.png":b"\x89PNG\r\n\x1a\n"+b"\0"*8+struct.pack(">II",32,32)+b"fixture","video.mp4":b"\0\0\0\x18ftypisomsynthetic"}
    audio=root/"audio.wav"
    with wave.open(str(audio),"wb") as item:item.setnchannels(1);item.setsampwidth(2);item.setframerate(8000);item.writeframes(b"\0\0"*8000)
    values["audio.wav"]=audio.read_bytes();return values
def percentile(values,q):return sorted(values)[min(len(values)-1,math.ceil(len(values)*q)-1)]
def main():
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);values=fixtures(root);results={}
        for name,data in values.items():
            times=[]
            for n in range(5):
                case=root/f"case-{name}-{n}";case.mkdir();source=case/name;source.write_bytes(data);memory=InMemoryReferenceRepository()
                with SqliteStudyRegistry(case/"study.sqlite3") as registry:
                    tick=perf_counter();result=StudyService(registry,memory,case).study(source);times.append((perf_counter()-tick)*1000)
                    segments=result.status.blocks_total
            results[name]={"bytes":len(data),"segments":segments,"p50_ms":statistics.median(times),"p95_ms":percentile(times,.95)}
        print(json.dumps(results,indent=2))
if __name__=="__main__":main()
