const API_URL = "http://localhost:8000/query";

const qInput = document.getElementById("queryInput");
const askBtn = document.getElementById("askBtn");
const results = document.getElementById("results");
const answerEl = document.getElementById("answer");
const metaEl = document.getElementById("meta");
const debugEl = document.getElementById("debug");
const debugPre = document.getElementById("debugPre");
const historyList = document.getElementById("historyList");
const debugToggle = document.getElementById("debugToggle");
const providerSelect = document.getElementById("providerSelect");
const modelInput = document.getElementById("modelInput");
const clearBtn = document.getElementById("clearBtn");

const MAX_HIST = 30;

// history persisted in localStorage
let history = [];
try{ history = JSON.parse(localStorage.getItem('vl_history')||'[]'); }catch(e){ history = []; }

function showLoading() {
  answerEl.textContent = "Thinking...";
  results.classList.remove("hidden");
}

function showError(err){
  answerEl.textContent = `Error: ${err}`;
  metaEl.textContent = "";
  debugPre.textContent = "";
  debugEl.style.display = "none";
  results.classList.remove("hidden");
}

function renderHistory(){
  historyList.innerHTML = "";
  history.slice().reverse().forEach((h)=>{
    const li = document.createElement('li');
    li.textContent = `${new Date(h.ts||Date.now()).toLocaleTimeString()} — ${h.query}`;
    li.onclick = ()=>{
      qInput.value = h.query;
      answerEl.textContent = h.answer;
      metaEl.textContent = `Path: ${ (h.path||[]).join(' > ') }`;
      results.classList.remove('hidden');
    }
    historyList.appendChild(li);
  });
}

askBtn.addEventListener('click', async () => {
  const query = qInput.value.trim();
  if(!query) return;
  showLoading();

  const body = { query, provider: providerSelect.value };
  if(modelInput.value.trim()) body.model = modelInput.value.trim();
  const url = debugToggle.checked ? `${API_URL}/debug` : API_URL;

  const start = Date.now();
  try{
    const res = await fetch(url, {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body),
    });
    if(!res.ok){
      const txt = await res.text().catch(()=>res.statusText);
      throw new Error(`${res.status} ${res.statusText} - ${txt}`);
    }
    const data = await res.json();
    const took = Date.now() - start;

    answerEl.textContent = data.answer || '(no answer)';
    metaEl.textContent = `Path: ${ (data.path||[]).join(' > ') } · Confidence: ${ (data.confidence||0).toFixed(2) } · ${took}ms`;

    if(debugToggle.checked){
      debugPre.textContent = JSON.stringify(data, null, 2);
      debugEl.style.display = 'block';
    } else {
      debugPre.textContent = '';
      debugEl.style.display = 'none';
    }

    history.push({ query, answer: data.answer||'', path: data.path||[], ts: Date.now() });
    if(history.length>MAX_HIST) history.shift();
    localStorage.setItem('vl_history', JSON.stringify(history));
    renderHistory();
  }catch(e){
    showError(e.message);
  }
});

// Allow Enter to submit when Ctrl/Cmd pressed
qInput.addEventListener('keydown', (ev)=>{
  if((ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey))){
    askBtn.click();
  }
});

// Initial render
renderHistory();

clearBtn.addEventListener('click', ()=>{
  qInput.value = '';
  answerEl.textContent = '';
  metaEl.textContent = '';
  debugPre.textContent = '';
  results.classList.add('hidden');
});
