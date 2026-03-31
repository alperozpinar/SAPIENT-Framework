# SAPIENT — Gemini 2.5 Flash Entegrasyonu ve Deney Sonuclari

**Tarih:** 2026-03-31  
**Kapsam:** Google Gemini API entegrasyonu, EXP-7 Gemini kolu, EXP-8 K=20 genisletme

---

## 1. Yapilan Degisiklikler

### 1.1 Yeni Dosyalar
*Yeni dosya eklenmedi — tum degisiklikler mevcut dosyalarda yapildi.*

### 1.2 Guncellenen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `agents/llm_client.py` | Gemini provider eklendi (sync `chat()` + async `achat()`). `PROVIDER_MAP`, `PRICING` guncellendi. Gemini 2.5 thinking token budget fix (max_output_tokens * 10). `_is_retryable()` fonksiyonuna Google API hatalari eklendi. |
| `config/models.json` | `gemini-2.5-flash` model tanimi eklendi (provider: google, pricing, concurrency: 2). `env_variables` blogu guncellendi. |
| `config/env_loader.py` | `get_api_key()` fonksiyonuna `"google": "GEMINI_API_KEY"` eklendi. |
| `.env.example` | `GEMINI_API_KEY=your-gemini-key-here` satiri eklendi. |
| `requirements.txt` | `google-generativeai>=0.8.0` eklendi. |
| `run_fast.py` | EXP-7 cagirisina `key_gemini` parametresi eklendi. Gemini key yoksa uyari verip devam ediyor. `--model` arguman aciklamasi guncellendi. |
| `experiments/exp7_cross_model.py` | 2-way (Claude vs GPT-4o) yerine 3-way (+ Gemini) karsilastirma. Pairwise Spearman + Pearson korelasyon. Pairwise Welch t-test. Pairwise Jaccard. |

### 1.3 Teknik Detaylar

**Gemini API Entegrasyonu:**
- SDK: `google-generativeai` (v0.8.6)
- Model: `gemini-2.5-flash`
- System prompt: `system_instruction` parametresi ile
- Multi-turn: Messages listesi Gemini Content formatina donusturuluyor (`role: "model"` / `"user"`)
- Async: `generate_content_async()` metodu ile
- Token tracking: `response.usage_metadata.prompt_token_count` / `candidates_token_count`
- Pricing: Input $0.15/MTok, Output $0.60/MTok

**Thinking Token Fix:**
Gemini 2.5 Flash modeli "thinking" modunu varsayilan olarak kullaniyor. Thinking tokenlari `max_output_tokens` butcesinden harcaniyor. 800 tokenlik butce ile model dusunmeye ~700 token harcayip gercek ciktiyi kesiyor. Cozum: `max_output_tokens = max(max_tokens * 10, 8192)` ile Gemini'ye yeterli butce saglandi.

**Error Handling:**
`google.api_core.exceptions` modulu uzerinden retryable hatalar: `ResourceExhausted`, `InternalServerError`, `ServiceUnavailable`, `TooManyRequests`.

---

## 2. Calistirilan Deneyler

### 2.1 EXP-7 Gemini Kolu (Yeni)
- **Senaryo:** Scenario 1, Variant C (accountability framing)
- **K:** 20 run
- **Personalar:** 8 (P1-P8), independent mode
- **Model:** gemini-2.5-flash
- **Sonuc:** 20 x 8 = **160 initial response** + **160 followup** = **320 API call**
- **Parse basari:** 160/160 (%100)
- **Toplam cost:** $0.10
- **Elapsed:** 6.1 dk
- **Mean latency:** 12.7 s/call
- **Input tokens:** 229,301
- **Output tokens:** 110,670

