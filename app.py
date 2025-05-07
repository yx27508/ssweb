from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uuid, json, re
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from openai import OpenAI

BASE_DIR  = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "database.json"
MODEL_DIR = BASE_DIR / "finetuned_model_fp16"
HOST = "0.0.0.0"
PORT = 5001

client = OpenAI(
    api_key="sk-your-api-key-here",  # ← 請填你自己的 API KEY
    base_url="https://api.deepseek.com"
)

tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
model = AutoModelForCausalLM.from_pretrained(str(MODEL_DIR), torch_dtype=torch.float16, device_map="auto")
local_pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

@app.get("/")
async def index():
    return FileResponse(BASE_DIR / "templates/index.html", media_type="text/html")

def load_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except:
            return []
    return []

def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

@app.post("/process")
async def process(request: Request):
    body = await request.json()
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="文本不能为空")

    prompt = (
        "请从下列文本中抽取所有“人/组织/事件”实体，并给出整体情感倾向（正向/中性/负向），再列出3-5个关键词，只输出纯 JSON。\n\n"
        f"文本：{text}"
    )
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是实体与情感分析专家，只输出 JSON。"},
            {"role": "user", "content": prompt}
        ],
        stream=False
    )
    raw = resp.choices[0].message.content
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    json_str = m.group(1).strip() if m else raw.strip()

    try:
        parsed = json.loads(json_str)
    except:
        return JSONResponse({"error": "解析 DeepSeek 返回失败", "raw": raw}, status_code=500)

    record = {
        "id": str(uuid.uuid4()),
        "text": text,
        "entities": parsed.get("entities", []),
        "sentiment": parsed.get("sentiment", ""),
        "keywords": parsed.get("keywords", [])
    }
    data = load_data()
    data.append(record)
    save_data(data)

    out = local_pipe(text, max_length=512, do_sample=True, top_p=0.9, temperature=0.8)
    reply = out[0]["generated_text"]

    return {
        **record,
        "reply": reply
    }
