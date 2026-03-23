# SAPIENT — Claude Code Uygulama Planı (Gerçek Kod Analizi)
## Multi-Model Desteği & Yeni Deneyler

**Son güncelleme:** 23 Mart 2026  
**Kaynak:** `/sapient/` dizinindeki gerçek kod incelendi

---

## MİMARİ ANALİZ — MEVCUT KOD NASIL ÇALIŞIYOR

### Dosya Yapısı (doğrulanmış)

```
sapient/
├── config/
│   ├── personas.json          # 8 persona (P1–P8), θ_i tuple formatı
│   └── scenarios.json         # Scenario 1 + signal_state_rich + 3 stimulus variant
├── agents/
│   ├── __init__.py            # Export: get_persona_response, get_persona_followup, build_persona_system_prompt, run_afg_session, run_afg_experiment
│   ├── persona_agent.py       # Sync API çağrıları — anthropic.Anthropic kullanır
│   ├── moderator_agent.py     # Sync AFG session orchestrator — persona_agent'ı çağırır
│   └── parallel_runner.py     # Async API çağrıları — anthropic.AsyncAnthropic kullanır
├── metrics/
│   ├── __init__.py            # Export: tüm analysis fonksiyonları
│   └── analysis.py            # Theme stability, variance collapse, sentiment, credibility, persona consistency
├── experiments/
│   ├── __init__.py            # Boş
│   ├── exp1_afg_protocol.py   # anthropic.Anthropic(api_key=api_key) OLUŞTURUYOR
│   ├── exp2_signal_ab.py      # Aynı pattern
│   ├── exp3_multilingual.py   # TURKISH_PERSONAS, TURKISH_STIMULUS, TURKISH_PROBES tanımlı
│   └── exp4_temperature.py    # Aynı pattern
├── results/                   # Boş (deneyler çıktılarını buraya yazıyor)
├── run_fast.py                # ANA RUNNER — parallel_runner kullanır
├── run_all.py                 # Sıralı runner — moderator_agent kullanır
├── generate_tables.py         # JSON → LaTeX tablo
├── requirements.txt           # anthropic, numpy, pandas, sentence-transformers, scipy, sklearn, tqdm
├── run.txt                    # Çalıştırma notları
├── README.md
└── EXPERIMENT_PLAN.md
```

**NOT:** `.gitignore` dosyası YOK — oluşturulması gerekiyor.

### API Çağrı Zinciri (KRİTİK — İki Paralel Yol Var)

```
YOL 1 — SYNC (run_all.py → moderator_agent → persona_agent)
  exp1_afg_protocol.py:
    client = anthropic.Anthropic(api_key=api_key)     ← Client burada oluşturuluyor
    run_afg_experiment(client, personas, stimulus...)   ← Client parametre olarak geçiyor
      → moderator_agent.run_afg_session(client, ...)
        → persona_agent.get_persona_response(client, ...) 
          → client.messages.create(model=, system=, messages=, temperature=, max_tokens=800)
        → persona_agent.get_persona_followup(client, ...)
          → client.messages.create(model=, system=, messages=, temperature=, max_tokens=500)

YOL 2 — ASYNC (run_fast.py → parallel_runner) ← BU ANA YOL
  run_fast.py:
    api_key string olarak geçiyor (client DEĞİL)
    run_afg_experiment_parallel(api_key, personas, stimulus...)
      → parallel_runner._run_experiment_async(api_key, ...)
        client = anthropic.AsyncAnthropic(api_key=api_key)  ← Client BURADA oluşturuluyor
        → _run_session_async(client, ...)
          → _async_persona_call(client, ...) x 8 paralel
            → client.messages.create(model=, system=, messages=, temperature=, max_tokens=800)
          → _async_followup_call(client, ...) x 8 paralel
            → client.messages.create(model=, system=, messages=, temperature=, max_tokens=500)
```

### Prompt Yapısı (LLM-Agnostic — Değişmesine Gerek YOK)

`build_persona_system_prompt()` saf string döndürür — hiçbir SDK bağımlılığı yok. ✓  
User message template JSON structured output istiyor — her iki LLM'de çalışır. ✓  
JSON parsing logic markdown wrapping handle ediyor — her iki LLM'de benzer çıktı. ✓

