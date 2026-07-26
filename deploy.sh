#!/bin/bash
set -e
git pull origin main
systemctl restart ai-documentary-studio-webui.service
sleep 3
curl -sf http://localhost:8501/_stcore/health && echo "Deploy OK" || echo "Deploy FAILED - health check başarısız"