### 2.2 EXP-8 K=20 Genisletme
- **Senaryo:** Scenario 1, Variant C original + paraphrase
- **K:** 20 run (onceki K=5'ten genisletildi)
- **Personalar:** 8 (P1-P8)
- **Model:** claude-sonnet-4-20250514
- **Sonuc:** 20 x 2 x 8 = **320 initial** + **320 followup** = **640 API call**
- **Toplam cost:** $3.69
- **Elapsed:** 3.8 dk

---

## 3. Sonuclar

### 3.1 Cross-Model Sentiment Karsilastirmasi (3-Way)

| Model | Sentiment Mean | Sentiment Std | Credibility Mean | Credibility Std |
|-------|---------------|---------------|-----------------|----------------|
| Claude Sonnet 4 | 4.269 | 0.804 | 4.394 | 0.717 |
| GPT-4o | 4.487 | 0.707 | 4.631 | 0.721 |
| Gemini 2.5 Flash | 4.619 | 1.117 | 4.569 | 1.197 |

### 3.2 Pairwise Welch t-test (Sentiment)

| Cift | t | p | Anlamlilik |
|------|---|---|-----------|
| Claude vs GPT-4o | -2.576 | 0.010 | * |
| Claude vs Gemini | -3.206 | 0.002 | * |
| GPT-4o vs Gemini | -1.252 | 0.212 | n.s. |

### 3.3 Persona-level Sentiment Korelasyonu

| Cift | Pearson r | Pearson p | Spearman r | Spearman p |
|------|-----------|-----------|------------|------------|
| Claude <-> GPT-4o | **0.935** | 0.0006 | 0.783 | 0.022 |
| Claude <-> Gemini | **0.924** | 0.0010 | 0.683 | 0.062 |
| GPT-4o <-> Gemini | **0.960** | 0.0002 | 0.898 | 0.002 |

### 3.4 Persona-level Sentiment Rankings (Mean, K=20)

| Persona | Claude | GPT-4o | Gemini |
|---------|--------|--------|--------|
| P1 | 2.800 | 3.000 | 2.100 |
| P2 | 4.900 | 5.000 | 5.250 |
| P3 | 4.250 | 4.900 | 5.100 |
| P4 | 3.950 | 4.200 | 4.500 |
| P5 | 4.850 | 4.650 | 4.850 |
| P6 | 4.800 | 5.000 | 5.500 |
| P7 | 4.250 | 4.400 | 5.000 |
| P8 | 4.350 | 4.750 | 4.650 |

### 3.5 Theme Overlap (Jaccard Index)

| Cift | Jaccard | Shared | Total A | Total B |
|------|---------|--------|---------|---------|
| Claude <-> GPT-4o | 0.060 | 39 | 368 | 325 |
| Claude <-> Gemini | 0.059 | 50 | 368 | 524 |
| GPT-4o <-> Gemini | 0.077 | 61 | 325 | 524 |

### 3.6 Variance Collapse (Mean Pairwise Cosine Similarity)

| Model | Mean Cosine Sim | Threshold (delta=0.85) | Flagged Runs |
|-------|----------------|----------------------|-------------|
| Claude Sonnet 4 | 0.184 | OK | 0/20 |
| GPT-4o | 0.279 | OK | 0/20 |
| Gemini 2.5 Flash | 0.203 | OK | 0/20 |

### 3.7 EXP-8 Prompt Sensitivity (K=20)

| Metrik | Original | Paraphrase | t | p | Anlamlilik |
|--------|----------|------------|---|---|-----------|
| Sentiment | 4.325 | 4.494 | -1.879 | 0.061 | n.s. |
| Credibility | 4.344 | 4.663 | -4.268 | <0.001 | * |
| Theme Jaccard | — | — | — | 0.300 | — |

---

## 4. Guncellenmis Runtime/Cost Tablosu

| Kalem | Deger |
|-------|-------|
| Onceki toplam API calls | 3,328 |
| + EXP-7 Gemini arm | +320 |
| + EXP-8 K=20 genisletme | +640 |
| **Yeni toplam API calls** | **4,288** |
| Gemini avg latency | 12.7 s/call |
| Gemini total cost | $0.10 |
| EXP-8 K=20 cost | $3.69 |
| **Ek toplam cost** | **$3.79** |

---

## 5. Cikti Dosyalari

| Dosya | Icerik |
|-------|--------|
| `results/exp7_gemini_20260331_122650.json` | Gemini 20 run raw + report + usage |
| `results/exp7_3way_comparison_20260331_124030.json` | 3-way comparison (Claude + GPT-4o + Gemini) |
| `results/exp8_prompt_sensitivity_20260331_123914.json` | EXP-8 K=20 raw + report + comparison |

---

## 6. Kullanim

```bash
# Gemini ile tek basina deney calistirma
python run_fast.py --exp 1 --K 5 --model gemini-2.5-flash

# 3-way cross-model karsilastirma (tum keyler gerekli)
python run_fast.py --exp 7 --K 20

# Cost tahmini
python run_fast.py --estimate --model gemini-2.5-flash
```

**Gerekli environment variables:**
```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=AIzaSy...
```

---

## 7. Notlar

- Gemini 2.5 Flash content filtering Claude'dan farkli olabilir; bu run'da herhangi bir filtered response gozlenmedi.
- `google.generativeai` paketi deprecated olarak isaretlendi, gelecekte `google.genai` paketine gecis yapilmasi gerekebilir. Mevcut SDK (v0.8.6) sorunsuz calisiyor.
- Gemini'nin variance collapse skoru (0.203) Claude'a yakin (0.184); her uc model de delta=0.85 esiginin altinda — variance collapse gozlenmedi.
- Persona-level korelasyonlar tum ciftlerde r > 0.92 (Pearson) — model-agnostic design iddiasini guclendiriyor.
