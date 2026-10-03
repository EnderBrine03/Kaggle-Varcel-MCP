# Kaggle-Varcel-MCP

Kaggle API'nin **tam yüzeyi** — competitions, datasets, kernels, models — Model Context Protocol (MCP) üzerinden.

## Tool listesi (40+)

### Competitions (9)
| Tool | Açıklama |
|------|----------|
| `competitions_list` | Yarışma ara / listele |
| `competition_get` | Detay |
| `competition_list_files` | Veri dosyaları |
| `competition_download_files` | Tüm dosyaları indir |
| `competition_download_file` | Tek dosya indir |
| `competition_submit` | Submission gönder |
| `competition_submissions` | Senin submission'ların |
| `competition_leaderboard` | Public LB (CSV metin) |
| `competition_leaderboard_download` | LB dosyasını kaydet |

### Datasets (10)
| Tool | Açıklama |
|------|----------|
| `datasets_list` | Dataset ara |
| `dataset_metadata` | Metadata |
| `dataset_list_files` | Dosya listesi |
| `dataset_status` | İşleme durumu |
| `dataset_download_files` | Tüm dosyaları indir |
| `dataset_download_file` | Tek dosya |
| `dataset_initialize` | metadata şablonu |
| `dataset_create` | Yeni dataset oluştur |
| `dataset_create_version` | Yeni versiyon |

### Kernels / Notebooks (8)
| Tool | Açıklama |
|------|----------|
| `kernels_list` | Notebook/script ara |
| `kernel_list_files` | Kernel dosyaları |
| `kernel_pull` | Kaynak kodu indir |
| `kernel_push` | Kernel yükle |
| `kernel_output` | Output indir |
| `kernel_status` | Çalışma durumu |
| `kernel_initialize` | metadata şablonu |

### Models (12)
| Tool | Açıklama |
|------|----------|
| `models_list` | Model ara |
| `model_get` | Model detay |
| `model_initialize` | metadata şablonu |
| `model_create` | Model oluştur |
| `model_update` | Metadata güncelle |
| `model_delete` | Model sil (yıkıcı) |
| `model_instances_list` | Instance'lar |
| `model_instance_get` | Instance detay |
| `model_instance_initialize` | instance metadata |
| `model_instance_create` | Instance oluştur |
| `model_instance_versions` | Versiyonlar |
| `model_instance_version_create` | Yeni versiyon |
| `model_instance_files` | Instance dosyaları |

### Utility
| Tool | Açıklama |
|------|----------|
| `whoami` | Kimlik doğrulama |
| `config_view` | Config yolları (secret yok) |

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export KAGGLE_USERNAME=...
export KAGGLE_KEY=...
# veya ~/.kaggle/kaggle.json
```

## Çalıştırma

```bash
# Claude Desktop / Cursor
python server.py

# ChatGPT remote
python server.py http
# → http://0.0.0.0:8000/mcp
```

### Claude Desktop

```json
{
  "mcpServers": {
    "kaggle": {
      "command": "python",
      "args": ["/abs/path/to/Kaggle-Varcel-MCP/server.py"],
      "env": {
        "KAGGLE_USERNAME": "your_user",
        "KAGGLE_KEY": "your_key"
      }
    }
  }
}
```

### ChatGPT Connector

1. Developer Mode aç
2. Settings → Connectors → Create
3. URL: `https://your-host/mcp`

## Notlar

- Competition download/submit için Kaggle'da **rules kabul** edilmiş olmalı.
- `model_*` metodları `kaggle` paketi sürümüne bağlı; eski sürümde bazıları hata dönebilir → `pip install -U kaggle`.
- Download tool'ları dosyayı **sunucunun lokal diskine** yazar (stdio host makinesi / Vercel ephemeral FS).

## Lisans

MIT
