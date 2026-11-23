#!/usr/bin/env python3
"""Evidence-first app research agent. Requires TAVILY_API_KEY and OPENAI_API_KEY."""
import argparse, csv, json, os, time
from datetime import datetime, timezone
from pathlib import Path
import requests
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
APPS = ROOT / "data" / "apps.csv"
OUT = ROOT / "data" / "research_results.json"

SCHEMA = {
  "type":"object",
  "properties":{
    "description":{"type":"string"},
    "auth_methods":{"type":"array","items":{"type":"string"}},
    "access_model":{"type":"string"},
    "api_surface":{"type":"string"},
    "mcp_status":{"type":"string"},
    "buildability":{"type":"string"},
    "blocker":{"type":"string"},
    "confidence":{"type":"string","enum":["High","Medium","Low","None"]},
    "research_status":{"type":"string","enum":["researched","needs_human_review","insufficient_evidence"]},
    "notes":{"type":"string"},
    "evidence_urls":{"type":"array","items":{"type":"string"}}
  },
  "required":["description","auth_methods","access_model","api_surface","mcp_status","buildability","blocker","confidence","research_status","notes","evidence_urls"],
  "additionalProperties":False
}

def search_web(query, api_key, max_results=6):
    response = requests.post(
        "https://api.tavily.com/search",
        json={"api_key":api_key,"query":query,"search_depth":"advanced",
              "max_results":max_results,"include_answer":False},
        timeout=45
    )
    response.raise_for_status()
    return response.json().get("results", [])

def research_one(app, tavily_key, client, model):
    hint = app["website_hint"]
    query = f'{app["app"]} official developer API documentation authentication OAuth API key MCP pricing access'
    results = search_web(query, tavily_key)
    compact = [{
        "title": r.get("title",""), "url": r.get("url",""),
        "content": (r.get("content","") or "")[:3500]
    } for r in results]
    prompt = f"""
Research this application for an AI-agent integration product-ops inventory.
App: {app['app']}
Category: {app['category']}
Official website/docs hint: {hint}

Use ONLY the supplied search evidence. Do not infer that an MCP exists merely because an API exists.
Distinguish: auth mechanism; whether credentials can be self-served or are gated; public REST/GraphQL breadth; first-party or community MCP; and practical buildability.
If pricing, free-tier eligibility, partner approval, or exact API breadth is not evidenced, say unknown / needs human review.
Prefer official vendor docs. Evidence URLs must be copied exactly from supplied results.
Do not invent endpoint counts, free plans, MCP servers, or access policies.
Search evidence:
{json.dumps(compact, ensure_ascii=False)}
"""
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type":"json_schema","json_schema":{"name":"app_research","strict":True,"schema":SCHEMA}},
        messages=[
            {"role":"system","content":"You are a cautious API documentation analyst. Evidence over completeness; uncertainty is acceptable."},
            {"role":"user","content":prompt}
        ]
    )
    data = json.loads(response.choices[0].message.content)
    # Guardrail: evidence URLs must come from search results.
    allowed = {r.get("url") for r in results if r.get("url")}
    data["evidence_urls"] = [u for u in data["evidence_urls"] if u in allowed]
    if not data["evidence_urls"]:
        data["research_status"] = "insufficient_evidence"
        data["confidence"] = "None"
    return data, compact

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL","gpt-4.1-mini"))
    args = parser.parse_args()
    tavily_key = os.getenv("TAVILY_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    if not tavily_key or not openai_key:
        raise SystemExit("Set TAVILY_API_KEY and OPENAI_API_KEY in your environment.")
    client = OpenAI(api_key=openai_key)
    with APPS.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    try:
        existing = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        existing = []
    by_num = {int(x["number"]): x for x in existing}
    for app in rows[:args.limit]:
        n = int(app["number"])
        print(f"[{n}/100] researching {app['app']} ...", flush=True)
        try:
            facts, search_results = research_one(app, tavily_key, client, args.model)
            by_num[n] = {
                **{k: (int(v) if k=="number" else v) for k,v in app.items()},
                **facts, "checked_at":datetime.now(timezone.utc).isoformat(),
                "evidence_titles":[r.get("title","") for r in search_results if r.get("url") in facts["evidence_urls"]]
            }
        except Exception as exc:
            prior = by_num.get(n, {})
            by_num[n] = {**prior, "number":n, "app":app["app"], "category":app["category"],
                         "research_status":"needs_human_review", "confidence":"None",
                         "notes":f"Agent error: {type(exc).__name__}: {exc}"}
            print(f"  ERROR: {exc}", flush=True)
        OUT.write_text(json.dumps([by_num[k] for k in sorted(by_num)], indent=2), encoding="utf-8")
        time.sleep(args.delay)
    print(f"Saved {len(by_num)} records to {OUT}")

if __name__ == "__main__":
    main()
