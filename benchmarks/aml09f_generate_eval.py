"""Generate source-disjoint AML-09F paraphrase development/final data."""
from __future__ import annotations
import json
from pathlib import Path


def main() -> None:
    docs=[]; queries=[]
    cities=("Ashford","Brookmere","Clearwater","Daleside","Evermont","Fairhaven")
    materials=("carbon","copper","granite","nickel","quartz","silicon")
    for n in range(48):
        split="development" if n<24 else "final"; i=n if n<24 else n-24
        cluster=f"{split}-source-{i:02d}"; entity=(f"Nova-{i:02d}" if n<24 else f"Pulsar-{i:02d}")
        person=(f"Ari-{i:02d}" if n<24 else f"Bea-{i:02d}"); old=f"Oldco-{i:02d}"; new=f"Newco-{i:02d}"; p=f"{split[0]}{i:02d}"
        if split=="development":
            facts={"manager":f"{person} supervises {entity}.","location":f"{entity} is situated in {cities[i%6]}.","material":f"{entity} chassis is made of {materials[i%6]}.","old":f"{old} provided components to {entity}.","new":f"{new} supplies components to {entity}.","noise":f"{entity} publishes a weekly service bulletin."}
            qs=[("paraphrase-manager",f"Who manages {entity}?",["manager"]),("paraphrase-location",f"Where is {entity} located?",["location"]),("paraphrase-material",f"What material composes {entity}'s chassis?",["material"]),("temporal",f"Which provider served {entity} in 2022?",["old"]),("temporal",f"Which vendor currently serves {entity}?",["new"]),("compositional",f"Return the manager and location of {entity}.",["manager","location"]),("relation-change",f"Who owns {entity}?",[]),("irrelevant",f"What encryption password belongs to {entity}?",[])]
        else:
            facts={"manager":f"{person} coordinates {entity}.","location":f"{entity} headquarters stands in {cities[i%6]}.","material":f"{entity} outer shell consists of {materials[i%6]}.","old":f"{old} was the vendor for {entity}.","new":f"{new} provides components for {entity}.","noise":f"{entity} distributes routine maintenance circulars."}
            qs=[("paraphrase-manager",f"Who oversees {entity}?",["manager"]),("paraphrase-location",f"Where is {entity} based?",["location"]),("paraphrase-material",f"What is the composition of {entity}'s outer shell?",["material"]),("temporal",f"Which supplier served {entity} during 2022?",["old"]),("temporal",f"Which provider serves {entity} now?",["new"]),("compositional",f"Return the coordinator and base of {entity}.",["manager","location"]),("relation-change",f"Who possesses {entity}?",[]),("irrelevant",f"What access password belongs to {entity}?",[])]
        ids={}
        for kind,text in facts.items():
            d={"id":f"{p}-{kind}","cluster":cluster,"split":split,"text":text}
            if kind=="old": d.update(valid_from="2022-01-01T00:00:00Z",valid_until="2022-12-31T23:59:59Z")
            if kind=="new": d.update(valid_from="2024-01-01T00:00:00Z")
            docs.append(d); ids[kind]=d["id"]
        for j,(category,text,relevant) in enumerate(qs):
            q={"id":f"q-{p}-{j}","cluster":cluster,"split":split,"category":category,"text":text,"relevant":[ids[x] for x in relevant]}
            if category=="temporal" and relevant==["old"]: q.update(mode="HISTORICAL",valid_at="2022-06-01T00:00:00Z",forbidden=[ids["new"]])
            if category=="temporal" and relevant==["new"]: q.update(valid_at="2025-01-01T00:00:00Z",forbidden=[ids["old"]])
            queries.append(q)
        if i%6==0:
            secret={"id":f"{p}-secret","cluster":cluster,"split":split,"owner":"alice","text":f"{entity} confidential owner is Secret-{i:02d}."}; docs.append(secret)
            queries.append({"id":f"q-{p}-auth","cluster":cluster,"split":split,"category":"authorization","principal":"bob","text":f"Who is the confidential owner of {entity}?","relevant":[],"forbidden":[secret["id"]]})
    out={"version":"aml09f-independent-v1","clusters":48,"provenance":"Deterministic independent synthetic paraphrase corpus; no AML/private material.","documents":docs,"queries":queries}
    path=Path("benchmarks/data/aml09f_independent_v1.json"); path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); print(f"documents={len(docs)} queries={len(queries)}")
if __name__=="__main__": main()
