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
