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

let history = [];

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
    li.textContent = h.query;
    li.onclick = ()=>{ qInput.value = h.query; answerEl.textContent = h.answer; results.classList.remove('hidden'); }
    historyList.appendChild(li);
  });
}

askBtn.addEventListener('click', async () => {
  const query = qInput.value.trim();
  if(!query) return;
  showLoading();

  try{
    const body = { query };
    const res = await fetch(API_URL, {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body)
    });
    if(!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const data = await res.json();

    answerEl.textContent = data.answer || '(no answer)';
    metaEl.textContent = `Path: ${ (data.path||[]).join(' > ') } · Confidence: ${ (data.confidence||0).toFixed(2) }`;

    if(debugToggle.checked && data.traversal_path){
      debugPre.textContent = JSON.stringify(data, null, 2);
      debugEl.style.display = 'block';
    } else {
      debugPre.textContent = '';
      debugEl.style.display = 'none';
    }

    history.push({ query, answer: data.answer||'' });
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
