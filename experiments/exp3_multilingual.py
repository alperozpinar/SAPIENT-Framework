"""
EXP-3: Multilingual Stress Test (English vs Turkish)

Maps to: Paper Stage 4a (§5.1)
Tests: Cross-lingual consistency when the same scenario runs in EN and TR.

Key concern from paper: "LLMs exhibit language-linked asymmetries in safety behavior,
stereotype expression, and response diversity" (§6.4, Limitations).
"""

import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.moderator_agent import run_afg_experiment
from metrics.analysis import (
    generate_full_report, print_summary,
    compute_theme_coverage_comparison
)


# Turkish translations of persona specs (matched demographics)
TURKISH_PERSONAS = [
    {
        "id": "P1_TR", "label": "Çevre Aktivisti", "language": "tr",
        "demographics": {"age_bracket": "25-34", "gender": "kadın", "education": "yüksek lisans", "income_range": "düşük-orta", "region": "Batı Avrupa"},
        "psychographics": {"environmental_concern": "çok_yüksek", "brand_loyalty": "düşük", "media_consumption": "sosyal_medya_yoğun", "institutional_trust": "düşük"},
        "role": "aktivist",
        "behavioral_priors": {"engagement_style": "yüzleştirici", "frame_susceptibility": "yeşil_badana_suçlaması", "info_seeking": "yüksek"}
    },
    {
        "id": "P2_TR", "label": "ESG Fon Yöneticisi", "language": "tr",
        "demographics": {"age_bracket": "40-49", "gender": "erkek", "education": "MBA", "income_range": "yüksek", "region": "Kuzey Amerika"},
        "psychographics": {"environmental_concern": "yüksek", "brand_loyalty": "orta", "media_consumption": "finansal_basın", "institutional_trust": "orta"},
        "role": "yatırımcı",
        "behavioral_priors": {"engagement_style": "analitik", "frame_susceptibility": "uyum_riski", "info_seeking": "çok_yüksek"}
    },
    {
        "id": "P3_TR", "label": "Perakende Tüketici", "language": "tr",
        "demographics": {"age_bracket": "30-39", "gender": "kadın", "education": "lisans", "income_range": "orta", "region": "Türkiye"},
        "psychographics": {"environmental_concern": "orta", "brand_loyalty": "yüksek", "media_consumption": "ana_akım_haber", "institutional_trust": "orta"},
        "role": "tüketici",
        "behavioral_priors": {"engagement_style": "pasif", "frame_susceptibility": "kişisel_ilgi", "info_seeking": "orta"}
    },
    {
        "id": "P4_TR", "label": "Sektör Gazetecisi", "language": "tr",
        "demographics": {"age_bracket": "35-44", "gender": "erkek", "education": "yüksek lisans", "income_range": "orta-yüksek", "region": "Türkiye"},
        "psychographics": {"environmental_concern": "orta", "brand_loyalty": "yok", "media_consumption": "sektör_yayınları", "institutional_trust": "düşük-orta"},
        "role": "gazeteci",
        "behavioral_priors": {"engagement_style": "araştırmacı", "frame_susceptibility": "haber_değeri", "info_seeking": "çok_yüksek"}
    },
    {
        "id": "P5_TR", "label": "Düzenleyici Gözlemci", "language": "tr",
        "demographics": {"age_bracket": "50-59", "gender": "kadın", "education": "hukuk", "income_range": "yüksek", "region": "AB"},
        "psychographics": {"environmental_concern": "yüksek", "brand_loyalty": "yok", "media_consumption": "düzenleyici_dosyalar", "institutional_trust": "yüksek"},
        "role": "düzenleyici",
        "behavioral_priors": {"engagement_style": "prosedürel", "frame_susceptibility": "uyum_boşluğu", "info_seeking": "yüksek"}
    },
    {
        "id": "P6_TR", "label": "Şirket Çalışanı", "language": "tr",
        "demographics": {"age_bracket": "28-35", "gender": "diğer", "education": "lisans", "income_range": "orta", "region": "Türkiye"},
        "psychographics": {"environmental_concern": "orta-yüksek", "brand_loyalty": "yüksek", "media_consumption": "iç_kanallar", "institutional_trust": "orta-yüksek"},
        "role": "çalışan",
        "behavioral_priors": {"engagement_style": "temkinli", "frame_susceptibility": "iş_güvenliği", "info_seeking": "orta"}
    },
    {
        "id": "P7_TR", "label": "Rakip Strateji Analisti", "language": "tr",
        "demographics": {"age_bracket": "32-40", "gender": "erkek", "education": "yüksek lisans", "income_range": "orta-yüksek", "region": "Doğu Asya"},
        "psychographics": {"environmental_concern": "düşük-orta", "brand_loyalty": "yok", "media_consumption": "sektör_raporları", "institutional_trust": "orta"},
        "role": "rakip",
        "behavioral_priors": {"engagement_style": "stratejik", "frame_susceptibility": "pazar_konumlandırma", "info_seeking": "yüksek"}
    },
    {
        "id": "P8_TR", "label": "Sürdürülebilirlik Akademisyeni", "language": "tr",
        "demographics": {"age_bracket": "45-55", "gender": "kadın", "education": "doktora", "income_range": "orta-yüksek", "region": "Batı Avrupa"},
        "psychographics": {"environmental_concern": "çok_yüksek", "brand_loyalty": "yok", "media_consumption": "akademik_dergiler", "institutional_trust": "orta"},
        "role": "akademisyen",
        "behavioral_priors": {"engagement_style": "kanıt_temelli", "frame_susceptibility": "bilimsel_doğruluk", "info_seeking": "çok_yüksek"}
    }
]

