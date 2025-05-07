console.log("✅ script.js 加载成功");

async function sendMessage() {
  const inputEl = document.getElementById("input");
  const respEl  = document.getElementById("response");
  const btn     = document.getElementById("sendBtn");
  const text    = inputEl.value.trim();

  if (!text) {
    respEl.textContent = "请输入内容再发送。";
    return;
  }

  btn.disabled   = true;
  respEl.textContent = "处理中…";

  try {
    const res = await fetch("/process", {
      method: "POST",
      headers: { "Content-Type":"application/json" },
      body: JSON.stringify({ text })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => res.statusText);
      throw err;
    }
    const data = await res.json();
    respEl.textContent =
      "【分析结果】\n" +
      "实体： "    + JSON.stringify(data.entities, null, 2) + "\n" +
      "情感： "    + data.sentiment + "\n" +
      "关键词： " + JSON.stringify(data.keywords, null, 2) +
      "\n\n【模型回复】\n" + data.reply;
  } catch (err) {
    console.error(err);
    respEl.textContent = "出错了： " + JSON.stringify(err);
  } finally {
    btn.disabled = false;
  }
}

document.getElementById("sendBtn").addEventListener("click", sendMessage);
document.getElementById("input").addEventListener("keydown", e => {
  if (e.key==="Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});