### KRİTİK BULGU: Prompt Template İKİ YERDE DUPLICATE EDİLMİŞ

Aynı user message template hem `persona_agent.py` (satır 78–96) hem `parallel_runner.py` (satır 30–48) içinde var. Followup template da aynı şekilde duplicate. Bu, değişiklik yapılacaksa **İKİ DOSYADA BİRDEN** yapılması gerektiği anlamına geliyor.

### Token/Usage Tracking: YOK

Mevcut kodda `response.usage` hiçbir yerde erişilmiyor. Anthropic API'si `response.usage.input_tokens` ve `response.usage.output_tokens` döndürüyor ama bu veri hiç loglanmıyor. Bu, Hakem 2'nin R2-7 (runtime) eleştirisinin kökenindeki eksiklik.

---

## UYGULAMA PLANI — ADIM ADIM

### ADIM 1: `.gitignore` ve `.env` Altyapısı

**1a. `.gitignore` oluştur** (proje kökünde — `sapient/.gitignore`)

```gitignore
# API Keys
.env
*.env
!.env.example

# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/

# Results (büyük JSON dosyaları — isteğe bağlı)
# results/*.json

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
```

**1b. `.env.example` oluştur** (git'e commit edilir)

```bash
# API Keys — Bu dosyayı .env olarak kopyalayıp kendi key'lerinizi yazın
ANTHROPIC_API_KEY=your-anthropic-key-here
OPENAI_API_KEY=your-openai-key-here
```

**1c. `.env` oluştur** (git'e ASLA commit edilmez)

```bash
ANTHROPIC_API_KEY=sk-ant-api03-...gerçek key...
OPENAI_API_KEY=sk-proj-...gerçek key...
```

**1e. `SETUP_API_KEYS.md` oluştur** (git'e commit edilir — kullanıcı rehberi)

Bu dosya repo'yu clone eden birinin ilk bakacağı yer. İçeriği:

```markdown
# SAPIENT — API Key Kurulumu ve Desteklenen Modeller

## Hızlı Başlangıç

1. `.env.example` dosyasını `.env` olarak kopyalayın:
   ```bash
   cp .env.example .env
   ```

2. `.env` dosyasını açıp kendi API key'lerinizi yazın.

3. `.env` dosyası git tarafından takip EDİLMEZ (`.gitignore`'da).
   Key'leriniz asla repo'ya commit olmaz.

## Desteklenen LLM Backend'leri

| Model | Provider | `--model` Parametresi | API Key Env Variable |
|-------|----------|-----------------------|---------------------|
| Claude Sonnet 4 | Anthropic | `claude-sonnet-4-20250514` (varsayılan) | `ANTHROPIC_API_KEY` |
| GPT-4o | OpenAI | `gpt-4o` | `OPENAI_API_KEY` |
| GPT-4o (belirli versiyon) | OpenAI | `gpt-4o-2024-11-20` | `OPENAI_API_KEY` |
| GPT-4o Mini | OpenAI | `gpt-4o-mini` | `OPENAI_API_KEY` |

Yeni model eklemek için `agents/llm_client.py` dosyasındaki `PROVIDER_MAP` ve
`PRICING` sözlüklerine ilgili model string'ini ekleyin.

## API Key Nasıl Alınır

### Anthropic (Claude)
1. https://console.anthropic.com/ adresinden hesap oluşturun
2. API Keys bölümünden yeni key oluşturun
3. Key `sk-ant-` ile başlar

### OpenAI (GPT-4o)
1. https://platform.openai.com/ adresinden hesap oluşturun
2. API Keys bölümünden yeni key oluşturun
3. Key `sk-proj-` ile başlar

## Kullanım

```bash
# Varsayılan model (Claude Sonnet 4):
python run_fast.py --exp 1 --K 2

# GPT-4o ile:
python run_fast.py --exp 1 --K 2 --model gpt-4o

# Cross-model karşılaştırma (her iki key gerekli):
python run_fast.py --exp 7

# Maliyet tahmini:
python run_fast.py --estimate --model gpt-4o
```

## Tahmini API Maliyetleri

| Model | Input ($/M token) | Output ($/M token) | Tipik Tek Deney (~K=10) |
|-------|-------------------|--------------------|-----------------------|
| Claude Sonnet 4 | $3.00 | $15.00 | ~$3–5 |
| GPT-4o | $2.50 | $10.00 | ~$2–4 |
| GPT-4o Mini | $0.15 | $0.60 | ~$0.20 |

## Sorun Giderme

- **"ANTHROPIC_API_KEY not set"**: `.env` dosyası proje kökünde mi kontrol edin.
- **"Unknown model: ..."**: `agents/llm_client.py` dosyasındaki `PROVIDER_MAP`'e
  modeli ekleyin.
- **Rate limit hatası**: `run_fast.py`'deki `max_concurrent_runs` değerini
  düşürün (varsayılan: 4).
```

**1f. `config/models.json` oluştur** (desteklenen modeller — opsiyonel ama düzenli)

```json
{
  "supported_models": {
    "claude-sonnet-4-20250514": {
      "provider": "anthropic",
      "display_name": "Claude Sonnet 4",
      "pricing": {"input_per_M": 3.00, "output_per_M": 15.00},
      "max_tokens_default": 800,
      "notes": "Varsayılan model. Makaledeki Exp 1-4 bununla koşturuldu."
    },
    "gpt-4o": {
      "provider": "openai",
      "display_name": "GPT-4o",
      "pricing": {"input_per_M": 2.50, "output_per_M": 10.00},
      "max_tokens_default": 800,
      "notes": "Revision deneylerinde cross-model karşılaştırma için eklendi."
    },
    "gpt-4o-2024-11-20": {
      "provider": "openai",
      "display_name": "GPT-4o (Nov 2024)",
      "pricing": {"input_per_M": 2.50, "output_per_M": 10.00},
      "max_tokens_default": 800,
      "notes": "Belirli versiyon pin'i — tekrarlanabilirlik için."
    },
    "gpt-4o-mini": {
      "provider": "openai",
      "display_name": "GPT-4o Mini",
      "pricing": {"input_per_M": 0.15, "output_per_M": 0.60},
      "max_tokens_default": 800,
      "notes": "Düşük maliyetli test modeli."
    }
  },
  "default_model": "claude-sonnet-4-20250514",
  "env_variables": {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY"
  }
}
```

Bu config dosyasının kullanımı opsiyonel — `llm_client.py` bunu okuyabilir veya
kendi hardcode PROVIDER_MAP'ini kullanmaya devam edebilir. Avantajı: yeni model
eklemek için kod değiştirmek yerine JSON düzenlemek yeterli olur.

**1d. `config/env_loader.py` oluştur**

Bu dosya:
- `.env` dosyasını okur (varsa)
- Yoksa environment variable'dan alır
- Provider'a göre doğru key'i döndürür
- `python-dotenv` dependency'si gerektirmez (kendi basit parser'ı)

```python
"""API key yönetimi. .env dosyasından veya environment'tan yükler."""
import os
from pathlib import Path

def load_env():
    """Proje kökündeki .env dosyasını yükle."""
    # sapient/ dizininden bir üst dizine (.env orada) veya aynı dizine bak
    for candidate in [
        Path(__file__).parent.parent / ".env",   # sapient/.env
        Path(__file__).parent.parent.parent / ".env",  # üst dizin
    ]:
        if candidate.exists():
            with open(candidate) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        os.environ.setdefault(key.strip(), value.strip())
            return

def get_api_key(provider: str) -> str:
    """Provider'a göre API key döndür."""
    load_env()
    key_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
    }
    env_var = key_map.get(provider)
    if not env_var:
        raise ValueError(f"Bilinmeyen provider: {provider}")
    key = os.environ.get(env_var)
    if not key or key.startswith("your-"):
        raise EnvironmentError(
            f"{env_var} ayarlanmamış. .env dosyası oluşturun veya export edin.\n"
            f"Bkz: .env.example"
        )
    return key
```

**Doğrulama:** `python -c "from config.env_loader import get_api_key; print(get_api_key('anthropic')[:10])"` → key'in ilk 10 karakteri görünmeli.

---

### ADIM 2: `agents/llm_client.py` — Unified LLM Client

Bu dosya TÜM API çağrılarını merkeze alır. Hem sync hem async destekler.

```
GENEL YAPI:

PROVIDER_MAP = {
    "claude-sonnet-4-20250514": "anthropic",
    "gpt-4o": "openai",
    "gpt-4o-2024-11-20": "openai",
    "gpt-4o-mini": "openai",
    # Gerektiğinde buraya yeni modeller eklenir
}

class LLMResponse:
    content: str           # Model çıktısı (text)
    model: str             # Kullanılan model adı
    provider: str          # "anthropic" veya "openai"
    input_tokens: int      # Giriş token sayısı
    output_tokens: int     # Çıkış token sayısı
    latency_ms: float      # Süre (milisaniye)
    cost_usd: float        # Tahmini maliyet (property)

# Sync fonksiyon
def chat(system_prompt, user_message, model, temperature, max_tokens, api_key) -> LLMResponse

# Async fonksiyon (parallel_runner için)
async def achat(system_prompt, user_message, model, temperature, max_tokens, api_key) -> LLMResponse
```

**Implementasyon detayları:**

Sync `chat()`:
- `provider == "anthropic"` → `anthropic.Anthropic(api_key).messages.create(system=..., messages=[{role:user}])`
- `provider == "openai"` → `openai.OpenAI(api_key).chat.completions.create(messages=[{role:system}, {role:user}])`
- Fark: Anthropic `system` parametresini ayrı alır; OpenAI `messages` listesinde system role olarak geçirir.

Async `achat()`:
- `provider == "anthropic"` → `anthropic.AsyncAnthropic(api_key).messages.create(...)`
- `provider == "openai"` → `openai.AsyncOpenAI(api_key).chat.completions.create(...)`

Response mapping:
```
Anthropic:
  content  = response.content[0].text
  input    = response.usage.input_tokens
  output   = response.usage.output_tokens

OpenAI:
  content  = response.choices[0].message.content
  input    = response.usage.prompt_tokens
  output   = response.usage.completion_tokens
```

Followup çağrısı için multi-turn messages:
```
Anthropic:  system=system_prompt, messages=[{user:...}, {assistant:...}, {user:...}]
OpenAI:     messages=[{system:system_prompt}, {user:...}, {assistant:...}, {user:...}]
```

**Maliyet hesaplama (LLMResponse.cost_usd property):**
```python
PRICING = {  # (input_per_M_tokens, output_per_M_tokens)
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "gpt-4o":                   (2.50, 10.00),
    "gpt-4o-2024-11-20":        (2.50, 10.00),
    "gpt-4o-mini":              (0.15,  0.60),
}
```

**Doğrulama testi:**
```python
# Test 1: Sync — Anthropic
resp = chat("You are helpful.", "Say hello.", "claude-sonnet-4-20250514", 0.7, 100, anthropic_key)
assert resp.provider == "anthropic"
assert resp.input_tokens > 0

# Test 2: Sync — OpenAI
resp = chat("You are helpful.", "Say hello.", "gpt-4o", 0.7, 100, openai_key)
assert resp.provider == "openai"
assert resp.input_tokens > 0

# Test 3: Async — her ikisi
# asyncio.run() ile test et
```

---

### ADIM 3: `agents/usage_tracker.py` — Token/Maliyet Loglama

Thread-safe bir tracker. Her API çağrısından sonra `record()` çağrılır.

```python
"""Deney boyunca API kullanımını takip eder."""
import threading

class UsageTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self.calls = []

    def record(self, response):  # LLMResponse alır
        with self._lock:
            self.calls.append({
                "model": response.model,
                "provider": response.provider,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "latency_ms": response.latency_ms,
                "cost_usd": response.cost_usd,
            })

    def summary(self) -> dict:
        if not self.calls:
            return {}
        return {
            "total_calls": len(self.calls),
            "total_input_tokens": sum(c["input_tokens"] for c in self.calls),
            "total_output_tokens": sum(c["output_tokens"] for c in self.calls),
            "total_cost_usd": round(sum(c["cost_usd"] for c in self.calls), 4),
            "mean_latency_ms": round(sum(c["latency_ms"] for c in self.calls) / len(self.calls), 1),
            "model": self.calls[0]["model"],
            "provider": self.calls[0]["provider"],
        }
```

---

### ADIM 4: `agents/parallel_runner.py` DEĞİŞİKLİĞİ (KRİTİK)

Bu dosya `run_fast.py`'nin kullandığı ana runner. En çok değişiklik gereken dosya.

**Yapılacak değişiklikler:**

**4a.** `import anthropic` → `from .llm_client import achat, LLMResponse, PROVIDER_MAP`  
**4b.** `from config.env_loader import get_api_key` ekle

**4c.** `_async_persona_call` fonksiyonunu değiştir:

```python
# MEVCUT (satır 18-79):
async def _async_persona_call(client: anthropic.AsyncAnthropic, ...) -> dict:
    ...
    response = await client.messages.create(model=model, max_tokens=800, ...)
    raw_text = response.content[0].text.strip()
    ...

# YENİ:
async def _async_persona_call(api_key: str, ..., usage_tracker=None) -> dict:
    ...
    response = await achat(
        system_prompt=system_prompt,
        user_message=user_message,
        model=model,
        temperature=temperature,
        max_tokens=800,
        api_key=api_key
    )
    if usage_tracker:
        usage_tracker.record(response)
    raw_text = response.content.strip()  # .content artık doğrudan string
    ...
```

**4d.** Aynı değişiklik `_async_followup_call` için:
- Burada multi-turn messages var. `achat()`'e messages listesi geçecek şekilde `achat_multiturn()` ek fonksiyonu gerekebilir.
- VEYA `achat()` fonksiyonuna `messages` parametresi de eklenebilir (system ayrı, messages liste olarak).

**DİKKAT — Followup'ta assistant message var:**
```python
messages = [
    {"role": "user", "content": "ANNOUNCEMENT..."},
    {"role": "assistant", "content": json.dumps({...})},  # Önceki yanıtın özeti
    {"role": "user", "content": "FOLLOW-UP QUESTION..."}
]
```
Bu yapı hem Anthropic hem OpenAI'da çalışır. Anthropic'te `system` ayrı parametre, OpenAI'da messages listesinin başına eklenir.

**4e.** `_run_experiment_async` fonksiyonunu değiştir:
```python
# MEVCUT:
client = anthropic.AsyncAnthropic(api_key=api_key)

# YENİ: Client oluşturma kaldırılır. api_key doğrudan fonksiyonlara geçer.
# Provider'a göre doğru key otomatik seçilir (llm_client içinde).
```

**4f.** Fonksiyon signature'larında `client: anthropic.AsyncAnthropic` → `api_key: str` değişikliği tüm zincirde yapılmalı.

**4g.** `usage_tracker` parametresini zincirin sonuna kadar geçir.

**Doğrulama:** Mevcut Exp 1'i K=1 ile koştur, sonuçların JSON yapısının aynı olduğunu doğrula.

---

### ADIM 5: `agents/persona_agent.py` DEĞİŞİKLİĞİ

Bu dosya `run_all.py` (sync yol) tarafından kullanılır.

**5a.** `import anthropic` → `from .llm_client import chat, LLMResponse`

**5b.** `get_persona_response` fonksiyonunu değiştir:
```python
# MEVCUT (satır 63-136):
def get_persona_response(client: anthropic.Anthropic, persona, stimulus, probe, signal_state, temperature, model):
    ...
    response = client.messages.create(model=model, max_tokens=800, temperature=temperature, system=system_prompt, messages=[...])
    raw_text = response.content[0].text.strip()

# YENİ:
def get_persona_response(api_key: str, persona, stimulus, probe, signal_state, temperature, model):
    ...
    response = chat(system_prompt=system_prompt, user_message=user_message, model=model, temperature=temperature, max_tokens=800, api_key=api_key)
    raw_text = response.content.strip()
```

**5c.** Aynı değişiklik `get_persona_followup` için — multi-turn messages ile.

**5d.** `build_persona_system_prompt` DEĞİŞMEZ — zaten LLM-agnostic.

---

### ADIM 6: `agents/moderator_agent.py` DEĞİŞİKLİĞİ

**6a.** `import anthropic` → kaldır  
**6b.** `run_afg_session(client: anthropic.Anthropic, ...)` → `run_afg_session(api_key: str, ...)`  
**6c.** `run_afg_experiment(client: anthropic.Anthropic, ...)` → `run_afg_experiment(api_key: str, ...)`  
**6d.** İçerideki `get_persona_response(client=client, ...)` → `get_persona_response(api_key=api_key, ...)`

---

### ADIM 7: `agents/__init__.py` GÜNCELLEMESİ

```python
from .persona_agent import get_persona_response, get_persona_followup, build_persona_system_prompt
from .moderator_agent import run_afg_session, run_afg_experiment
from .llm_client import chat, achat, LLMResponse, PROVIDER_MAP
from .usage_tracker import UsageTracker
```

---

### ADIM 8: `experiments/exp1_afg_protocol.py` (ve 2, 3, 4) DEĞİŞİKLİĞİ

Mevcut experiment dosyaları kendi `anthropic.Anthropic(api_key=api_key)` client'larını oluşturuyor. Bu değişmeli:

```python
# MEVCUT (exp1, satır ~27):
client = anthropic.Anthropic(api_key=api_key)
result = run_afg_experiment(client, personas, stimulus, ...)

# YENİ:
result = run_afg_experiment(api_key, personas, stimulus, ...)
```

Bu değişiklik exp1, exp2, exp3, exp4'te yapılacak.

**exp3_multilingual.py özel not:** Bu dosya `TURKISH_PERSONAS`, `TURKISH_STIMULUS`, `TURKISH_PROBES` tanımlıyor. Bunlar `run_fast.py` tarafından import ediliyor. Bu yapı korunacak.

---

### ADIM 9: `run_fast.py` GÜNCELLEMESİ

**9a.** API key yükleme değişikliği:

```python
# MEVCUT (satır 255-258):
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("ERROR: SET ANTHROPIC_API_KEY=sk-ant-...")
    sys.exit(1)

# YENİ:
from config.env_loader import get_api_key
from agents.llm_client import PROVIDER_MAP

provider = PROVIDER_MAP.get(args.model, "anthropic")
try:
    api_key = get_api_key(provider)
except EnvironmentError as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

**9b.** `--exp` choices genişletme:

```python
# MEVCUT:
parser.add_argument("--exp", type=int, choices=[1, 2, 3, 4])

# YENİ:
parser.add_argument("--exp", type=int, choices=[1, 2, 3, 4, 5, 6, 7, 8])
parser.add_argument("--revision", action="store_true", help="Sadece revision deneylerini koştur (5-8)")
```

**9c.** Yeni deney fonksiyonlarını ekle (Faz sonraki adımlarda implement edilecek):

```python
if args.all or args.revision or args.exp == 5:
    run_exp5(api_key, Ko, args.model)

if args.all or args.revision or args.exp == 6:
    run_exp6(api_key, Ko, args.model)

if args.all or args.revision or args.exp == 7:
    # İki model karşılaştırması — her ikisinin key'i gerekir
    key_claude = get_api_key("anthropic")
    key_openai = get_api_key("openai")
    run_exp7(key_claude, key_openai, K=args.K or 20)

if args.all or args.revision or args.exp == 8:
    run_exp8(api_key, K=args.K or 5, model=args.model)
```

**9d.** `estimate_cost()` fonksiyonuna yeni deneyleri ekle.

---

### ADIM 10: `requirements.txt` GÜNCELLEMESİ

```
anthropic>=0.40.0
openai>=1.0.0          # YENİ
numpy>=1.24.0
pandas>=2.0.0
sentence-transformers>=2.2.0
scipy>=1.10.0
scikit-learn>=1.3.0
tqdm>=4.65.0
```

---

### ADIM 11: Yeni Senaryo Config'leri

**11a.** `config/scenarios.json` dosyasına `scenario_2_greenhushing` ekle.

İçerik: Bir finans firması ESG ilerlemesini yayınlayıp yayınlamamak arasında kalmış. İki variant:
- `variant_A_disclose`: Firma ESG raporu yayınlar
- `variant_B_silent`: Firma sessiz kalır, rakip açıklar

Signal state: ESG disclosure gap, investor expectations, competitor reporting, greenhushing trend.

**11b.** `config/scenarios.json` dosyasına `scenario_4_crisis` ekle.

İçerik: "Sürdürülebilir kaynaklı" ürün hattının tedarikçi ihlalleri ortaya çıkmış. Üç variant:
- `variant_A_apologize`: Hemen özür + düzeltme planı
- `variant_B_rebut`: Olgusal çürütme
- `variant_C_delay`: 72 saat gecikme

Signal state: Kritik seviye, anomaly_score=0.92, sosyal medya ikiye katlanıyor.

**11c.** `config/scenarios.json` dosyasına Variant C paraphrase'i ekle (Exp 8 için).

Mevcut `variant_C_accountability` ile aynı bilgiyi içeren ama cümle yapısı farklı bir versiyon. Claude Code mevcut variant'ı okuyup semantik eşdeğer bir paraphrase oluştursun.

**11d.** `config/personas_scenario2.json` oluştur VEYA mevcut `personas.json`'a `personas_scenario2` key'i ekle.

Finans/yatırım ağırlıklı 8 persona: Institutional Investor, ESG Analyst, Financial Journalist, Retail Investor, Regulator, Company CSO, Competitor Analyst, Sustainability Academic.

**ÖNEMLİ:** Her persona'nın JSON yapısı mevcut persona'larla BİREBİR AYNI formatta olmalı: `id`, `label`, `demographics` (age_bracket, gender, education, income_range, region), `psychographics` (environmental_concern, brand_loyalty, media_consumption, institutional_trust), `role`, `behavioral_priors` (engagement_style, frame_susceptibility, info_seeking), `language`.

---

### ADIM 12: Yeni Deney Dosyaları

**12a. `experiments/exp5_greenhushing.py`**

Scenario 2, 2 variant, 8 persona, K run per variant.  
`run_fast.py`'den `--model` parametresi ile çağrılır — model ne verilirse o kullanılır.  
Her iki model karşılaştırması `run_fast.py`'den iki ayrı çağrıyla yapılır:
```bash
python run_fast.py --exp 5 --model claude-sonnet-4-20250514 --K 10
python run_fast.py --exp 5 --model gpt-4o --K 10
```

**12b. `experiments/exp6_crisis.py`**

Scenario 4, 3 variant, 8 persona (Scenario 1 ile aynı persona seti — tutarlılık için), K=5.  
Aynı dual-model çalıştırma pattern'i.

**12c. `experiments/exp7_cross_model.py`**

Scenario 1 Variant C — iki modeli aynı deney içinde sırayla koşturur.  
İki ayrı API key alır. Sonuçları karşılaştırma metrikleriyle birlikte kaydeder:
- Sentiment farkı (scipy.stats.ttest_ind)
- Tema örtüşme (Jaccard)
- Persona-level Pearson correlation
- Cosine similarity dağılımı karşılaştırması

**12d. `experiments/exp8_prompt_sensitivity.py`**

Scenario 1 Variant C orijinal vs paraphrase. Tek model (Claude). K=5 per variant.

---

### ADIM 13: `generate_tables.py` GÜNCELLEMESİ

Yeni tablolar:
- `generate_exp5_table()` — Greenhushing A/B sonuçları
- `generate_exp6_table()` — Crisis 3-variant sonuçları
- `generate_exp7_table()` — Cross-model karşılaştırma (Claude vs GPT-4o yan yana)
- `generate_exp8_table()` — Prompt sensitivity (orijinal vs paraphrase)
- `generate_sensitivity_summary()` — Tüm deneylerden parameter sensitivity özeti
- `generate_runtime_table()` — UsageTracker'dan toplanan runtime/token/cost verileri

---

### ADIM 14: README ve EXPERIMENT_PLAN Güncelleme

README'ye:
- OpenAI API key gerekliliği
- `--model gpt-4o` kullanım örneği
- Exp 5–8 açıklamaları
- `--revision` flag açıklaması

EXPERIMENT_PLAN'a:
- Exp 5–8 paper mapping'i
- Güncellenmiş maliyet tahmini

---

## UYGULAMA SIRASI — Claude Code'a VERİLECEK SIRA

```
[ ] ADIM 1:  .gitignore, .env.example, .env, config/env_loader.py, SETUP_API_KEYS.md, config/models.json
[ ] ADIM 2:  agents/llm_client.py (sync chat + async achat + LLMResponse + PROVIDER_MAP)
[ ] ADIM 3:  agents/usage_tracker.py
[ ] TEST A:  llm_client'ı test et — her iki provider'a basit bir prompt gönder
[ ] ADIM 4:  agents/parallel_runner.py güncelle (anthropic → llm_client)
[ ] ADIM 5:  agents/persona_agent.py güncelle (anthropic → llm_client)
[ ] ADIM 6:  agents/moderator_agent.py güncelle (client → api_key)
[ ] ADIM 7:  agents/__init__.py güncelle
[ ] ADIM 8:  experiments/exp1-4 güncelle (client → api_key)
[ ] TEST B:  Mevcut Exp 1'i K=1 ile koştur — regression test (Claude backend)
[ ] TEST C:  Exp 1'i K=1 ile --model gpt-4o ile koştur — yeni backend çalışıyor mu?
[ ] ADIM 9:  run_fast.py güncelle (model routing, exp 5-8, --revision flag)
[ ] ADIM 10: requirements.txt güncelle (openai>=1.0.0 ekle)
[ ] ADIM 11: Yeni senaryo config'leri (scenarios.json, personas)
[ ] ADIM 12: Yeni deney dosyaları (exp5, exp6, exp7, exp8)
[ ] TEST D:  Exp 5'i K=1 ile koştur (Claude) — yeni senaryo çalışıyor mu?
[ ] TEST E:  Exp 7'yi K=1 ile koştur — cross-model çalışıyor mu?
[ ] ADIM 13: generate_tables.py güncelle
[ ] ADIM 14: README, EXPERIMENT_PLAN ve SETUP_API_KEYS güncelle
[ ] TEST F:  run_fast.py --revision --K 2 — tüm yeni deneyler uçtan uca
```

---

## DEĞİŞİKLİK ÖZETİ

| Dosya | Durum | Ana Değişiklik |
|-------|-------|---------------|
| `.gitignore` | **YENİ** | .env, __pycache__, vb. |
| `.env.example` | **YENİ** | API key template (git'e commit edilir) |
| `.env` | **YENİ** | Gerçek key'ler (gitignore'da — ASLA commit edilmez) |
| `SETUP_API_KEYS.md` | **YENİ** | Kullanıcı rehberi: key alma, model listesi, kurulum, maliyet |
| `config/env_loader.py` | **YENİ** | .env okuyucu |
| `config/models.json` | **YENİ** | Desteklenen modeller, fiyatlandırma, provider mapping |
| `agents/llm_client.py` | **YENİ** | Unified sync+async LLM client |
| `agents/usage_tracker.py` | **YENİ** | Token/cost loglama |
| `agents/persona_agent.py` | **DEĞİŞ** | `client: Anthropic` → `api_key: str` + llm_client kullanımı |
| `agents/moderator_agent.py` | **DEĞİŞ** | `client: Anthropic` → `api_key: str` |
| `agents/parallel_runner.py` | **DEĞİŞ** | `AsyncAnthropic` → `achat()` + usage tracking |
| `agents/__init__.py` | **DEĞİŞ** | Yeni export'lar |
| `config/scenarios.json` | **DEĞİŞ** | Scenario 2, 4, Variant C paraphrase eklenir |
| `config/personas.json` | **DEĞİŞ** | Scenario 2 persona seti eklenir (veya ayrı dosya) |
| `experiments/exp1_afg_protocol.py` | **DEĞİŞ** | `client` → `api_key` |
| `experiments/exp2_signal_ab.py` | **DEĞİŞ** | `client` → `api_key` |
| `experiments/exp3_multilingual.py` | **DEĞİŞ** | `client` → `api_key` |
| `experiments/exp4_temperature.py` | **DEĞİŞ** | `client` → `api_key` |
| `experiments/exp5_greenhushing.py` | **YENİ** | Greenhushing deneyi |
| `experiments/exp6_crisis.py` | **YENİ** | Kriz iletişimi deneyi |
| `experiments/exp7_cross_model.py` | **YENİ** | Cross-model karşılaştırma |
| `experiments/exp8_prompt_sensitivity.py` | **YENİ** | Prompt hassasiyet testi |
| `run_fast.py` | **DEĞİŞ** | Model routing, exp 5-8, --revision |
| `run_all.py` | **DEĞİŞ** | Aynı pattern |
| `generate_tables.py` | **DEĞİŞ** | Yeni tablo fonksiyonları |
| `requirements.txt` | **DEĞİŞ** | `openai>=1.0.0` eklenir |
| `README.md` | **DEĞİŞ** | Multi-model dokümantasyonu |
| `EXPERIMENT_PLAN.md` | **DEĞİŞ** | Exp 5-8 dokümantasyonu |

**Yeni: 10 dosya — Değişen: 18 dosya — Toplam: 28 dosya**