# Turkish stimulus (same scenario)
TURKISH_STIMULUS = """GlobalChem Corp şu açıklamayı yapıyor: 'Kendi operasyonlarımız dahil olmak üzere kimya sektörünün önemli bir çevresel ayak izine sahip olduğunun farkındayız. Son dönemdeki haberler, tedarik zinciri gözetimimizdeki boşlukları gün yüzüne çıkarmıştır ve bunu ciddiye alıyoruz. Bugün, 2040 yılına kadar net sıfır hedefimizi üç acil eylemle birlikte açıklıyoruz: 6 ay içinde tamamlanacak bağımsız bir tedarik zinciri denetimi, 500 milyon dolarlık tedarikçi dönüşüm fonu ve 2025'in ilk çeyreğinden itibaren Kapsam 1, 2 ve 3 emisyonlarının üç aylık kamuya açık raporlanması. Bizi hesap verebilir kılmak için bağımsız bir sürdürülebilirlik danışma kurulu oluşturduk.'"""

TURKISH_PROBES = [
    "Bu açıklamayı ne kadar inandırıcı buluyorsunuz? Hangi unsurlar güveninizi artırıyor veya azaltıyor?",
    "Bu açıklamada eksik olan hangi bilgileri görmeniz gerekir?"
]


def run_exp3(api_key: str, K: int = 5, model: str = "claude-sonnet-4-20250514"):
    """Run multilingual comparison: English vs Turkish."""
    with open(os.path.join(os.path.dirname(__file__), "..", "config", "personas.json")) as f:
        en_personas = json.load(f)["personas"]

    with open(os.path.join(os.path.dirname(__file__), "..", "config", "scenarios.json")) as f:
        scenario = json.load(f)["scenario_1_greenwashing"]

    en_stimulus = scenario["stimuli"]["variant_C_accountability"]
    en_probes = scenario["moderator_probes"][:2]
    signal_state = scenario["signal_state_rich"]

    # --- English ---
    print("\n" + "=" * 60)
    print("ENGLISH SESSION")
    print("=" * 60)

    result_en = run_afg_experiment(
        api_key=api_key, personas=en_personas, stimulus=en_stimulus,
        probes=en_probes, K=K, signal_state=signal_state,
        temperature_mode="stratified", model=model, experiment_label="exp3_EN"
    )
    report_en = generate_full_report(result_en)
    print_summary(report_en)

    # --- Turkish ---
    print("\n" + "=" * 60)
    print("TURKISH SESSION")
    print("=" * 60)

    result_tr = run_afg_experiment(
        api_key=api_key, personas=TURKISH_PERSONAS, stimulus=TURKISH_STIMULUS,
        probes=TURKISH_PROBES, K=K, signal_state=signal_state,
        temperature_mode="stratified", model=model, experiment_label="exp3_TR"
    )
    report_tr = generate_full_report(result_tr)
    print_summary(report_tr)

    # --- Cross-lingual comparison ---
    print("\n" + "=" * 70)
    print("CROSS-LINGUAL COMPARISON: EN vs TR")
    print("=" * 70)

    sent_en = report_en.get("sentiment", {}).get("overall", {})
    sent_tr = report_tr.get("sentiment", {}).get("overall", {})
    vc_en = report_en.get("variance_collapse", {})
    vc_tr = report_tr.get("variance_collapse", {})

    print(f"\nSentiment:")
    print(f"  EN: mean={sent_en.get('mean', 0):.2f}, std={sent_en.get('std', 0):.2f}")
    print(f"  TR: mean={sent_tr.get('mean', 0):.2f}, std={sent_tr.get('std', 0):.2f}")
    print(f"\nResponse Diversity (mean cosine sim):")
    print(f"  EN: {vc_en.get('overall_mean', 0):.4f}")
    print(f"  TR: {vc_tr.get('overall_mean', 0):.4f}")
    print(f"\nTheme Count:")
    print(f"  EN: {report_en.get('theme_stability', {}).get('total_unique_themes', 0)}")
    print(f"  TR: {report_tr.get('theme_stability', {}).get('total_unique_themes', 0)}")

    # Save
    output_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    with open(os.path.join(output_dir, f"exp3_multilingual_{timestamp}.json"), "w") as f:
        json.dump({
            "english": {"result": result_en, "report": report_en},
            "turkish": {"result": result_tr, "report": report_tr},
        }, f, indent=2, default=str, ensure_ascii=False)

    print(f"\nResults saved to {output_dir}/exp3_multilingual_{timestamp}.json")


if __name__ == "__main__":
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)
    K = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    run_exp3(api_key, K=K)
